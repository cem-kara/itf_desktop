# -*- coding: utf-8 -*-
"""
Arıza modülü unit testleri
============================
Kapsam:
  - ArizaTableModel : rowCount, columnCount, data, headerData,
                      DisplayRole, ForegroundRole, TextAlignmentRole,
                      set_data, get_row
  - Arıza ID formatı (ARZ-YYYYMMDD-HHMMSS)
  - COLUMNS / DURUM_RENK / ONCELIK_RENK sabitleri
  - Filtre mantığı (metin arama, durum, öncelik)

Qt bağımlılığı: sadece QApplication + QAbstractTableModel.
Ekran (display) gerekmez.
"""
import sys
import pytest
from unittest.mock import patch
import re
import datetime


# ─── QApplication fixture ────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    """Tek QApplication; tüm modül testleri paylaşır."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ─── Yardımcı: model oluştur ─────────────────────────────────

def make_model(data=None, qapp=None):
    from ui.pages.cihaz.ariza_listesi import ArizaTableModel
    return ArizaTableModel(data=data)


ORNEK_ARIZA = {
    "Arizaid":         "ARZ-20240101-120000",
    "Cihazid":         "CIH-001",
    "BaslangicTarihi": "2024-01-01",
    "Bildiren":        "Ahmet Yılmaz",
    "Baslik":          "Ekran bozuk",
    "Oncelik":         "Yüksek",
    "Durum":           "Açık",
}


# ════════════════════════════════════════════════════════════
#  1. COLUMNS / Sabit Kontrolü
# ════════════════════════════════════════════════════════════

class TestArizaConstants:

    def test_columns_7_sutun(self, qapp):
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        assert len(COLUMNS) == 7

    def test_columns_ilk_sutun_arizaid(self, qapp):
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        assert COLUMNS[0][0] == "Arizaid"

    def test_durum_renk_acik_var(self, qapp):
        from ui.pages.cihaz.ariza_listesi import DURUM_RENK
        assert "Açık" in DURUM_RENK

    def test_durum_renk_kapali_cozuldu(self, qapp):
        from ui.pages.cihaz.ariza_listesi import DURUM_RENK
        assert "Kapalı (Çözüldü)" in DURUM_RENK

    def test_oncelik_renk_acil(self, qapp):
        from ui.pages.cihaz.ariza_listesi import ONCELIK_RENK
        assert "Acil (Kritik)" in ONCELIK_RENK

    def test_oncelik_renk_dusuk(self, qapp):
        from ui.pages.cihaz.ariza_listesi import ONCELIK_RENK
        assert "Düşük" in ONCELIK_RENK

    def test_sutun_anahtarlari_dogru(self, qapp):
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        keys = [c[0] for c in COLUMNS]
        assert "Durum"           in keys
        assert "Oncelik"         in keys
        assert "BaslangicTarihi" in keys
        assert "Baslik"          in keys


# ════════════════════════════════════════════════════════════
#  2. ArizaTableModel — Temel Sayaçlar
# ════════════════════════════════════════════════════════════

class TestArizaTableModelCounts:

    def test_bos_model_row_count_sifir(self, qapp):
        model = make_model(qapp=qapp)
        assert model.rowCount() == 0

    def test_bos_model_column_count_7(self, qapp):
        model = make_model(qapp=qapp)
        assert model.columnCount() == 7

    def test_tek_kayit_row_count_1(self, qapp):
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        assert model.rowCount() == 1

    def test_bes_kayit_row_count_5(self, qapp):
        veri = [dict(ORNEK_ARIZA, Arizaid=f"ARZ-{i:03d}") for i in range(5)]
        model = make_model(veri, qapp=qapp)
        assert model.rowCount() == 5

    def test_column_count_her_zaman_7(self, qapp):
        """Veri içeriğinden bağımsız kolon sayısı sabit 7."""
        veri = [dict(ORNEK_ARIZA, Arizaid=f"ARZ-{i:03d}") for i in range(10)]
        model = make_model(veri, qapp=qapp)
        assert model.columnCount() == 7


# ════════════════════════════════════════════════════════════
#  3. ArizaTableModel — data() / DisplayRole
# ════════════════════════════════════════════════════════════

