from collections import Counter

from core.services.nobet.nb_algoritma import NbAlgoritma


class FakeRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def get_all(self):
        return [dict(row) for row in self.rows]

    def insert(self, row):
        self.rows.append(dict(row))

    def delete(self, pk):
        for index, row in enumerate(self.rows):
            if row.get("SatirID") == pk or row.get("PlanID") == pk:
                self.rows.pop(index)
                return True
        return False


class FakeRegistry:
    def __init__(self, data):
        self._repos = {name: FakeRepo(rows) for name, rows in data.items()}

    def get(self, name):
        return self._repos.setdefault(name, FakeRepo())


def _algoritma_registry() -> FakeRegistry:
    return FakeRegistry({
        "NB_BirimAyar": [
            {"BirimID": "B1", "GunlukSlotSayisi": 2, "FmMaxSaat": 60},
        ],
        "NB_VardiyaGrubu": [
            {
                "GrupID": "G1",
                "BirimID": "B1",
                "GrupAdi": "Ana Grup",
                "Aktif": 1,
                "Sira": 1,
            },
        ],
        "NB_Vardiya": [
            {
                "VardiyaID": "V1",
                "GrupID": "G1",
                "VardiyaAdi": "Gunduz",
                "Rol": "ana",
                "Aktif": 1,
                "Sira": 1,
                "SureDakika": 720,
            },
            {
                "VardiyaID": "V2",
                "GrupID": "G1",
                "VardiyaAdi": "Gece",
                "Rol": "ana",
                "Aktif": 1,
                "Sira": 2,
                "SureDakika": 720,
            },
        ],
        "NB_BirimPersonel": [
            {"BirimID": "B1", "PersonelID": "P1", "Aktif": 1},
            {"BirimID": "B1", "PersonelID": "P2", "Aktif": 1},
            {"BirimID": "B1", "PersonelID": "P3", "Aktif": 1},
        ],
        "NB_PersonelTercih": [
            {
                "BirimID": "B1",
                "PersonelID": "P3",
                "Yil": 2026,
                "Ay": 3,
                "NobetTercihi": "fazla_mesai_gonullu",
                "HedefTipi": "normal",
            },
        ],
        "NB_Birim": [
            {"BirimID": "B1", "BirimAdi": "Radyoloji"},
        ],
        "Personel": [
            {"KimlikNo": "P1", "AdSoyad": "Personel 1", "GorevYeri": "Radyoloji"},
            {"KimlikNo": "P2", "AdSoyad": "Personel 2", "GorevYeri": "Radyoloji"},
            {"KimlikNo": "P3", "AdSoyad": "Personel 3", "GorevYeri": "Radyoloji"},
        ],
        "Tatiller": [],
        "Izin_Giris": [],
        "NB_Plan": [],
        "NB_PlanSatir": [],
    })


def test_ayni_gunde_ayni_kisiye_ikinci_atama_yapilmaz():
    registry = _algoritma_registry()

    sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

    assert sonuc.basarili is True

    plan_satirlari = registry.get("NB_PlanSatir").get_all()
    gun_kisi_sayaci = Counter(
        (satir["NobetTarihi"], satir["PersonelID"])
        for satir in plan_satirlari
    )

    assert gun_kisi_sayaci
    assert all(adet == 1 for adet in gun_kisi_sayaci.values())


def test_once_tum_personel_yerlesir_kalan_slot_bos_kalir():
    registry = _algoritma_registry()

    sonuc = NbAlgoritma(registry).plan_olustur("B1", 2026, 3)

    assert sonuc.basarili is True

    ilk_gun_satirlari = [
        satir for satir in registry.get("NB_PlanSatir").get_all()
        if satir["NobetTarihi"] == "2026-03-01"
    ]

    assert len(ilk_gun_satirlari) == 3
    assert {satir["PersonelID"] for satir in ilk_gun_satirlari} == {"P1", "P2", "P3"}
    assert any("2026-03-01" in uyari and "doldurulamadı" in uyari
               for uyari in sonuc.veri["uyarilar"])