# -*- coding: utf-8 -*-
"""RKE Raporlama — Background Worker Threads."""
from typing import List, Dict
from PySide6.QtCore import QThread, Signal
from core.logger import logger
from .rke_rapor_utils import pdf_olustur, html_genel_rapor, html_hurda_rapor
import datetime


# ════════════════════════════════════════════════════════════════════
#  WORKER THREADS
# ════════════════════════════════════════════════════════════════════
class RaporVeriYukleyici(QThread):
    """Rapor verilerini yüklemek için async worker."""
    veri_hazir = Signal(list, list, list, list, list)
    hata_olustu = Signal(str)

    def __init__(self, rke_repo=None, muayene_repo=None, parent=None):
        super().__init__(parent)
        self.rke_repo = rke_repo
        self.muayene_repo = muayene_repo

    def run(self):
        try:
            env = {}
            abd_s = set()
            birim_s = set()
            tarih_s = set()
            
            if self.rke_repo:
                for r in self.rke_repo.get_all():
                    en = str(r.get('EkipmanNo', '')).strip()
                    if en:
                        env[en] = {
                            'ABD': str(r.get('AnaBilimDali', '')).strip(),
                            'Birim': str(r.get('Birim', '')).strip(),
                            'Cins': str(r.get('KoruyucuCinsi', '')).strip(),
                            'Pb': str(r.get('KursunEsdegeri', '')).strip()
                        }
                        if env[en]['ABD']:
                            abd_s.add(env[en]['ABD'])
                        if env[en]['Birim']:
                            birim_s.add(env[en]['Birim'])

            birlesik = []
            ws2_data = self.muayene_repo.get_all() if self.muayene_repo else []
            if ws2_data:
                for r in ws2_data:
                    en = str(r.get('EkipmanNo', '')).strip()
                    tarih = str(r.get('FMuayeneTarihi') or r.get('F_MuayeneTarihi') or r.get('MuayeneTarihi') or '').strip()
                    fiz = str(r.get('FizikselDurum', '')).strip()
                    sko = str(r.get('SkopiDurum', '')).strip()
                    if tarih:
                        tarih_s.add(tarih)
                    item = {
                        'EkipmanNo': en,
                        'Tarih': tarih,
                        'Fiziksel': fiz,
                        'Skopi': sko,
                        'KontrolEden': str(r.get('KontrolEden', '')).strip(),
                        'Aciklama': str(r.get('Aciklamalar', '')).strip(),
                        'Sonuc': "Kullanıma Uygun"
                    }
                    if "Değil" in fiz or "Değil" in sko:
                        item['Sonuc'] = "Kullanıma Uygun Değil"
                    item.update(env.get(en, {'ABD': '-', 'Birim': '-', 'Cins': '-', 'Pb': '-'}))
                    birlesik.append(item)

            st = sorted(tarih_s, reverse=True)
            headers = ["Ekipman No", "Cins", "Pb", "Birim", "Tarih", "Fiziksel", "Skopi", "Sonuç"]
            self.veri_hazir.emit(birlesik, headers, sorted(abd_s), sorted(birim_s), st)
        except Exception as e:
            self.hata_olustu.emit(str(e))


class RaporOlusturucuWorker(QThread):
    """PDF Rapor oluşturma worker'ı."""
    log_mesaji = Signal(str)
    islem_bitti = Signal()

    def __init__(self, mod: int, veriler: List[Dict], filtreler: Dict):
        super().__init__()
        self.mod = mod
        self.veriler = veriler
        self.filtreler = filtreler

    def run(self):
        try:
            ozet = self.filtreler.get('ozet', '')
            
            if self.mod == 1:
                f = f"RKE_Genel_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
                if not self.veriler:
                    self.log_mesaji.emit("⚠  Veri yok.")
                    return
                if pdf_olustur(html_genel_rapor(self.veriler, ozet), f):
                    self.log_mesaji.emit(f"✓  Genel rapor oluşturuldu: {f}")
                else:
                    self.log_mesaji.emit("✗  PDF oluşturulamadı.")

            elif self.mod == 2:
                f = f"RKE_Hurda_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
                hv = [v for v in self.veriler if "Değil" in v.get('Sonuc', '')]
                if not hv:
                    self.log_mesaji.emit("⚠  Hurda kaydı yok.")
                    return
                if pdf_olustur(html_hurda_rapor(hv, ozet), f):
                    self.log_mesaji.emit(f"✓  Hurda raporu oluşturuldu: {f}")

            elif self.mod == 3:
                gruplar: Dict = {}
                for item in self.veriler:
                    gruplar.setdefault((item.get('KontrolEden', ''), item.get('Tarih', '')), []).append(item)
                self.log_mesaji.emit(f"{len(gruplar)} rapor oluşturuluyor...")
                for (kisi, tarih), liste in gruplar.items():
                    f = f"Rapor_{kisi}_{tarih}.pdf".replace(" ", "_")
                    if pdf_olustur(html_genel_rapor(liste, f"Kontrolör: {kisi} – {tarih}"), f):
                        self.log_mesaji.emit(f"✓  {f}")
        except Exception as e:
            self.log_mesaji.emit(f"✗  HATA: {e}")
        finally:
            self.islem_bitti.emit()
