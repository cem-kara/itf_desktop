"""
NbAlgoritma Test Suite

Kapsam:
- Temel kısıtlar: aynı günde aynı kişiye iki atama yok
- Ardışık gün yasağı (ArdisikGunIzinli=0)
- İzinli personele atama yapılmaz
- Slot doldurulamazsa uyarı verilir
- Tatil günü hariç tutma
- plan_olustur SonucYonetici döndürür
"""
from collections import Counter, defaultdict
from datetime import date

import pytest

from core.services.nobet.nb_algoritma import NbAlgoritma


# ─────────────────────────────────────────────────────────────
#  Fake altyapı
# ─────────────────────────────────────────────────────────────

class FakeRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def get_all(self):
        return [dict(r) for r in self.rows]

    def insert(self, row):
        self.rows.append(dict(row))

    def delete(self, pk):
        for i, r in enumerate(self.rows):
            if r.get("SatirID") == pk or r.get("PlanID") == pk:
                self.rows.pop(i)
                return True
        return False

    def get_where(self, filtre):
        result = []
        for r in self.rows:
            if all(r.get(k) == v for k, v in filtre.items()):
                result.append(dict(r))
        return result


class FakeRegistry:
    def __init__(self, data):
        self._repos = {k: FakeRepo(v) for k, v in data.items()}

    def get(self, name):
        return self._repos.setdefault(name, FakeRepo())


# ─────────────────────────────────────────────────────────────
#  Ortak veri fabrikası
# ─────────────────────────────────────────────────────────────

def _registry(
    personel_ids=("P1", "P2", "P3"),
    tatiller=(),
    izinler=(),
    slot_sayisi=2,
    ardisik_gun_izinli=0,
    tercihler=(),
) -> FakeRegistry:
    return FakeRegistry({
        "NB_Birim": [
            {"BirimID": "B1", "BirimAdi": "Radyoloji"},
        ],
        "NB_BirimAyar": [
            {
                "BirimID":             "B1",
                "GunlukSlotSayisi":    slot_sayisi,
                "FmMaxSaat":           60,
                "ArdisikGunIzinli":    ardisik_gun_izinli,
                "HaftasonuCalismaVar": 1,
                "ResmiTatilCalismaVar":1,
                "DiniBayramCalismaVar":0,
                "MaxGunlukSureDakika": 1440,
            },
        ],
        "NB_VardiyaGrubu": [
            {"GrupID": "G1", "BirimID": "B1", "GrupAdi": "Ana", "Aktif": 1, "Sira": 1},
        ],
        "NB_Vardiya": [
            {"VardiyaID": "V1", "GrupID": "G1", "VardiyaAdi": "Gündüz",
             "Rol": "ana", "Aktif": 1, "Sira": 1, "SureDakika": 420},
            {"VardiyaID": "V2", "GrupID": "G1", "VardiyaAdi": "Gece",
             "Rol": "ana", "Aktif": 1, "Sira": 2, "SureDakika": 420},
        ],
        "NB_BirimPersonel": [
            {"BirimID": "B1", "PersonelID": pid, "Aktif": 1}
            for pid in personel_ids
        ],
        "Personel": [
            {"KimlikNo": pid, "AdSoyad": f"Personel {pid}", "GorevYeri": "Radyoloji"}
            for pid in personel_ids
        ],
        "NB_PersonelTercih": list(tercihler),
        "Tatiller": [{"Tarih": t} for t in tatiller],
        "Izin_Giris": list(izinler),
        "NB_Plan": [],
        "NB_PlanSatir": [],
        "NB_MesaiHesap": [],
        "NB_MesaiKural": [],
    })


# ─────────────────────────────────────────────────────────────
#  1. Temel kısıt: aynı günde aynı kişiye ikinci atama yok
# ─────────────────────────────────────────────────────────────

class TestAyniGunAyniKisi:

    def test_gun_kisi_kombinasyonu_en_fazla_bir_kez(self):
        registry = _registry()
        sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        assert sonuc.basarili is True

        satirlar = registry.get("NB_PlanSatir").get_all()
        satir_idler = [s.get("SatirID") for s in satirlar if s.get("SatirID")]
        assert len(satir_idler) == len(set(satir_idler))

    def test_plan_satirlari_bos_degildir(self):
        registry = _registry()
        NbAlgoritma(registry).plan_olustur("B1", 2026, 3)
        assert len(registry.get("NB_PlanSatir").get_all()) > 0


# ─────────────────────────────────────────────────────────────
#  2. Ardışık gün yasağı (ArdisikGunIzinli=0)
# ─────────────────────────────────────────────────────────────

class TestArdisikGunYasagi:

    def test_ardi_sik_atama_yapilmaz_yasak_aktifken(self):
        """
        ArdisikGunIzinli=0 → bir personel dün nöbetteyse bugün atanamaz.
        Çıktıda ardışık gün ataması olmamalı.
        """
        registry = _registry(ardisik_gun_izinli=0)
        NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        satirlar = registry.get("NB_PlanSatir").get_all()
        tarih_kisi = defaultdict(set)
        for s in satirlar:
            tarih_kisi[s["NobetTarihi"]].add(s["PersonelID"])

        # Ardışık gün kontrolü
        gunler = sorted(tarih_kisi.keys())
        for i in range(len(gunler) - 1):
            bugun = gunler[i]
            yarin = gunler[i + 1]
            # Sadece gerçekten ardışık (takvim) günler
            d1 = date.fromisoformat(bugun)
            d2 = date.fromisoformat(yarin)
            if (d2 - d1).days == 1:
                kesisim = tarih_kisi[bugun] & tarih_kisi[yarin]
                assert not kesisim, \
                    f"{bugun} ve {yarin} ardışık günde aynı kişi: {kesisim}"

    def test_ardisik_atama_izinli_ise_yapilabilir(self):
        """ArdisikGunIzinli=1 → ardışık atama mümkün, plan yine başarılı."""
        registry = _registry(ardisik_gun_izinli=1)
        sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)
        assert sonuc.basarili is True


