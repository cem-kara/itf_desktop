# -*- coding: utf-8 -*-
"""RKE muayene worker threads."""

import os
import time
import datetime
from typing import List, Dict

from PySide6.QtCore import QThread, Signal

from core.paths import DB_PATH
from core.storage.storage_service import StorageService
from database.repository_registry import RepositoryRegistry
from ui.styles.colors import DarkTheme

from .rke_muayene_utils import envanter_durumunu_belirle

try:
    from dateutil.relativedelta import relativedelta
    from core.logger import logger
    from database.google import veritabani_getir
except Exception:
    import logging
    logger = logging.getLogger("RKEMuayene")
    def veritabani_getir(vt, sayfa):
        return None
    class relativedelta:
        def __init__(self, **kw):
            self.years = kw.get("years", 0)
        def __radd__(self, dt):
            return dt.replace(year=dt.year + self.years)


class VeriYukleyici(QThread):
    veri_hazir = Signal(list, list, dict, list, list, list, list, list)
    hata_olustu = Signal(str)

    def __init__(self, db_path=None, use_sheets=True):
        super().__init__()
        self._db_path = db_path or DB_PATH
        self._use_sheets = use_sheets

    @staticmethod
    def _repo_muayene_to_table(rows: List[Dict]):
        if not rows:
            return [], []
        headers = [
            "KayitNo", "EkipmanNo", "F_MuayeneTarihi", "FizikselDurum",
            "S_MuayeneTarihi", "SkopiDurum", "Aciklamalar",
            "KontrolEden/Unvani", "BirimSorumlusu/Unvani", "Not", "Rapor"
        ]
        data = []
        for r in rows:
            data.append([
                r.get("KayitNo", ""),
                r.get("EkipmanNo", ""),
                r.get("FMuayeneTarihi", ""),
                r.get("FizikselDurum", ""),
                r.get("SMuayeneTarihi", ""),
                r.get("SkopiDurum", ""),
                r.get("Aciklamalar", ""),
                r.get("KontrolEdenUnvani", ""),
                r.get("BirimSorumlusuUnvani", ""),
                r.get("Notlar", ""),
                r.get("Rapor", ""),
            ])
        return headers, data

    @staticmethod
    def _find_header_index(headers: List[str], *candidates: str) -> int:
        for name in candidates:
            if name in headers:
                return headers.index(name)
        return -1

    def run(self):
        try:
            rke_data, rke_combo, rke_dict = [], [], {}
            muayene_listesi, headers = [], []
            teknik_aciklamalar = []
            kontrol_edenler, birim_sorumlulari = set(), set()

            db = None
            rke_repo = None
            muayene_repo = None
            if not self._use_sheets:
                from database.sqlite_manager import SQLiteManager
                from core.di import get_registry
                db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
                registry = get_registry(db)
                rke_repo = registry.get("RKE_List")
                muayene_repo = registry.get("RKE_Muayene")

            ws_rke = None
            ws_muayene = None
            ws_sabit = None
            if self._use_sheets:
                try:
                    ws_rke = veritabani_getir("rke", "rke_list")
                except Exception:
                    ws_rke = None
                try:
                    ws_muayene = veritabani_getir("rke", "rke_muayene")
                except Exception:
                    ws_muayene = None
                try:
                    ws_sabit = veritabani_getir("sabit", "Sabitler")
                except Exception:
                    ws_sabit = None

            if ws_rke:
                rke_data = ws_rke.get_all_records()
            elif rke_repo:
                rke_data = rke_repo.get_all()

            for row in rke_data:
                ekipman_no = str(row.get("EkipmanNo", "")).strip()
                cins = str(row.get("KoruyucuCinsi", "")).strip()
                if ekipman_no:
                    display = f"{ekipman_no} | {cins}"
                    rke_combo.append(display)
                    rke_dict[display] = ekipman_no

            if ws_muayene:
                raw = ws_muayene.get_all_values()
                if raw:
                    headers = [str(h).strip() for h in raw[0]]
                    muayene_listesi = raw[1:]
            elif muayene_repo:
                headers, muayene_listesi = self._repo_muayene_to_table(muayene_repo.get_all())

            if headers and muayene_listesi:
                idx_k = self._find_header_index(headers, "KontrolEden/Unvani", "KontrolEden")
                idx_s = self._find_header_index(headers, "BirimSorumlusu/Unvani", "BirimSorumlusu")
                for row in muayene_listesi:
                    if idx_k != -1 and len(row) > idx_k:
                        val = str(row[idx_k]).strip()
                        if val:
                            kontrol_edenler.add(val)
                    if idx_s != -1 and len(row) > idx_s:
                        val = str(row[idx_s]).strip()
                        if val:
                            birim_sorumlulari.add(val)

            if ws_sabit:
                for s in ws_sabit.get_all_records():
                    if str(s.get("Kod", "")).strip() == "RKE_Teknik":
                        eleman = str(s.get("MenuEleman", "")).strip()
                        if eleman:
                            teknik_aciklamalar.append(eleman)
            elif db:
                try:
                    rows = db.execute("SELECT Kod, MenuEleman FROM Sabitler").fetchall()
                    for s in rows:
                        if str(s["Kod"]).strip() == "RKE_Teknik":
                            eleman = str(s["MenuEleman"]).strip()
                            if eleman:
                                teknik_aciklamalar.append(eleman)
                except Exception:
                    pass

            if not teknik_aciklamalar:
                teknik_aciklamalar = ["Yirtik Yok", "Kursun Butunlugu Tam", "Askilar Saglam", "Temiz"]

            self.veri_hazir.emit(
                rke_data, sorted(rke_combo), rke_dict,
                muayene_listesi, headers, sorted(teknik_aciklamalar),
                sorted(kontrol_edenler), sorted(birim_sorumlulari)
            )
            if db:
                db.close()
        except Exception as e:
            self.hata_olustu.emit(str(e))


class KayitWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, veri_dict, dosya_yolu, db_path=None, use_sheets=True):
        super().__init__()
        self.veri = veri_dict
        self.dosya_yolu = dosya_yolu
        self._db_path = db_path or DB_PATH
        self._use_sheets = use_sheets

    def run(self):
        try:
            drive_link = "-"
            upload_result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry
            db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
            registry = get_registry(db)

            if self.dosya_yolu and os.path.exists(self.dosya_yolu):
                storage = StorageService(db)
                upload_result = storage.upload(
                    file_path=self.dosya_yolu,
                    folder_name="RKE_Rapor",
                    custom_name=os.path.basename(self.dosya_yolu)
                )
                drive_link = upload_result.get("drive_link") or upload_result.get("local_path") or "-"

                if upload_result.get("mode") != "none":
                    try:
                        repo_doc = registry.get("Dokumanlar")
                        repo_doc.insert({
                            "EntityType": "rke",
                            "EntityId": str(self.veri.get("EkipmanNo", "")),
                            "BelgeTuru": "Rapor",
                            "Belge": os.path.basename(self.dosya_yolu),
                            "DocType": "RKE_Rapor",
                            "DisplayName": os.path.basename(self.dosya_yolu),
                            "LocalPath": upload_result.get("local_path") or "",
                            "DrivePath": upload_result.get("drive_link") or "",
                            "BelgeAciklama": "",
                            "YuklenmeTarihi": datetime.datetime.now().isoformat(),
                            "IliskiliBelgeID": self.veri.get("KayitNo"),
                            "IliskiliBelgeTipi": "RKE_Muayene",
                        })
                    except Exception as e:
                        logger.warning(f"Dokumanlar kaydi eklenemedi: {e}")

            rke_repo = None
            muayene_repo = None
            if not self._use_sheets:
                rke_repo = registry.get("RKE_List")
                muayene_repo = registry.get("RKE_Muayene")

            if self._use_sheets:
                ws_muayene = veritabani_getir("rke", "rke_muayene")
                if not ws_muayene:
                    raise Exception("Veritabani baglantisi yok.")

                satir = [
                    self.veri["KayitNo"], self.veri["EkipmanNo"],
                    self.veri["F_MuayeneTarihi"], self.veri["FizikselDurum"],
                    self.veri["S_MuayeneTarihi"], self.veri["SkopiDurum"],
                    self.veri["Aciklamalar"], self.veri["KontrolEden"],
                    self.veri["BirimSorumlusu"], self.veri["Not"], drive_link
                ]
                ws_muayene.append_row(satir)

                ws_list = veritabani_getir("rke", "rke_list")
                if ws_list:
                    cell = ws_list.find(self.veri["EkipmanNo"])
                    if cell:
                        yeni_durum = envanter_durumunu_belirle(
                            self.veri["FizikselDurum"], self.veri["SkopiDurum"])
                        gelecek = ""
                        skopi_str = self.veri["S_MuayeneTarihi"]
                        if skopi_str:
                            try:
                                dt_obj = datetime.datetime.strptime(skopi_str, "%Y-%m-%d")
                                gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                            except Exception:
                                gelecek = skopi_str

                        hdrs = ws_list.row_values(1)
                        def ci(name):
                            try:
                                return hdrs.index(name) + 1
                            except Exception:
                                return -1
                        if (c := ci("KontrolTarihi")) > 0 and gelecek:
                            ws_list.update_cell(cell.row, c, gelecek)
                        if (c := ci("Durum")) > 0:
                            ws_list.update_cell(cell.row, c, yeni_durum)
                        if (c := ci("Aciklama")) > 0:
                            ws_list.update_cell(cell.row, c, self.veri["Aciklamalar"])
            else:
                if not muayene_repo:
                    raise Exception("Veritabani baglantisi yok.")
                muayene_data = {
                    "KayitNo": self.veri.get("KayitNo"),
                    "EkipmanNo": self.veri.get("EkipmanNo"),
                    "FMuayeneTarihi": self.veri.get("F_MuayeneTarihi"),
                    "FizikselDurum": self.veri.get("FizikselDurum"),
                    "SMuayeneTarihi": self.veri.get("S_MuayeneTarihi"),
                    "SkopiDurum": self.veri.get("SkopiDurum"),
                    "Aciklamalar": self.veri.get("Aciklamalar"),
                    "KontrolEdenUnvani": self.veri.get("KontrolEden"),
                    "BirimSorumlusuUnvani": self.veri.get("BirimSorumlusu"),
                    "Notlar": self.veri.get("Not"),
                    "Rapor": drive_link,
                }
                muayene_repo.insert(muayene_data)

                if rke_repo:
                    yeni_durum = envanter_durumunu_belirle(
                        self.veri["FizikselDurum"], self.veri["SkopiDurum"])
                    gelecek = ""
                    skopi_str = self.veri["S_MuayeneTarihi"]
                    if skopi_str:
                        try:
                            dt_obj = datetime.datetime.strptime(skopi_str, "%Y-%m-%d")
                            gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                        except Exception:
                            gelecek = skopi_str
                    update_data = {"Durum": yeni_durum, "Aciklama": self.veri.get("Aciklamalar", "")}
                    if gelecek:
                        update_data["KontrolTarihi"] = gelecek
                    rke_repo.update(self.veri["EkipmanNo"], update_data)

            self.finished.emit("Kayit ve guncelleme basarili.")
            if db:
                db.close()
        except Exception as e:
            self.error.emit(str(e))


