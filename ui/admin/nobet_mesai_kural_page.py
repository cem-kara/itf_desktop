# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.di import get_nb_mesai_service
from core.hata_yonetici import bilgi_goster, hata_logla_goster, soru_sor, uyari_goster


class NobetMesaiKuralPage(QWidget):
    """Kurum-genel nöbet mesai/bildirim kuralı yönetim ekranı."""

    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._ag = action_guard
        self._mesai_svc = get_nb_mesai_service(db) if db else None
        self.setProperty("bg-role", "page")
        self._build()
        self._kural_yukle()

    def _build(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(16, 16, 16, 16)
        ana.setSpacing(12)

        ana.addWidget(self._build_header())
        ana.addWidget(self._build_form_panel())
        ana.addStretch()

    def _build_header(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        baslik = QLabel("Mesai Kuralı")
        baslik.setProperty("style-role", "title")
        layout.addWidget(baslik)

        alt = QLabel(
            "Bu ekran kurum geneli aylık hedef, bildirim eşiği ve kapanış politikasını yönetir. "
            "Ücret hesaplamaz; sadece bildirim ve devir davranışını belirler."
        )
        alt.setWordWrap(True)
        alt.setProperty("color-role", "muted")
        layout.addWidget(alt)
        return panel

    def _build_form_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("bg-role", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._spn_hedef_saat = QSpinBox()
        self._spn_hedef_saat.setRange(0, 400)
        self._spn_hedef_saat.setSuffix(" saat")
        self._spn_hedef_saat.setValue(0)
        form.addRow("Sabit Aylık Hedef:", self._spn_hedef_saat)

        self._lbl_hedef_ipucu = QLabel(
            "0 bırakılırsa her personel için o ayın iş günü × günlük çalışma saati ile "
            "otomatik hesaplanır (izin günleri düşülür)."
        )
        self._lbl_hedef_ipucu.setWordWrap(True)
        self._lbl_hedef_ipucu.setProperty("color-role", "muted")
        form.addRow("", self._lbl_hedef_ipucu)

        self._spn_bildirim_esik = QSpinBox()
        self._spn_bildirim_esik.setRange(0, 400)
        self._spn_bildirim_esik.setSuffix(" saat")
        self._spn_bildirim_esik.setValue(12)
        form.addRow("Bildirim Eşiği:", self._spn_bildirim_esik)

        self._cmb_bildirim_temeli = QComboBox()
        self._cmb_bildirim_temeli.addItem("Sadece bu ay farkı", userData="donem_farki")
        self._cmb_bildirim_temeli.addItem("Net bakiye", userData="net_bakiye")
        form.addRow("Bildirim Temeli:", self._cmb_bildirim_temeli)

        self._cmb_kapanis = QComboBox()
        self._cmb_kapanis.addItem("Devret", userData="devret")
        self._cmb_kapanis.addItem("Tam ödeme ile 0'la", userData="tam_odeme_sifirla")
        self._cmb_kapanis.addItem("İzin ile 0'la", userData="izinle_sifirla")
        form.addRow("Kapanış Politikası:", self._cmb_kapanis)

        self._chk_negatif_devir = QCheckBox("Negatif bakiye sonraki aya devretsin")
        self._chk_negatif_devir.setChecked(True)
        form.addRow("Negatif Devir:", self._chk_negatif_devir)

        layout.addLayout(form)

        self._lbl_gecerlilik = QLabel("")
        self._lbl_gecerlilik.setProperty("color-role", "muted")
        layout.addWidget(self._lbl_gecerlilik)

        self._lbl_ozet = QLabel("")
        self._lbl_ozet.setWordWrap(True)
        self._lbl_ozet.setProperty("color-role", "muted")
        layout.addWidget(self._lbl_ozet)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addStretch()

        self._btn_yenile = QPushButton("Yükle")
        self._btn_yenile.setProperty("style-role", "secondary")
        self._btn_yenile.setFixedHeight(30)
        self._btn_yenile.clicked.connect(self._kural_yukle)
        btns.addWidget(self._btn_yenile)

        self._btn_kaydet = QPushButton("Kuralı Kaydet")
        self._btn_kaydet.setProperty("style-role", "action")
        self._btn_kaydet.setFixedHeight(30)
        self._btn_kaydet.clicked.connect(self._kural_kaydet)
        btns.addWidget(self._btn_kaydet)

        layout.addLayout(btns)
        return panel

    def _combo_set_user_data(self, combo: QComboBox, value: str):
        hedef = str(value or "")
        for idx in range(combo.count()):
            if str(combo.itemData(idx) or "") == hedef:
                combo.setCurrentIndex(idx)
                return

    def _kural_yukle(self):
        if not self._mesai_svc:
            return
        try:
            sonuc = self._mesai_svc.get_kurum_genel_kural(date.today().isoformat())
            if not sonuc.basarili:
                self._lbl_gecerlilik.setText(
                    "Aktif kural bulunamadı. Varsayılan değerler gösteriliyor."
                )
                self._lbl_ozet.setText(
                    "İlk kayıtla birlikte bu ayın başından itibaren geçerli yeni kurum kuralı oluşturulur."
                )
                return

            veri = sonuc.veri or {}
            self._spn_hedef_saat.setValue(int(int(veri.get("sabit_hedef_dakika", 0)) / 60))
            self._spn_bildirim_esik.setValue(int(int(veri.get("bildirim_esik_dakika", 0)) / 60))
            self._combo_set_user_data(
                self._cmb_bildirim_temeli,
                str(veri.get("bildirim_temeli", "donem_farki")),
            )
            self._combo_set_user_data(
                self._cmb_kapanis,
                str(veri.get("kapanis_politikasi", "devret")),
            )
            self._chk_negatif_devir.setChecked(bool(veri.get("negatif_devir_izinli", True)))

            self._lbl_gecerlilik.setText(
                f"Geçerlilik başlangıcı: {veri.get('GeserlilikBaslangic', '-') or '-'}"
            )
            hedef_saat = int(int(veri.get("sabit_hedef_dakika", 0)) / 60)
            hedef_str = f"{hedef_saat} saat (sabit)" if hedef_saat > 0 else "otomatik (iş günü × günlük saat)"
            self._lbl_ozet.setText(
                f"Aktif kural: {veri.get('KuralAdi', 'Kurum Genel Mesai Kuralı')} | "
                f"Hedef: {hedef_str} | "
                f"Eşik {int(int(veri.get('bildirim_esik_dakika', 0)) / 60)} saat | "
                f"Temel: {'Net bakiye' if str(veri.get('bildirim_temeli', '')) == 'net_bakiye' else 'Bu ay farkı'} | "
                f"Kapanış: {self._cmb_kapanis.currentText()}"
            )
        except Exception as exc:
            hata_logla_goster(self, "NobetMesaiKuralPage._kural_yukle", exc)

    def _kural_kaydet(self):
        if not self._mesai_svc:
            return
        try:
            if not soru_sor(
                self,
                "Kurum-genel mesai kuralı kaydedilecek. Yeni hesaplamalar bu kurala göre yapılacak. Devam edilsin mi?",
            ):
                return

            bugun = date.today()
            sonuc = self._mesai_svc.kurum_genel_kural_kaydet(
                aylik_hedef_saat=int(self._spn_hedef_saat.value()),
                bildirim_esik_saat=int(self._spn_bildirim_esik.value()),
                bildirim_temeli=str(self._cmb_bildirim_temeli.currentData() or "donem_farki"),
                kapanis_politikasi=str(self._cmb_kapanis.currentData() or "devret"),
                negatif_devir_izinli=bool(self._chk_negatif_devir.isChecked()),
                gecerlilik_baslangic=f"{bugun.year:04d}-{bugun.month:02d}-01",
            )
            if not sonuc.basarili:
                uyari_goster(self, sonuc.mesaj or "Kural kaydedilemedi.")
                return

            self._kural_yukle()
            bilgi_goster(self, "Kurum-genel mesai kuralı kaydedildi.")
        except Exception as exc:
            hata_logla_goster(self, "NobetMesaiKuralPage._kural_kaydet", exc)