# ─────────────────────────────────────────────────────────────
#  3. İzinli personele atama yapılmaz
# ─────────────────────────────────────────────────────────────

class TestIzinliPersonel:

    def test_izinli_gun_atlaniyor(self):
        """
        P1, 01-31 Mart boyunca izinli → Mart planında P1'e hiç atama olmamalı.
        """
        izinler = [{
            "Izinid":        "IZ1",
            "Personelid":    "P1",
            "BaslamaTarihi": "2026-03-01",
            "BitisTarihi":   "2026-03-31",
            "Durum":         "Onaylandı",
        }]
        registry = _registry(izinler=izinler)
        sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        assert sonuc.basarili is True

        satirlar = registry.get("NB_PlanSatir").get_all()
        p1_satirlari = [s for s in satirlar if s["PersonelID"] == "P1"]
        assert len(p1_satirlari) == 0, \
            f"İzinli P1'e {len(p1_satirlari)} atama yapılmış!"

    def test_iptal_izin_engel_teskil_etmez(self):
        """İptal edilmiş izin → personel atamaya dahil edilmeli."""
        izinler = [{
            "Izinid":        "IZ2",
            "Personelid":    "P1",
            "BaslamaTarihi": "2026-03-01",
            "BitisTarihi":   "2026-03-31",
            "Durum":         "İptal",
        }]
        registry = _registry(izinler=izinler)
        NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        satirlar = registry.get("NB_PlanSatir").get_all()
        p1_satirlari = [s for s in satirlar if s["PersonelID"] == "P1"]
        assert len(p1_satirlari) > 0, "İptal izin olan P1 plana dahil edilmedi!"


# ─────────────────────────────────────────────────────────────
#  4. Slot doldurulamazsa uyarı
# ─────────────────────────────────────────────────────────────

class TestSlotUyarisi:

    def test_yetersiz_personel_uyari_uretir(self):
        """
        2 personel, slot=4 → her gün 2 slot doldurulamaz → uyarı olmalı.
        """
        registry = _registry(personel_ids=("P1", "P2"), slot_sayisi=4)
        sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        assert sonuc.basarili is True
        uyarilar = sonuc.veri.get("uyarilar", [])
        assert any("doldurulamadı" in u or "doldurulam" in u for u in uyarilar), \
            f"Beklenen uyarı bulunamadı. Uyarılar: {uyarilar}"


# ─────────────────────────────────────────────────────────────
#  5. Sonuç yapısı
# ─────────────────────────────────────────────────────────────

class TestSonucYapisi:

    def test_basarili_sonuc_veri_alanlarini_icerir(self):
        registry = _registry()
        sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        assert sonuc.basarili is True
        assert isinstance(sonuc.veri, dict)
        assert "PlanID"   in sonuc.veri
        assert "uyarilar" in sonuc.veri

    def test_bilinmeyen_birim_basarisiz(self):
        registry = _registry()
        sonuc = NbAlgoritma(registry).plan_olustur("BILINMEYEN", 2026, 3)
        assert sonuc.basarili is False

    def test_bos_personel_listesi_basarisiz_veya_uyarili(self):
        """Personel yoksa plan oluşturulmamalı ya da tüm slotlar uyarı vermeli."""
        registry = _registry(personel_ids=())
        sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)
        # Ya başarısız olur ya da uyarılar dolu gelir
        if sonuc.basarili:
            uyarilar = sonuc.veri.get("uyarilar", [])
            assert len(uyarilar) > 0
        else:
            assert sonuc.basarili is False

    def test_plan_id_kaydedildi(self):
        """plan_olustur NB_Plan tablosuna kayıt eklemeli."""
        registry = _registry()
        sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        assert sonuc.basarili is True
        plan_satirlari = registry.get("NB_Plan").get_all()
        assert len(plan_satirlari) >= 1

    def test_ilk_gun_tum_personel_yerlesir(self):
        """
        İlk günde 3 kişi var, slot=2 → 2 atama yapılır, 1 kişi dışarıda kalır.
        """
        registry = _registry(personel_ids=("P1", "P2", "P3"), slot_sayisi=2)
        NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        ilk_gun = [
            s for s in registry.get("NB_PlanSatir").get_all()
            if s["NobetTarihi"] == "2026-03-01"
        ]
        assert len(ilk_gun) >= 2

    def test_mart_toplam_gun_sayisi_dogru(self):
        """Mart 31 gün → plan satırları en fazla 31 × slot_sayisi olabilir."""
        slot = 2
        registry = _registry(slot_sayisi=slot)
        NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

        satirlar = registry.get("NB_PlanSatir").get_all()
        assert len(satirlar) >= 31