class TopluKayitWorker(QThread):
    progress = Signal(int, int)
    finished = Signal()
    error = Signal(str)

    def __init__(self, ekipman_listesi, ortak_veri, dosya_yolu, fiziksel_aktif, skopi_aktif, db_path=None, use_sheets=True):
        super().__init__()
        self.ekipman_listesi = ekipman_listesi
        self.ortak_veri = ortak_veri
        self.dosya_yolu = dosya_yolu
        self.fiziksel_aktif = fiziksel_aktif
        self.skopi_aktif = skopi_aktif
        self._db_path = db_path or DB_PATH
        self._use_sheets = use_sheets

    def run(self):
        try:
            drive_link = "-"
            upload_result = {"mode": "none", "drive_link": "", "local_path": "", "error": ""}

            from database.sqlite_manager import SQLiteManager
            from core.di import get_registry
            db = SQLiteManager(db_path=self._db_path, check_same_thread=True)
            registry = get_registry(db)

            if self.dosya_yolu and os.path.exists(self.dosya_yolu):
                storage = StorageService(db)
                upload_result = storage.upload(
                    file_path=self.dosya_yolu,
                    folder_name="RKE_Rapor",
                    custom_name=os.path.basename(self.dosya_yolu)
                )
                drive_link = upload_result.get("drive_link") or upload_result.get("local_path") or "-"

            rke_repo = None
            muayene_repo = None
            if not self._use_sheets:
                rke_repo = registry.get("RKE_List")
                muayene_repo = registry.get("RKE_Muayene")

            if self._use_sheets:
                ws_muayene = veritabani_getir("rke", "rke_muayene")
                ws_list = veritabani_getir("rke", "rke_list")
                if not ws_muayene or not ws_list:
                    raise Exception("Veritabani baglantisi yok.")

                hdrs = ws_list.row_values(1)
                def ci(name):
                    try:
                        return hdrs.index(name) + 1
                    except Exception:
                        return -1
                col_tarih = ci("KontrolTarihi")
                col_durum = ci("Durum")
                col_aciklama = ci("Aciklama")
                try:
                    col_ekipman = hdrs.index("EkipmanNo") + 1
                except Exception:
                    col_ekipman = 2
                all_ekipman = ws_list.col_values(col_ekipman)

                rows_to_add, batch_updates = [], []
                base_time = int(time.time())

                for idx, ekipman_no in enumerate(self.ekipman_listesi):
                    unique_id = f"M-{base_time}-{idx}"
                    f_tarih = self.ortak_veri["F_MuayeneTarihi"] if self.fiziksel_aktif else ""
                    f_durum = self.ortak_veri["FizikselDurum"] if self.fiziksel_aktif else ""
                    s_tarih = self.ortak_veri["S_MuayeneTarihi"] if self.skopi_aktif else ""
                    s_durum = self.ortak_veri["SkopiDurum"] if self.skopi_aktif else ""

                    rows_to_add.append([
                        unique_id, ekipman_no, f_tarih, f_durum, s_tarih, s_durum,
                        self.ortak_veri["Aciklamalar"], self.ortak_veri["KontrolEden"],
                        self.ortak_veri["BirimSorumlusu"], self.ortak_veri["Not"], drive_link
                    ])

                    try:
                        row_num = all_ekipman.index(ekipman_no) + 1
                        yeni_genel = envanter_durumunu_belirle(f_durum, s_durum)
                        gelecek = ""
                        if s_tarih:
                            try:
                                dt_obj = datetime.datetime.strptime(s_tarih, "%Y-%m-%d")
                                gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                            except Exception:
                                gelecek = s_tarih
                        if col_tarih > 0 and gelecek:
                            batch_updates.append({"range": f"{chr(64+col_tarih)}{row_num}", "values": [[gelecek]]})
                        if col_durum > 0:
                            batch_updates.append({"range": f"{chr(64+col_durum)}{row_num}", "values": [[yeni_genel]]})
                        if col_aciklama > 0:
                            batch_updates.append({
                                "range": f"{chr(64+col_aciklama)}{row_num}",
                                "values": [[self.ortak_veri["Aciklamalar"]]],
                            })
                    except ValueError:
                        pass

                    self.progress.emit(idx + 1, len(self.ekipman_listesi))

                ws_muayene.append_rows(rows_to_add)
                if batch_updates:
                    ws_list.batch_update(batch_updates)
                self.finished.emit()
            else:
                if not muayene_repo:
                    raise Exception("Veritabani baglantisi yok.")
                base_time = int(time.time())
                for idx, ekipman_no in enumerate(self.ekipman_listesi):
                    unique_id = f"M-{base_time}-{idx}"
                    f_tarih = self.ortak_veri["F_MuayeneTarihi"] if self.fiziksel_aktif else ""
                    f_durum = self.ortak_veri["FizikselDurum"] if self.fiziksel_aktif else ""
                    s_tarih = self.ortak_veri["S_MuayeneTarihi"] if self.skopi_aktif else ""
                    s_durum = self.ortak_veri["SkopiDurum"] if self.skopi_aktif else ""

                    muayene_data = {
                        "KayitNo": unique_id,
                        "EkipmanNo": ekipman_no,
                        "FMuayeneTarihi": f_tarih,
                        "FizikselDurum": f_durum,
                        "SMuayeneTarihi": s_tarih,
                        "SkopiDurum": s_durum,
                        "Aciklamalar": self.ortak_veri["Aciklamalar"],
                        "KontrolEdenUnvani": self.ortak_veri["KontrolEden"],
                        "BirimSorumlusuUnvani": self.ortak_veri["BirimSorumlusu"],
                        "Notlar": self.ortak_veri["Not"],
                        "Rapor": drive_link,
                    }
                    muayene_repo.insert(muayene_data)

                    if rke_repo:
                        yeni_genel = envanter_durumunu_belirle(f_durum, s_durum)
                        gelecek = ""
                        if s_tarih:
                            try:
                                dt_obj = datetime.datetime.strptime(s_tarih, "%Y-%m-%d")
                                gelecek = (dt_obj + relativedelta(years=1)).strftime("%Y-%m-%d")
                            except Exception:
                                gelecek = s_tarih
                        update_data = {"Durum": yeni_genel, "Aciklama": self.ortak_veri.get("Aciklamalar", "")}
                        if gelecek:
                            update_data["KontrolTarihi"] = gelecek
                        rke_repo.update(ekipman_no, update_data)

                    if upload_result.get("mode") != "none":
                        try:
                            repo_doc = registry.get("Dokumanlar")
                            repo_doc.insert({
                                "EntityType": "rke",
                                "EntityId": str(ekipman_no),
                                "BelgeTuru": "Rapor",
                                "Belge": os.path.basename(self.dosya_yolu),
                                "DocType": "RKE_Rapor",
                                "DisplayName": os.path.basename(self.dosya_yolu),
                                "LocalPath": upload_result.get("local_path") or "",
                                "DrivePath": upload_result.get("drive_link") or "",
                                "BelgeAciklama": "",
                                "YuklenmeTarihi": datetime.datetime.now().isoformat(),
                                "IliskiliBelgeID": unique_id,
                                "IliskiliBelgeTipi": "RKE_Muayene",
                            })
                        except Exception as e:
                            logger.warning(f"Dokumanlar kaydi eklenemedi: {e}")

                self.finished.emit()
            if db:
                db.close()
        except Exception as e:
            self.error.emit(str(e))
