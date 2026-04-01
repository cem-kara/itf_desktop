# -*- coding: utf-8 -*-
"""
İşten Ayrılık Sayfası
- Personel bilgi özeti
- Ayrılış bilgileri (tarih, neden, ek dosya)
- Kullanılan izinler özeti
- Dosya arşivleme (resim + diplomalar + ek dosya → tek PDF → Eski_Personel)
"""
import os
import tempfile
import shutil
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QProgressBar, QFrame, QComboBox, QDateEdit,
    QGroupBox, QFileDialog, QGridLayout,
    QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QCursor

from core.logger import logger
from core.hata_yonetici import exc_logla, bilgi_goster, hata_goster, uyari_goster, soru_sor
from core.di import get_izin_service, get_dokuman_service, get_fhsz_service, get_personel_service
from core.date_utils import to_ui_date
from ui.styles.icons import IconRenderer


# ═══════════════════════════════════════════════
#  ARŞİV WORKER
# ═══════════════════════════════════════════════

class ArsivWorker(QThread):
    """
    1. Drive'dan mevcut dosyaları (resim, diploma1, diploma2) indir
    2. Ek dosya ile birlikte tek PDF'e birleştir
    3. Eski_Personel klasörüne yükle
    4. Eski Drive dosyalarını sil
    """
    progress = Signal(str)
    finished = Signal(str)   # arşiv_link
    error = Signal(str)

    def __init__(self, personel_data, ek_dosya_path, drive_folders):
        super().__init__()
        self._data = personel_data
        self._ek_dosya = ek_dosya_path
        self._folders = drive_folders

    def run(self):
        tmp_dir = tempfile.mkdtemp(prefix="arsiv_")
        try:
            from database.google import GoogleDriveService
            drive = GoogleDriveService()

            tc = self._data.get("KimlikNo", "")
            ad = self._data.get("AdSoyad", "")

            # ── 1. Mevcut dosyaları indir ──
            downloaded = []
            old_ids = []

            for db_col, label in [("Resim", "Resim"), ("Diploma1", "Diploma1"), ("Diploma2", "Diploma2")]:
                link = str(self._data.get(db_col, "")).strip()
                if not link or not link.startswith("http"):
                    continue
                file_id = drive.extract_file_id(link)
                if not file_id:
                    continue

                self.progress.emit(f"İndiriliyor: {label}...")
                dest = os.path.join(tmp_dir, f"{tc}_{label}.tmp")
                if drive.download_file(file_id, dest):
                    ext = self._detect_ext(dest)
                    final = os.path.join(tmp_dir, f"{tc}_{label}{ext}")
                    os.rename(dest, final)
                    downloaded.append(final)
                    old_ids.append(file_id)

            # Ek dosya
            if self._ek_dosya and os.path.exists(self._ek_dosya):
                downloaded.append(self._ek_dosya)

            if not downloaded:
                self.finished.emit("")
                return

            # ── 2. Tek PDF ──
            self.progress.emit("PDF birleştiriliyor...")
            merged = os.path.join(tmp_dir, f"{tc}_{ad.replace(' ', '_')}_Arsiv.pdf")
            self._merge_to_pdf(downloaded, merged)

            # ── 3. Yükle ──
            arsiv_id = self._folders.get("Eski_Personel", "") or self._folders.get("Personel_Dosya", "")
            link = ""
            if arsiv_id:
                self.progress.emit("Arşive yükleniyor...")
                link = drive.upload_file(
                    merged, parent_folder_id=arsiv_id,
                    custom_name=f"{tc}_{ad.replace(' ', '_')}_Arsiv.pdf"
                ) or ""
            else:
                self.progress.emit("Arşiv klasörü bulunamadı.")

            # ── 4. Eski dosyaları sil (yalnızca arşiv başarıyla yüklendiyse) ──
            if link:
                for fid in old_ids:
                    self.progress.emit("Eski dosyalar temizleniyor...")
                    drive.delete_file(fid)

            self.finished.emit(link)

        except Exception as e:
            exc_logla("IstenAyrilik.Worker", e)
            self.error.emit(str(e))
        finally:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    def _detect_ext(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                h = f.read(8)
            if h[:4] == b'%PDF': return '.pdf'
            if h[:3] == b'\xff\xd8\xff': return '.jpg'
            if h[:8] == b'\x89PNG\r\n\x1a\n': return '.png'
        except Exception:
            pass
        return '.jpg'

    def _merge_to_pdf(self, files, output):
        rl_page_size = None
        rl_canvas_mod = None
        rl_image_reader = None
        pypdf2_mod = None

        try:
            from reportlab.lib.pagesizes import A4 as rl_a4
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.utils import ImageReader as rl_img_reader
            rl_page_size = rl_a4
            rl_canvas_mod = rl_canvas
            rl_image_reader = rl_img_reader
            has_rl = True
        except ImportError:
            has_rl = False

        try:
            import PyPDF2 as pypdf2
            pypdf2_mod = pypdf2
            has_pypdf = True
        except ImportError:
            has_pypdf = False

        tmp_dir = os.path.dirname(output)
        temp_pdfs = []

        for i, f in enumerate(files):
            ext = os.path.splitext(f)[1].lower()
            if ext == '.pdf':
                temp_pdfs.append(f)
            elif ext in ('.jpg', '.jpeg', '.png', '.bmp') and has_rl and rl_canvas_mod and rl_page_size and rl_image_reader:
                pdf_p = os.path.join(tmp_dir, f"_p{i}.pdf")
                try:
                    c = rl_canvas_mod.Canvas(pdf_p, pagesize=rl_page_size)
                    w, h = rl_page_size
                    img = rl_image_reader(f)
                    iw, ih = img.getSize()
                    ratio = min(w / iw, h / ih) * 0.9
                    nw, nh = iw * ratio, ih * ratio
                    c.drawImage(img, (w - nw) / 2, (h - nh) / 2, nw, nh, preserveAspectRatio=True)
                    c.showPage(); c.save()
                    temp_pdfs.append(pdf_p)
                except Exception as e:
                    logger.error(f"Görüntü→PDF hatası: {e}")

        if not temp_pdfs:
            return
        if has_pypdf and pypdf2_mod and len(temp_pdfs) > 1:
            merger = pypdf2_mod.PdfMerger()
            for p in temp_pdfs:
                try:
                    merger.append(p)
                except Exception as e:
                    logger.error(f"PDF ekleme hatası: {e}")
            merger.write(output); merger.close()
        elif temp_pdfs:
            shutil.copy2(temp_pdfs[0], output)


# ═══════════════════════════════════════════════
#  İŞTEN AYRILIK SAYFASI
# ═══════════════════════════════════════════════

class IstenAyrilikPage(QWidget):
    """
    İşten ayrılık sayfası.
    db: SQLiteManager
    personel_data: dict
    on_back: callback → geri dönüş
    """

    def __init__(self, db=None, personel_data=None, on_back=None, parent=None):
        super().__init__(parent)
        self.setProperty("bg-role", "page")
        self._db = db
        self._data = personel_data or {}
        self._on_back = on_back
        self._ek_dosya = ""
        self._drive_folders = {}
        self._arsiv_worker = None
        self._pending_ayrilis_data = None
        self._archive_required = False
        self._dok_svc      = get_dokuman_service(db) if db else None
        self._fhsz_svc     = get_fhsz_service(db) if db else None
        self._izin_svc     = get_izin_service(db) if db else None
        self._personel_svc = get_personel_service(db) if db else None

        self._setup_ui()
        self._load_drive_folders()
        self._load_izin_ozet()

    # ═══════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════

    def _setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 12, 20, 12)
        main.setSpacing(12)

        # ── HEADER ──
        header_frame = QFrame()
        header_frame.setProperty("bg-role", "elevated")
        header_frame.setProperty("style-role", "header")
        hdr = QHBoxLayout(header_frame)
        hdr.setContentsMargins(16, 10, 16, 10)
        hdr.setSpacing(12)

        ad = self._data.get("AdSoyad", "")
        lbl = QLabel(f"Isten Ayrilis - {ad}")
        lbl.setProperty("style-role", "header-name")
        hdr.addWidget(lbl)
        hdr.addStretch()
        main.addWidget(header_frame)

        # ── SCROLL ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setProperty("style-role", "plain")

        content = QWidget()
        content.setProperty("bg-role", "transparent")
        cl = QHBoxLayout(content)
        cl.setSpacing(16)
        cl.setContentsMargins(0, 0, 0, 0)

        # ── SOL: Personel Bilgi + Ayrılış Formu ──
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(12)

        # Personel Özet
        grp_ozet = QGroupBox("Personel Bilgileri")
        grp_ozet.setProperty("style-role", "group")
        og = QGridLayout(grp_ozet)
        og.setSpacing(6)
        og.setContentsMargins(12, 12, 12, 12)

        bilgiler = [
            ("TC Kimlik", self._data.get("KimlikNo", "")),
            ("Ad Soyad", self._data.get("AdSoyad", "")),
            ("Hizmet Sınıfı", self._data.get("HizmetSinifi", "")),
            ("Kadro Ünvanı", self._data.get("KadroUnvani", "")),
            ("Görev Yeri", self._data.get("GorevYeri", "")),
            ("Başlama Tarihi", self._format_date(self._data.get("MemuriyeteBaslamaTarihi", ""))),
        ]
        for i, (lbl_t, val) in enumerate(bilgiler):
            l = QLabel(lbl_t)
            l.setProperty("style-role", "stat-label")
            v = QLabel(str(val))
            v.setProperty("style-role", "stat-value")
            og.addWidget(l, i, 0)
            og.addWidget(v, i, 1)
        left_l.addWidget(grp_ozet)

        # Ayrılış Formu
        grp_form = QGroupBox("Ayrilis Bilgileri")
        grp_form.setProperty("style-role", "group")
        fg = QGridLayout(grp_form)
        fg.setSpacing(10)
        fg.setContentsMargins(12, 12, 12, 12)

        lbl_t = QLabel("Ayrılış Tarihi")
        lbl_t.setProperty("style-role", "form")
        fg.addWidget(lbl_t, 0, 0)
        self.dt_tarih = QDateEdit(QDate.currentDate())
        self.dt_tarih.setCalendarPopup(True)
        self.dt_tarih.setDisplayFormat("dd.MM.yyyy")
        self.dt_tarih.setProperty("style-role", "form")
        fg.addWidget(self.dt_tarih, 0, 1)

        lbl_n = QLabel("Ayrılma Nedeni")
        lbl_n.setProperty("style-role", "form")
        fg.addWidget(lbl_n, 1, 0)
        self.cmb_neden = QComboBox()
        self.cmb_neden.setEditable(True)
        self.cmb_neden.addItems(["Emekli", "Vefat", "İstifa", "Tayin", "Diğer"])
        self.cmb_neden.setProperty("style-role", "form")
        fg.addWidget(self.cmb_neden, 1, 1)

        lbl_d = QLabel("Ek Dosya")
        lbl_d.setProperty("style-role", "form")
        fg.addWidget(lbl_d, 2, 0)
        dosya_h = QHBoxLayout()
        self.btn_dosya = QPushButton("Dosya Sec")
        self.btn_dosya.setProperty("style-role", "upload")
        self.btn_dosya.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_dosya.clicked.connect(self._select_file)
        IconRenderer.set_button_icon(self.btn_dosya, "upload", color="primary", size=14)
        dosya_h.addWidget(self.btn_dosya)
        self.lbl_dosya = QLabel("")
        self.lbl_dosya.setProperty("bg-role", "panel")
        dosya_h.addWidget(self.lbl_dosya, 1)
        fg.addLayout(dosya_h, 2, 1)

        left_l.addWidget(grp_form)

        # Mevcut Dosyalar (Doküman tablosundaki tüm belgeler — sadece liste)
        grp_dosya = QGroupBox("Mevcut Drive Dosyalari")
        grp_dosya.setProperty("style-role", "group")
        dg = QVBoxLayout(grp_dosya)
        dg.setContentsMargins(12, 12, 12, 12)

        tc = self._data.get("KimlikNo", "")
        if not tc or not self._db:
            fallback = QLabel("Doküman listesi yüklenemedi.")
            fallback.setProperty("bg-role", "panel")
            dg.addWidget(fallback)
        else:
            try:
                svc = self._dok_svc
                doks = svc.get_belgeler("personel", tc).veri or [] if svc else []

                table = QTableWidget()
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(["Belge Türü", "Dosya Adı", "Açıklama", "Tarih"])
                table.setMinimumHeight(160)
                table.setAlternatingRowColors(True)
                table.setSelectionBehavior(table.SelectionBehavior.SelectRows)
                table.setSelectionMode(table.SelectionMode.SingleSelection)
                table.setRowCount(len(doks))

                from datetime import datetime
                for r, doc in enumerate(doks):
                    tarih = doc.get("YuklenmeTarihi", "")
                    try:
                        tarih_str = datetime.fromisoformat(tarih).strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        tarih_str = tarih[:16] if len(tarih) > 16 else tarih or "-"

                    table.setItem(r, 0, QTableWidgetItem(doc.get("BelgeTuru", "")))
                    table.setItem(r, 1, QTableWidgetItem(doc.get("Belge") or doc.get("Belge", "")))
                    table.setItem(r, 2, QTableWidgetItem(doc.get("BelgeAciklama", "") or "-"))
                    table.setItem(r, 3, QTableWidgetItem(tarih_str))

                dg.addWidget(table)
            except Exception as e:
                logger.error(f"Dokumanlar yüklenemedi: {e}")
                fallback = QLabel("Doküman listesi yüklenemedi.")
                fallback.setProperty("bg-role", "panel")
                dg.addWidget(fallback)

        left_l.addWidget(grp_dosya)

        left_l.addStretch()

        # ── SAĞ: İzin Özeti + Onay ──
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(12)

        # İzin Özeti
        grp_izin = QGroupBox("Izin Ozeti")
        grp_izin.setProperty("style-role", "group")
        ig = QGridLayout(grp_izin)
        ig.setSpacing(4)
        ig.setContentsMargins(12, 12, 12, 12)

        lbl_y = QLabel("YILLIK İZİN")
        lbl_y.setProperty("style-role", "section-title")
        ig.addWidget(lbl_y, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
        self.lbl_y_toplam = self._add_stat(ig, 1, "Toplam Hak", "stat_value")
        self.lbl_y_kul = self._add_stat(ig, 2, "Kullanılan", "stat_red")
        self.lbl_y_kal = self._add_stat(ig, 3, "Kalan", "stat_green")

        sep = QFrame(); sep.setFixedHeight(1); sep.setProperty("bg-role", "separator")
        ig.addWidget(sep, 4, 0, 1, 2)

        lbl_s = QLabel("ŞUA İZNİ")
        lbl_s.setProperty("style-role", "section-title")
        ig.addWidget(lbl_s, 5, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
        self.lbl_s_kul = self._add_stat(ig, 6, "Kullanılan", "stat_red")
        self.lbl_s_kal = self._add_stat(ig, 7, "Kalan", "stat_green")

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setProperty("bg-role", "separator")
        ig.addWidget(sep2, 8, 0, 1, 2)
        self.lbl_diger = self._add_stat(ig, 9, "Rapor / Mazeret", "stat-value")

        ig.setRowStretch(10, 1)
        right_l.addWidget(grp_izin)

        # Uyarı + Buton
        grp_onay = QGroupBox("Islemi Onayla")
        grp_onay.setProperty("style-role", "group")
        onay_l = QVBoxLayout(grp_onay)
        onay_l.setSpacing(12)
        onay_l.setContentsMargins(12, 12, 12, 12)

        uyari = QLabel(
            "Bu işlem:\n"
            "• Personeli PASİF duruma getirecek\n"
            "• Tüm dosyaları (resim, diploma, ek) tek PDF olarak arşivleyecek\n"
            "• Arşivi Eski Personel klasörüne taşıyacak\n"
            "• Eski Drive dosyalarını silecek"
        )
        uyari.setWordWrap(True)
        uyari.setProperty("bg-role", "panel")
        onay_l.addWidget(uyari)

        self.btn_onayla = QPushButton("ONAYLA VE BITIR")
        self.btn_onayla.setProperty("style-role", "danger")
        self.btn_onayla.setFixedHeight(30)
        self.btn_onayla.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_onayla.clicked.connect(self._on_confirm)
        IconRenderer.set_button_icon(self.btn_onayla, "alert_triangle", color="primary", size=14)
        onay_l.addWidget(self.btn_onayla)

        right_l.addWidget(grp_onay)
        right_l.addStretch()

        cl.addWidget(left, 1)
        cl.addWidget(right, 1)
        scroll.setWidget(content)
        main.addWidget(scroll, 1)

        # Progress
        self.progress = QProgressBar()
        self.progress.setFixedHeight(16)
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setProperty("style-role", "danger")
        main.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setProperty("color-role", "muted")
        self.lbl_status.setProperty("bg-role", "panel")
        main.addWidget(self.lbl_status)

    def _add_stat(self, grid, row, text, style_key):
        lbl = QLabel(text)
        lbl.setProperty("style-role", "stat-label")
        grid.addWidget(lbl, row, 0)
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val.setProperty("style-role", style_key)
        grid.addWidget(val, row, 1)
        return val

    def _format_date(self, val):
        return to_ui_date(val, "—")

    # ═══════════════════════════════════════════
    #  VERİ YÜKLEME
    # ═══════════════════════════════════════════

    def _load_drive_folders(self):
        if not self._db:
            return
        try:
            fhsz_svc = self._fhsz_svc
            sabit_repo = fhsz_svc.get_sabitler_repo().veri if fhsz_svc else None
            all_sabit = sabit_repo.get_all() if sabit_repo else []
            self._drive_folders = {
                str(r.get("MenuEleman") or "").strip(): str(r.get("Aciklama") or "").strip()
                for r in all_sabit
                if isinstance(r, dict)
                and r.get("Kod") == "Sistem_DriveID"
                and str(r.get("Aciklama") or "").strip()
            }
        except Exception as e:
            logger.error(f"Drive klasör yükleme hatası: {e}")

    def _load_izin_ozet(self):
        tc = self._data.get("KimlikNo", "")
        if not self._db or not tc:
            return
        try:
            izin_svc = self._izin_svc
            izin_repo = izin_svc.get_izin_bilgi_repo().veri if izin_svc else None
            izin = izin_repo.get_by_id(tc) if izin_repo else None
            if izin:
                self.lbl_y_toplam.setText(str(izin.get("YillikToplamHak", "0")))
                self.lbl_y_kul.setText(str(izin.get("YillikKullanilan", "0")))
                self.lbl_y_kal.setText(str(izin.get("YillikKalan", "0")))
                self.lbl_s_kul.setText(str(izin.get("SuaKullanilan", "0")))
                self.lbl_s_kal.setText(str(izin.get("SuaKalan", "0")))
                self.lbl_diger.setText(str(izin.get("RaporMazeretTop", "0")))
        except Exception as e:
            logger.error(f"İzin özet yükleme hatası: {e}")

    # ═══════════════════════════════════════════
    #  DOSYA SEÇ
    # ═══════════════════════════════════════════

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ek Dosya Seç", "",
            "Dosyalar (*.pdf *.jpg *.jpeg *.png *.doc *.docx);;Tüm Dosyalar (*)"
        )
        if path:
            self._ek_dosya = path
            self.lbl_dosya.setText(os.path.basename(path))

    # ═══════════════════════════════════════════
    #  ONAYLA
    # ═══════════════════════════════════════════

    def _on_confirm(self):
        ad = self._data.get("AdSoyad", "")
        neden = self.cmb_neden.currentText().strip()
        if not neden:
            uyari_goster(self, "Ayrılma nedeni seçilmeli.", "Eksik")
            return

        cevap = soru_sor(
            self,
            f"{ad} personeli PASİF yapılacak ve dosyaları arşivlenecek.\n\n"
            f"Neden: {neden}\n"
            f"Tarih: {self.dt_tarih.date().toString('dd.MM.yyyy')}\n\n"
            "Devam etmek istiyor musunuz?",
            "Son Onay",
        )
        if not cevap:
            return

        self._pending_ayrilis_data = {
            "AyrilisTarihi": self.dt_tarih.date().toString("yyyy-MM-dd"),
            "AyrilmaNedeni": neden,
            "Durum": "Pasif",
        }

        # Güvenli mod: Arşiv gerekiyorsa önce arşiv, sonra pasife alma
        self._archive_required = self._has_archive_source()
        if not self._archive_required:
            self._finalize_departure("")
            return

        # 2. Arşivleme başlat
        self.progress.setVisible(True)
        self.btn_onayla.setEnabled(False)
        self.lbl_status.setText("Arşivleme başlatıldı...")

        self._arsiv_worker = ArsivWorker(
            personel_data=self._data,
            ek_dosya_path=self._ek_dosya,
            drive_folders=self._drive_folders
        )
        self._arsiv_worker.progress.connect(self._on_progress)
        self._arsiv_worker.finished.connect(self._on_finished)
        self._arsiv_worker.error.connect(self._on_error)
        self._arsiv_worker.start()

    def _on_progress(self, msg):
        self.lbl_status.setText(msg)
        logger.info(f"Arşiv: {msg}")

    def _on_finished(self, arsiv_link):
        self.progress.setVisible(False)
        self.btn_onayla.setEnabled(True)

        ad = self._data.get("AdSoyad", "")

        if self._archive_required and not arsiv_link:
            self.lbl_status.setText("Arşiv oluşturulamadı. Personel pasife alınmadı.")
            uyari_goster(
                self,
                f"{ad} için arşiv yüklenemedi.\n"
                "Güvenli mod nedeniyle personel pasife alınmadı.",
                "Arşiv Uyarısı",
            )
            return

        self._finalize_departure(arsiv_link)

    def _on_error(self, hata):
        self.progress.setVisible(False)
        self.btn_onayla.setEnabled(True)
        self.lbl_status.setText(f"Arsiv hatasi: {hata}")
        logger.error(f"Arşiv hatası: {hata}")
        uyari_goster(
            self,
            f"Arşivleme hatası oluştu:\n{hata}\n\n"
            "Güvenli mod nedeniyle personel pasife alınmadı.",
            "Arşiv Uyarısı",
        )

    def _has_archive_source(self):
        if self._ek_dosya and os.path.exists(self._ek_dosya):
            return True
        for col in ("Resim", "Diploma1", "Diploma2"):
            link = str(self._data.get(col, "")).strip()
            if link.startswith("http"):
                return True
        return False

    def _finalize_departure(self, arsiv_link):
        tc = self._data.get("KimlikNo", "")
        ad = self._data.get("AdSoyad", "")
        ayrilis_data = self._pending_ayrilis_data or {
            "AyrilisTarihi": self.dt_tarih.date().toString("yyyy-MM-dd"),
            "AyrilmaNedeni": self.cmb_neden.currentText().strip(),
            "Durum": "Pasif",
        }

        update_data = dict(ayrilis_data)
        if arsiv_link:
            update_data.update({
                "OzlukDosyasi": arsiv_link,
                "Resim": "",
                "Diploma1": "",
                "Diploma2": "",
            })

        try:
            personel_svc = self._personel_svc
            if personel_svc:
                repo_sonuc = personel_svc.get_personel_repo()
                if repo_sonuc.basarili and repo_sonuc.veri:
                    repo_sonuc.veri.update(tc, update_data)
            self._data.update(update_data)
            logger.info(f"Personel pasif (güvenli mod): {tc}")
        except Exception as e:
            logger.error(f"Güvenli mod DB güncelleme hatası: {e}")
            hata_goster(self, f"Güncelleme hatası:\n{e}")
            return

        self.lbl_status.setText("Islem tamamlandi.")
        bilgi_goster(
            self,
            f"{ad} personeli PASİF duruma getirildi.\n"
            f"{'Dosyaları arşivlendi.' if arsiv_link else 'Arşivlenecek dosya bulunamadı.'}",
            "Tamamlandı",
        )
        self._go_back()

    # ═══════════════════════════════════════════
    #  GERİ
    # ═══════════════════════════════════════════

    def _go_back(self):
        if self._on_back:
            self._on_back()