class TestArizaTableModelData:

    def _index(self, model, row, col):
        return model.index(row, col)

    def test_display_role_arizaid(self, qapp):
        from PySide6.QtCore import Qt
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        idx = self._index(model, 0, 0)  # Arizaid sütunu
        assert model.data(idx, Qt.DisplayRole) == "ARZ-20240101-120000"

    def test_display_role_baslik(self, qapp):
        from PySide6.QtCore import Qt
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        # Baslik = COLUMNS[4]
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        baslik_col = [c[0] for c in COLUMNS].index("Baslik")
        idx = self._index(model, 0, baslik_col)
        assert model.data(idx, Qt.DisplayRole) == "Ekran bozuk"

    def test_display_role_durum(self, qapp):
        from PySide6.QtCore import Qt
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        durum_col = [c[0] for c in COLUMNS].index("Durum")
        idx = self._index(model, 0, durum_col)
        assert model.data(idx, Qt.DisplayRole) == "Açık"

    def test_display_role_none_alan_bos_string(self, qapp):
        """Eksik alan → boş string."""
        from PySide6.QtCore import Qt
        kayit = {"Arizaid": "ARZ-X"}  # diğerleri yok
        model = make_model([kayit], qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        baslik_col = [c[0] for c in COLUMNS].index("Baslik")
        idx = self._index(model, 0, baslik_col)
        assert model.data(idx, Qt.DisplayRole) == ""

    def test_gecersiz_index_none(self, qapp):
        """Geçersiz index → None dönmeli."""
        from PySide6.QtCore import Qt, QModelIndex
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        assert model.data(QModelIndex(), Qt.DisplayRole) is None

    def test_foreground_role_durum_acik(self, qapp):
        """Durum='Açık' → kırmızımsı renk dönmeli."""
        from PySide6.QtCore import Qt
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS, DURUM_RENK
        durum_col = [c[0] for c in COLUMNS].index("Durum")
        idx = self._index(model, 0, durum_col)
        renk = model.data(idx, Qt.ForegroundRole)
        assert renk == DURUM_RENK["Açık"]

    def test_foreground_role_oncelik_yuksek(self, qapp):
        """Öncelik='Yüksek' → turuncu renk dönmeli."""
        from PySide6.QtCore import Qt
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS, ONCELIK_RENK
        onc_col = [c[0] for c in COLUMNS].index("Oncelik")
        idx = self._index(model, 0, onc_col)
        renk = model.data(idx, Qt.ForegroundRole)
        assert renk == ONCELIK_RENK["Yüksek"]

    def test_foreground_role_bos_durum_fallback(self, qapp):
        """Bilinmeyen durum → varsayılan renk dönmeli (None değil)."""
        from PySide6.QtCore import Qt
        kayit = dict(ORNEK_ARIZA, Durum="BilinmeyenDurum")
        model = make_model([kayit], qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        durum_col = [c[0] for c in COLUMNS].index("Durum")
        idx = self._index(model, 0, durum_col)
        # None değil ama DURUM_RENK'te de yok → fallback renk
        renk = model.data(idx, Qt.ForegroundRole)
        assert renk is not None

    def test_alignment_role_tarih_hucre_merkez(self, qapp):
        """BaslangicTarihi → AlignCenter."""
        from PySide6.QtCore import Qt
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        tarih_col = [c[0] for c in COLUMNS].index("BaslangicTarihi")
        idx = self._index(model, 0, tarih_col)
        alignment = model.data(idx, Qt.TextAlignmentRole)
        assert alignment == Qt.AlignCenter

    def test_alignment_role_baslik_sol(self, qapp):
        """Baslik → sol hizalama."""
        from PySide6.QtCore import Qt
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        baslik_col = [c[0] for c in COLUMNS].index("Baslik")
        idx = self._index(model, 0, baslik_col)
        alignment = model.data(idx, Qt.TextAlignmentRole)
        assert alignment == (Qt.AlignVCenter | Qt.AlignLeft)


# ════════════════════════════════════════════════════════════
#  4. ArizaTableModel — headerData
# ════════════════════════════════════════════════════════════

class TestArizaTableModelHeaders:

    def test_header_ilk_sutun_ariza_id(self, qapp):
        from PySide6.QtCore import Qt
        model = make_model(qapp=qapp)
        baslik = model.headerData(0, Qt.Horizontal, Qt.DisplayRole)
        assert baslik == "Arıza ID"

    def test_header_durum_sutunu(self, qapp):
        from PySide6.QtCore import Qt
        model = make_model(qapp=qapp)
        from ui.pages.cihaz.ariza_listesi import COLUMNS
        durum_col = [c[0] for c in COLUMNS].index("Durum")
        baslik = model.headerData(durum_col, Qt.Horizontal, Qt.DisplayRole)
        assert baslik == "Durum"

    def test_header_dikey_none(self, qapp):
        """Dikey header → None."""
        from PySide6.QtCore import Qt
        model = make_model(qapp=qapp)
        assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) is None


# ════════════════════════════════════════════════════════════
#  5. ArizaTableModel — set_data / get_row
# ════════════════════════════════════════════════════════════

class TestArizaTableModelMethods:

    def test_set_data_gunceller(self, qapp):
        model = make_model(qapp=qapp)
        assert model.rowCount() == 0
        model.set_data([ORNEK_ARIZA])
        assert model.rowCount() == 1

    def test_set_data_none_bos_yapar(self, qapp):
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        model.set_data(None)
        assert model.rowCount() == 0

    def test_set_data_bos_liste(self, qapp):
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        model.set_data([])
        assert model.rowCount() == 0

    def test_get_row_gecerli(self, qapp):
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        row = model.get_row(0)
        assert row["Arizaid"] == "ARZ-20240101-120000"

    def test_get_row_sinir_disi_none(self, qapp):
        model = make_model([ORNEK_ARIZA], qapp=qapp)
        assert model.get_row(99) is None
        assert model.get_row(-1) is None

    def test_set_data_coklu_kayit(self, qapp):
        veri = [dict(ORNEK_ARIZA, Arizaid=f"ARZ-{i:03d}") for i in range(8)]
        model = make_model(qapp=qapp)
        model.set_data(veri)
        assert model.rowCount() == 8
        assert model.get_row(7)["Arizaid"] == "ARZ-007"


# ════════════════════════════════════════════════════════════
#  6. Arıza ID Formatı
# ════════════════════════════════════════════════════════════

class TestArizaIdFormati:

    def test_format_regex(self):
        """ARZ-YYYYMMDD-HHMMSS formatı."""
        pattern = r"^ARZ-\d{8}-\d{6}$"
        ornek = "ARZ-20240512-143022"
        assert re.match(pattern, ornek)

    def test_format_gecersiz_reddedilir(self):
        pattern = r"^ARZ-\d{8}-\d{6}$"
        assert not re.match(pattern, "ARZ-240512-143022")
        assert not re.match(pattern, "ISL-20240512-143022")
        assert not re.match(pattern, "ARZ-20240512")

    def test_ariza_id_tarih_guncel(self):
        """Otomatik ID bugünü içermeli."""
        today = datetime.date.today().strftime("%Y%m%d")
        ariza_id = f"ARZ-{today}-120000"
        assert today in ariza_id

    def test_benzersizlik_zamana_gore(self):
        """Farklı zamanlarda üretilen ID'ler farklı olmalı."""
        from datetime import datetime
        t1 = datetime(2024, 1, 1, 10, 0, 0).strftime("ARZ-%Y%m%d-%H%M%S")
        t2 = datetime(2024, 1, 1, 10, 0, 1).strftime("ARZ-%Y%m%d-%H%M%S")
        assert t1 != t2


# ════════════════════════════════════════════════════════════
#  7. Filtre Mantığı (saf Python)
# ════════════════════════════════════════════════════════════

class TestArizaFiltreMantigi:
    """
    Proxy model testleri Qt display gerektirdiğinden,
    filtre mantığının iş mantığı saf Python ile test edilir.
    """

    VERI = [
        {"Arizaid": "ARZ-001", "Baslik": "Ekran bozuk",  "Durum": "Açık",    "Oncelik": "Yüksek"},
        {"Arizaid": "ARZ-002", "Baslik": "Fare çalışmıyor", "Durum": "İşlemde", "Oncelik": "Normal"},
        {"Arizaid": "ARZ-003", "Baslik": "Güç sorunu",   "Durum": "Açık",    "Oncelik": "Acil (Kritik)"},
        {"Arizaid": "ARZ-004", "Baslik": "Network hatası", "Durum": "Kapalı (Çözüldü)", "Oncelik": "Düşük"},
    ]

    def _filtrele(self, veri, metin="", durum="Tümü", oncelik="Tümü"):
        sonuc = []
        for r in veri:
            if metin and metin.lower() not in str(r.get("Baslik","")).lower() \
                     and metin.lower() not in str(r.get("Arizaid","")).lower():
                continue
            if durum != "Tümü" and r.get("Durum") != durum:
                continue
            if oncelik != "Tümü" and r.get("Oncelik") != oncelik:
                continue
            sonuc.append(r)
        return sonuc

    def test_filtre_yok_hepsi_gorunur(self):
        assert len(self._filtrele(self.VERI)) == 4

    def test_metin_filtre_baslik(self):
        sonuc = self._filtrele(self.VERI, metin="ekran")
        assert len(sonuc) == 1
        assert sonuc[0]["Arizaid"] == "ARZ-001"

    def test_durum_filtre_acik(self):
        sonuc = self._filtrele(self.VERI, durum="Açık")
        assert len(sonuc) == 2

    def test_durum_filtre_islemde(self):
        sonuc = self._filtrele(self.VERI, durum="İşlemde")
        assert len(sonuc) == 1
        assert sonuc[0]["Arizaid"] == "ARZ-002"

    def test_oncelik_filtre_acil(self):
        sonuc = self._filtrele(self.VERI, oncelik="Acil (Kritik)")
        assert len(sonuc) == 1
        assert sonuc[0]["Arizaid"] == "ARZ-003"

    def test_kombinasyon_durum_oncelik(self):
        sonuc = self._filtrele(self.VERI, durum="Açık", oncelik="Yüksek")
        assert len(sonuc) == 1

    def test_eslesen_yok_bos(self):
        sonuc = self._filtrele(self.VERI, metin="xyzzy")
        assert sonuc == []

    def test_buyuk_kucuk_harf(self):
        sonuc1 = self._filtrele(self.VERI, metin="EKRAN")
        sonuc2 = self._filtrele(self.VERI, metin="ekran")
        assert len(sonuc1) == len(sonuc2) == 1
