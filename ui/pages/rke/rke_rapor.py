# -*- coding: utf-8 -*-
"""RKE Raporlama Merkezi - mockup tasarim dili."""
import datetime
from typing import List, Dict, Optional

from PySide6.QtCore  import Qt, QThread, Signal, QMarginsF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
    QTableView, QHeaderView, QLabel, QPushButton, QComboBox,
    QRadioButton, QButtonGroup, QFrame, QApplication, QMessageBox,
)
from PySide6.QtGui import (
    QColor, QCursor, QTextDocument, QPdfWriter,
    QPageSize, QPageLayout,
)

from core.logger import logger
from core.di import get_rke_service as _get_rke_service
from core.paths import DB_PATH
from ui.components.base_table_model import BaseTableModel
from ui.styles.colors import DarkTheme
from ui.styles.icons import IconRenderer

# ==================================================================
#  PALETTE
# ==================================================================
_BG0  = DarkTheme.BG_PRIMARY; _BG1 = DarkTheme.BG_PRIMARY; _BG2 = DarkTheme.BG_SECONDARY; _BG3 = DarkTheme.BG_ELEVATED
_BD   = DarkTheme.BORDER_PRIMARY; _BD2 = DarkTheme.BORDER_PRIMARY
_TX0  = DarkTheme.TEXT_PRIMARY; _TX1 = DarkTheme.TEXT_SECONDARY; _TX2 = DarkTheme.TEXT_MUTED
_RED  = DarkTheme.STATUS_ERROR; _AMBER= DarkTheme.STATUS_WARNING; _GREEN= DarkTheme.STATUS_SUCCESS
_BLUE = DarkTheme.ACCENT; _CYAN = DarkTheme.ACCENT2; _PURP = DarkTheme.RKE_PURP
_MONO = DarkTheme.MONOSPACE

# _S_COMBO kaldırıldı — global QSS kuralı geçerli
# _S_TABLE kaldırıldı — global QSS kuralı geçerli


# ==================================================================
#  PDF SABLONLARI (degismedi)
# ==================================================================
def _css():
    return ("body{font-family:'Times New Roman',serif;font-size:11pt;color:#000;}"
            "h1{text-align:center;font-size:14pt;font-weight:bold;margin-bottom:5px;}"
            "h2{font-size:12pt;font-weight:bold;margin-top:15px;margin-bottom:5px;text-decoration:underline;}"
            ".c{text-align:center;}"
            "table{width:100%;border-collapse:collapse;margin-top:10px;font-size:10pt;}"
            "th,td{border:1px solid #000;padding:4px;text-align:center;vertical-align:middle;}"
            "th{background:#f0f0f0;font-weight:bold;}.l{text-align:left;}"
            ".sig{width:100%;border:none;margin-top:40px;}"
            ".sig td{border:none;text-align:center;vertical-align:top;padding:20px;}"
            ".line{border-top:1px solid #000;width:80%;margin:30px auto 0;}"
            ".legal{text-align:justify;margin:5px 0;line-height:1.4;}")


def html_genel_rapor(veriler: List[Dict], filtre_ozeti: str) -> str:
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows = "".join(
        f"<tr><td>{r['Cins']}</td><td>{r['EkipmanNo']}</td><td>{r['Pb']}</td>"
        f"<td>{r['Tarih']}<br>{r['Fiziksel']}</td><td>{r['Tarih']}<br>{r['Skopi']}</td>"
        f"<td class='l'>{r['Aciklama']}</td></tr>"
        for r in veriler
    )
    return (f"<html><head><style>{_css()}</style></head><body>"
            f"<h1>RADYASYON KORUYUCU EKİPMAN (RKE) KONTROL RAPORU</h1>"
            f"<div class='c'>Filtre: {filtre_ozeti} | Rapor Tarihi: {tarih}</div>"
            f"<table><thead><tr>"
            f"<th width='15%'>Koruyucu Cinsi</th><th width='15%'>Koruyucu No</th>"
            f"<th width='10%'>Pb (mm)</th><th width='20%'>Fiziksel Kontrol</th>"
            f"<th width='20%'>Skopi Kontrol</th><th width='20%'>Açıklama</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
            f"<table class='sig'><tr>"
            f"<td><b>Kontrol Eden</b><div class='line'>İmza</div></td>"
            f"<td><b>Birim Sorumlusu</b><div class='line'>İmza</div></td>"
            f"<td><b>RKS</b><div class='line'>İmza</div></td>"
            f"</tr></table></body></html>")


def html_hurda_rapor(veriler: List[Dict], filtre_ozeti: str) -> str:
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    rows = "".join(
        f"<tr><td>{i}</td><td>{r['Cins']}</td><td>{r['EkipmanNo']}</td>"
        f"<td>{r['Birim']}</td><td>{r['Pb']}</td>"
        f"<td class='l'>{' | '.join(filter(None,['Fiziksel: '+r['Fiziksel'] if 'Değil' in r['Fiziksel'] else '',' Skopi: '+r['Skopi'] if 'Değil' in r['Skopi'] else '',r['Aciklama']]))}</td></tr>"
        for i, r in enumerate(veriler, 1)
    )
    return (f"<html><head><style>{_css()}</style></head><body>"
            f"<h1>HURDA (HEK) EKİPMAN TEKNİK RAPORU</h1>"
            f"<div class='c'>Tarih: {tarih}</div>"
            f"<h2>A. İMHA EDİLECEK EKİPMAN LİSTESİ</h2>"
            f"<table><thead><tr>"
            f"<th width='5%'>Sira</th><th width='20%'>Malzeme Adi</th>"
            f"<th width='15%'>Barkod/Demirbas</th><th width='15%'>Bolum</th>"
            f"<th width='10%'>Pb (mm)</th><th width='35%'>Uygunsuzluk</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
            f"<h2>B. TEKNİK RAPOR</h2>"
            f"<div class='legal'>Yukarıdaki ekipmanların fiziksel veya radyolojik bütünlüklerini "
            f"yitirdikleri tespit edilmistir. HEK kaydina alinmasi arz olunur.</div>"
            f"<table class='sig'><tr>"
            f"<td><b>Kontrol Eden</b><div class='line'>İmza</div></td>"
            f"<td><b>Birim Sorumlusu</b><div class='line'>İmza</div></td>"
            f"<td><b>RKS</b><div class='line'>İmza</div></td>"
            f"</tr></table></body></html>")


def pdf_olustur(html: str, dosya: str) -> bool:
    try:
        doc = QTextDocument(); doc.setHtml(html)
        w = QPdfWriter(dosya); w.setPageSize(QPageSize(QPageSize.PageSizeId.A4)); w.setResolution(300)
        lay = QPageLayout()
        lay.setPageSize(QPageSize(QPageSize.PageSizeId.A4)); lay.setOrientation(QPageLayout.Orientation.Portrait)
        lay.setMargins(QMarginsF(15,15,15,15)); w.setPageLayout(lay)
        doc.print_(w); return True
    except Exception as e:
        logger.error(f"PDF: {e}"); return False


# ==================================================================
#  WORKER THREADS (is mantigi degismedi)
# ==================================================================
class RaporVeriYukleyici(QThread):
    veri_hazir  = Signal(list, list, list, list, list)
    hata_olustu = Signal(str)

    def __init__(self, db_path=None, parent=None):
        super().__init__(parent)
        self.db_path = db_path or DB_PATH

    def run(self):
        db = None
        try:
            env={}; abd_s=set(); birim_s=set(); tarih_s=set()
            from database.sqlite_manager import SQLiteManager

            db = SQLiteManager(db_path=self.db_path, check_same_thread=True)
            rke_svc = _get_rke_service(db)
            rke_repo = rke_svc.get_rke_repo()
            muayene_repo = rke_svc.get_muayene_repo()

            if rke_repo:
                for r in rke_repo.get_all():
                    en=str(r.get('EkipmanNo','')).strip()
                    if en:
                        env[en]={'ABD':str(r.get('AnaBilimDali','')).strip(),
                                 'Birim':str(r.get('Birim','')).strip(),
                                 'Cins':str(r.get('KoruyucuCinsi','')).strip(),
                                 'Pb':str(r.get('KursunEsdegeri','')).strip()}
                        if env[en]['ABD']:   abd_s.add(env[en]['ABD'])
                        if env[en]['Birim']: birim_s.add(env[en]['Birim'])

            birlesik=[]
            ws2_data = muayene_repo.get_all() if muayene_repo else []
            if ws2_data:
                for r in ws2_data:
                    en=str(r.get('EkipmanNo','')).strip()
                    tarih=str(r.get('FMuayeneTarihi') or r.get('F_MuayeneTarihi') or r.get('MuayeneTarihi') or '').strip()
                    fiz=str(r.get('FizikselDurum','')).strip()
                    sko=str(r.get('SkopiDurum','')).strip()
                    if tarih: tarih_s.add(tarih)
                    item={'EkipmanNo':en,'Tarih':tarih,'Fiziksel':fiz,'Skopi':sko,
                          'KontrolEden':str(r.get('KontrolEden','')).strip(),
                          'Aciklama':str(r.get('Aciklamalar','')).strip(),
                          'Sonuc':"Kullanıma Uygun"}
                    if "Değil" in fiz or "Değil" in sko: item['Sonuc']="Kullanıma Uygun Değil"
                    item.update(env.get(en,{'ABD':'-','Birim':'-','Cins':'-','Pb':'-'}))
                    birlesik.append(item)

            st=sorted(tarih_s,reverse=True)
            headers=["Ekipman No","Cins","Pb","Birim","Tarih","Fiziksel","Skopi","Sonuç"]
            self.veri_hazir.emit(birlesik,headers,sorted(abd_s),sorted(birim_s),st)
        except Exception as e:
            self.hata_olustu.emit(str(e))
        finally:
            if db:
                db.conn.close()

class RaporOlusturucuWorker(QThread):
    log_mesaji  = Signal(str)
    islem_bitti = Signal()

    def __init__(self, mod:int, veriler:List[Dict], filtreler:Dict):
        super().__init__(); self.mod=mod; self.veriler=veriler; self.filtreler=filtreler

    def run(self):
        try:
            ozet=self.filtreler.get('ozet','')
            if self.mod==1:
                f=f"RKE_Genel_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
                if not self.veriler: self.log_mesaji.emit("Uyari: Veri yok."); return
                if pdf_olustur(html_genel_rapor(self.veriler,ozet),f):
                    self.log_mesaji.emit(f"OK - Genel rapor olusturuldu: {f}")
                else: self.log_mesaji.emit("Hata: PDF olusturulamadi.")

            elif self.mod==2:
                f=f"RKE_Hurda_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
                hv=[v for v in self.veriler if "Değil" in v.get('Sonuc','')]
                if not hv: self.log_mesaji.emit("Uyari: Hurda kaydi yok."); return
                if pdf_olustur(html_hurda_rapor(hv,ozet),f):
                    self.log_mesaji.emit(f"OK - Hurda raporu olusturuldu: {f}")

            elif self.mod==3:
                gruplar:Dict={}
                for item in self.veriler:
                    gruplar.setdefault((item.get('KontrolEden',''),item.get('Tarih','')),
                                      []).append(item)
                self.log_mesaji.emit(f"{len(gruplar)} rapor olusturuluyor...")
                for (kisi,tarih),liste in gruplar.items():
                    f=f"Rapor_{kisi}_{tarih}.pdf".replace(" ","_")
                    if pdf_olustur(html_genel_rapor(liste,f"Kontrolor: {kisi} - {tarih}"),f):
                        self.log_mesaji.emit(f"OK - {f}")
        except Exception as e:
            self.log_mesaji.emit(f"HATA: {e}")
        finally:
            self.islem_bitti.emit()

#  TABLO MODELİ
# ==================================================================
_RCOLS = [
    ("EkipmanNo","EKİPMAN NO",130),
    ("Cins",     "CİNS",     110),
    ("Pb",       "Pb",         70),
    ("Birim",    "BİRİM",    110),
    ("Tarih",    "TARİH",    100),
    ("Sonuc",    "SONUC",    130),
    ("Aciklama", "ACIKLAMA", 160),
]
_RK=[c[0] for c in _RCOLS]; _RH=[c[1] for c in _RCOLS]; _RW=[c[2] for c in _RCOLS]


class RaporTableModel(BaseTableModel):
    def __init__(self,rows=None,parent=None):
        super().__init__(_RCOLS, rows, parent)

    def _display(self, key, row):
        return str(row.get(key, ""))

    def _fg(self, key, row):
        if key == "Sonuc":
            return QColor(_RED) if "Değil" in row.get(key, "") else QColor(_GREEN)
        return None

    def _align(self, key):
        if key in ("Tarih", "Sonuc", "Pb"):
            return Qt.AlignmentFlag.AlignCenter
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

    def set_rows(self, rows):
        self.set_data(rows)

    def get_row(self, idx):
        return self._data[idx] if 0 <= idx < len(self._data) else None


# ==================================================================
#  ANA PENCERE
# ==================================================================
class RKERaporPenceresi(QWidget):
    def __init__(self, db=None, action_guard=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._action_guard = action_guard
        self.setWindowTitle("RKE Raporlama Merkezi")
        self.resize(1200, 820)
        self.setStyleSheet("background:{};color:{};".format(_BG1, _TX0))

        self.ham_veriler:       List[Dict]=[]
        self.filtrelenmis_veri: List[Dict]=[]
        self._kpi:              Dict[str,QLabel]={}
        
        # Filtre widget'ları için tip tanımları
        self.cmb_abd: QComboBox
        self.cmb_birim: QComboBox
        self.cmb_tarih: QComboBox
        
        # Repository'leri hazırla
        self._registry = None
        self._rke_repo = None
        self._muayene_repo = None
        self._db_path = getattr(self._db, "db_path", DB_PATH)
        if self._db:
            try:

                self._rke_svc = _get_rke_service(self._db)
                self._rke_repo = self._rke_svc.get_rke_repo()
                self._muayene_repo = self._rke_svc.get_muayene_repo()
            except Exception as e:
                logger.error(f"Repository baslatma hatasi: {e}")

        self._setup_ui()
        # YetkiYoneticisi.uygula(self,"rke_rapor")  # TODO: Yetki sistemi entegrasyonu

    # LAYOUT
    def _setup_ui(self):
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._mk_kpi_bar())
        root.addWidget(self._mk_control_panel())
        root.addWidget(self._mk_table_panel(),1)

    # KPI
    def _mk_kpi_bar(self) -> QWidget:
        bar=QWidget(); bar.setFixedHeight(68)
        bar.setStyleSheet("border-bottom: 1px solid {};".format(_BD))
        hl=QHBoxLayout(bar); hl.setContentsMargins(0,0,0,0); hl.setSpacing(1)
        for key,title,val,color in [
            ("toplam","TOPLAM KAYIT","0",_BLUE),
            ("uygun","KULLANIMA UYGUN","0",_GREEN),
            ("uygun_d","UYGUN DEĞİL","0",_RED),
            ("hurda_a","HURDA ADAYI","0",_AMBER),
            ("kaynak","FARKLI EKİPMAN","0",_TX2),
        ]:
            hl.addWidget(self._mk_kpi_card(key,title,val,color),1)
        return bar

    def _mk_kpi_card(self,key,title,val,color) -> QWidget:
        w=QWidget(); w.setStyleSheet("background:{};".format(_BG1))
        hl=QHBoxLayout(w); hl.setContentsMargins(0,0,0,0); hl.setSpacing(0)
        accent=QFrame(); accent.setFixedWidth(3)
        accent.setStyleSheet("border: none;")
        content=QWidget(); content.setStyleSheet("background:{};".format(_BG1))
        vl=QVBoxLayout(content); vl.setContentsMargins(14,8,14,8); vl.setSpacing(2)
        lt=QLabel(title)
        lt.setStyleSheet("color:{};background:transparent;font-family:{};"
                         "font-size:8px;font-weight:700;letter-spacing:2px;".format(_TX2, _MONO))
        lv=QLabel(val)
        lv.setStyleSheet("color:{};background:transparent;font-family:{};"
                         "font-size:20px;font-weight:700;".format(color, _MONO))
        vl.addWidget(lt); vl.addWidget(lv)
        hl.addWidget(accent); hl.addWidget(content,1)
        self._kpi[key]=lv; return w

    # KONTROL PANELI
    def _mk_control_panel(self) -> QWidget:
        outer=QWidget(); outer.setFixedHeight(110)
        outer.setStyleSheet("border-bottom: 1px solid {};".format(_BD))
        hl=QHBoxLayout(outer); hl.setContentsMargins(16,10,16,10); hl.setSpacing(20)

        # Rapor Turu
        sec_widget=QWidget(); sec_widget.setStyleSheet("background:transparent;")
        sec_widget.setFixedWidth(280)
        sv=QVBoxLayout(sec_widget); sv.setContentsMargins(0,0,0,0); sv.setSpacing(6)
        sec_lbl=QLabel("RAPOR TURU")
        sec_lbl.setStyleSheet("color:{};font-family:{};font-size:8px;"
                              "font-weight:700;letter-spacing:2px;".format(_TX2, _MONO))
        sv.addWidget(sec_lbl)

        rb_ss=(f"QRadioButton{{color:{_TX1};font-family:{_MONO};font-size:11px;padding:3px;}}"
               f"QRadioButton::indicator{{width:14px;height:14px;border-radius:7px;"
               f"border:2px solid {_BD2};background:{_BG3};}}"
               f"QRadioButton::indicator:checked{{background:{_PURP};border-color:{_PURP};}}"
               f"QRadioButton:hover{{color:{_TX0};}}")
        self.rb_genel=QRadioButton("A. Kontrol Raporu (Genel)"); self.rb_genel.setChecked(True)
        self.rb_hurda=QRadioButton("B. Hurda (HEK) Raporu")
        self.rb_kisi =QRadioButton("C. Personel Bazlı Raporlar")
        self.bg=QButtonGroup(self)
        for rb in (self.rb_genel,self.rb_hurda,self.rb_kisi):
            rb.setStyleSheet(rb_ss); self.bg.addButton(rb); sv.addWidget(rb)
        self.bg.buttonClicked.connect(self.filtrele)
        hl.addWidget(sec_widget)

        # dikey ayraç
        sep=QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background:{};width:1px;".format(_BD))
        hl.addWidget(sep)

        # Filtreler
        fil_widget=QWidget(); fil_widget.setStyleSheet("background:transparent;")
        fv=QVBoxLayout(fil_widget); fv.setContentsMargins(0,0,0,0); fv.setSpacing(6)
        fil_lbl=QLabel("FİLTRELER")
        fil_lbl.setStyleSheet("color:{};font-family:{};font-size:8px;"
                              "font-weight:700;letter-spacing:2px;".format(_TX2, _MONO))
        fv.addWidget(fil_lbl)
        fh=QHBoxLayout(); fh.setSpacing(10); fh.setContentsMargins(0,0,0,0)
        for attr,title,mw in [("cmb_abd","ANA BİLİM DALI",170),
                               ("cmb_birim","BİRİM",160),("cmb_tarih","İŞLEM TARİHİ",150)]:
            col=QVBoxLayout(); col.setSpacing(4); col.setContentsMargins(0,0,0,0)
            l=QLabel(title)
            l.setStyleSheet("font-family: {}; font-size: 8px; font-weight: 700; letter-spacing: 1px;".format(_MONO))
            w=QComboBox(); w.setFixedHeight(28); w.setMinimumWidth(mw)
            col.addWidget(l); col.addWidget(w); fh.addLayout(col)
            setattr(self,attr,w)
        self.cmb_abd.currentIndexChanged.connect(self.abd_birim_degisti)
        self.cmb_birim.currentIndexChanged.connect(self.abd_birim_degisti)
        self.cmb_tarih.currentIndexChanged.connect(self.filtrele)
        fv.addLayout(fh)
        hl.addWidget(fil_widget,1)

        # ayraç
        sep2=QFrame(); sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("background:{};width:1px;".format(_BD))
        hl.addWidget(sep2)

        # Butonlar
        btn_widget=QWidget(); btn_widget.setStyleSheet("background:transparent;")
        bv=QVBoxLayout(btn_widget); bv.setContentsMargins(0,0,0,0); bv.setSpacing(6)
        btn_lbl=QLabel("İŞLEMLER")
        btn_lbl.setStyleSheet("color:{};font-family:{};font-size:8px;"
                              "font-weight:700;letter-spacing:2px;".format(_TX2, _MONO))
        bv.addWidget(btn_lbl)

        self.btn_yenile=QPushButton("VERILERI YENILE")
        self.btn_yenile.setFixedHeight(30); self.btn_yenile.setMinimumWidth(180)
        self.btn_yenile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_yenile.setProperty("style-role", "refresh")
        self.btn_yenile.clicked.connect(self.load_data)
        IconRenderer.set_button_icon(self.btn_yenile, "refresh", size=16, color=_TX1)

        self.btn_olustur=QPushButton("PDF RAPOR OLUSTUR")
        self.btn_olustur.setObjectName("btn_kaydet")
        self.btn_olustur.setFixedHeight(30); self.btn_olustur.setMinimumWidth(180)
        self.btn_olustur.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_olustur.setProperty("style-role", "danger")
        self.btn_olustur.clicked.connect(self.rapor_baslat)
        IconRenderer.set_button_icon(self.btn_olustur, "save", size=16, color="#FFFFFF")
        if self._action_guard:
            self._action_guard.disable_if_unauthorized(self.btn_olustur, "cihaz.write")

        bv.addWidget(self.btn_yenile); bv.addWidget(self.btn_olustur)
        hl.addWidget(btn_widget)
        return outer

    # TABLO
    def _mk_table_panel(self) -> QWidget:
        panel=QWidget(); panel.setStyleSheet("background:{};".format(_BG0))
        vl=QVBoxLayout(panel); vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        self._rapor_model=RaporTableModel(); self.tablo=QTableView()
        self.tablo.setModel(self._rapor_model)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False); self.tablo.setShowGrid(False)
        self.tablo.setSortingEnabled(True)
        hdr=self.tablo.horizontalHeader()
        for i,w in enumerate(_RW):
            hdr.setSectionResizeMode(i,QHeaderView.ResizeMode.Stretch if i==len(_RCOLS)-1 else QHeaderView.ResizeMode.Interactive)
            if i!=len(_RCOLS)-1: hdr.resizeSection(i,w)
        vl.addWidget(self.tablo,1)

        foot=QWidget(); foot.setFixedHeight(30)
        foot.setStyleSheet("border-top: 1px solid {};".format(_BD))
        fl=QHBoxLayout(foot); fl.setContentsMargins(12,0,12,0)
        self.lbl_durum=QLabel("")
        self.lbl_durum.setStyleSheet("font-family: {}; font-size: 9px;".format(_MONO))
        self.lbl_sayi=QLabel("0 kayıt")
        self.lbl_sayi.setStyleSheet("font-family: {}; font-size: 9px;".format(_MONO))
        fl.addWidget(self.lbl_durum); fl.addStretch(); fl.addWidget(self.lbl_sayi)
        vl.addWidget(foot)
        return panel

    # KPI GUNCELLEME
    def _update_kpi(self, rows:List[Dict]):
        toplam=len(rows)
        uygun=sum(1 for r in rows if "Değil" not in r.get("Sonuc","") and r.get("Sonuc",""))
        uygun_d=sum(1 for r in rows if "Değil" in r.get("Sonuc",""))
        kaynak=len({r.get("EkipmanNo","") for r in rows})
        for k,v in [("toplam",toplam),("uygun",uygun),("uygun_d",uygun_d),
                    ("hurda_a",uygun_d),("kaynak",kaynak)]:
            if k in self._kpi: self._kpi[k].setText(str(v))

    # MANTIK
    def _tc(self, s:str) -> Optional[datetime.date]:
        if not s: return None
        for fmt in ("%Y-%m-%d","%d.%m.%Y","%d/%m/%Y"):
            try: return datetime.datetime.strptime(s,fmt).date()
            except: continue
        return None

    def load_data(self):
        """Ana pencereden çağırılan veri yükleme metodu."""
        if not self._db or not self._rke_repo:
            QMessageBox.warning(self, "Bağlantı Yok", "Veritabanı bağlantısı kurulamadı.")
            return
        
        try:
            self.btn_olustur.setEnabled(False)
            self.btn_yenile.setText("YUKLENIYOR...")
            self.lbl_durum.setText("Veriler yükleniyor...")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            self.loader = RaporVeriYukleyici(self._db_path)
            self.loader.veri_hazir.connect(self.veriler_geldi)
            self.loader.hata_olustu.connect(self._yukleme_hata)
            self.loader.finished.connect(self._yukle_bitti)
            self.loader.start()

        except Exception as e:
            logger.error(f"Veri yükleme hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Veri yüklenirken hata: {e}")
    
    def _populate_combos(self):
        """Combo kutularını doldurmak için yardımcı metod."""
        abds = set()
        birims = set()
        tarihler = set()
        
        for row in self.ham_veriler:
            abd = row.get("AnaBilimDali", "Tüm ABD")
            birim = row.get("Birim", "Tüm Birim")
            tarih = row.get("KayitTarih", "Tüm Tarih")
            
            if abd: abds.add(str(abd))
            if birim: birims.add(str(birim))
            if tarih: tarihler.add(str(tarih))
        
        # Combo'ları doldur
        self.cmb_abd.blockSignals(True)
        self.cmb_abd.clear()
        self.cmb_abd.addItem("Tüm ABD")
        self.cmb_abd.addItems(sorted(abds))
        self.cmb_abd.blockSignals(False)
        
        self.cmb_birim.blockSignals(True)
        self.cmb_birim.clear()
        self.cmb_birim.addItem("Tüm Birim")
        self.cmb_birim.addItems(sorted(birims))
        self.cmb_birim.blockSignals(False)
        
        self.cmb_tarih.blockSignals(True)
        self.cmb_tarih.clear()
        self.cmb_tarih.addItem("Tüm Tarih")
        self.cmb_tarih.addItems(sorted(tarihler))
        self.cmb_tarih.blockSignals(False)

    def _yukle_bitti(self):
        QApplication.restoreOverrideCursor()
        self.btn_olustur.setEnabled(True)
        self.btn_yenile.setText("VERILERI YENILE")
        self.lbl_durum.setText("")

    def _yukleme_hata(self, msg: str):
        logger.error(f"Veri yükleme hatası: {msg}")
        QMessageBox.critical(self, "Hata", f"Veri yüklenirken hata: {msg}")

    def veriler_geldi(self, data, headers, abd_l, birim_l, tarih_l):
        self.ham_veriler=data
        for cmb,baslik,liste in [(self.cmb_abd,"Tüm Bölümler",abd_l),
                                  (self.cmb_birim,"Tüm Birimler",birim_l),
                                  (self.cmb_tarih,"Tüm Tarihler",tarih_l)]:
            cmb.blockSignals(True); cur=cmb.currentText()
            cmb.clear(); cmb.addItem(baslik); cmb.addItems(liste)
            idx=cmb.findText(cur); cmb.setCurrentIndex(idx if idx>=0 else 0)
            cmb.blockSignals(False)
        self.abd_birim_degisti()

    def abd_birim_degisti(self):
        fa=self.cmb_abd.currentText(); fb=self.cmb_birim.currentText()
        t=set()
        for r in self.ham_veriler:
            if "Tüm" not in fa  and r.get('ABD','')!=fa: continue
            if "Tüm" not in fb and r.get('Birim','')!=fb: continue
            if r.get('Tarih'): t.add(r['Tarih'])
        sirali=sorted(t,reverse=True,key=lambda x: self._tc(x) or datetime.date.min)
        self.cmb_tarih.blockSignals(True); self.cmb_tarih.clear()
        self.cmb_tarih.addItem("Tüm Tarihler"); self.cmb_tarih.addItems(sirali)
        self.cmb_tarih.blockSignals(False)
        self.filtrele()

    def filtrele(self):
        fa=self.cmb_abd.currentText(); fb=self.cmb_birim.currentText()
        ft=self.cmb_tarih.currentText()
        filtered=[]
        for r in self.ham_veriler:
            if "Tüm" not in fa and r.get('ABD','')!=fa: continue
            if "Tüm" not in fb and r.get('Birim','')!=fb: continue
            if "Tüm" not in ft and r.get('Tarih','')!=ft: continue
            if self.rb_hurda.isChecked() and "Değil" not in r.get('Sonuc',''): continue
            filtered.append(r)
        self.filtrelenmis_veri=filtered
        self._rapor_model.set_rows(filtered)
        self.lbl_sayi.setText(f"{len(filtered)} kayıt gösteriliyor")
        self._update_kpi(filtered)

    def rapor_baslat(self):
        if self._action_guard and not self._action_guard.check_and_warn(
            self, "cihaz.write", "RKE Rapor Oluşturma"
        ):
            return
        if not self.filtrelenmis_veri:
            QMessageBox.warning(self, "Uyarı", "Rapor alınacak veri yok."); return
        mod=1
        if self.rb_hurda.isChecked(): mod=2
        elif self.rb_kisi.isChecked(): mod=3
        ozet=f"{self.cmb_abd.currentText()} - {self.cmb_birim.currentText()}"
        self.btn_olustur.setEnabled(False)
        self.btn_olustur.setText("ISLENIYOR...")
        self.lbl_durum.setText("PDF olusturuluyor...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.worker=RaporOlusturucuWorker(mod,self.filtrelenmis_veri,{"ozet":ozet})
        self.worker.log_mesaji.connect(self.lbl_durum.setText)
        self.worker.islem_bitti.connect(self._rapor_tamam)
        self.worker.start()

    def _rapor_tamam(self):
        QApplication.restoreOverrideCursor()
        self.btn_olustur.setEnabled(True)
        self.btn_olustur.setText("PDF RAPOR OLUSTUR")
        QMessageBox.information(self, "Tamamlandi", "Rapor islemleri tamamlandi.")
        self.lbl_durum.setText("Hazır.")

    def closeEvent(self,event):
        for a in ("loader","worker"):
            t=getattr(self,a,None)
            if t and t.isRunning(): t.quit(); t.wait(500)
        event.accept()


# main_window uyumluluk alias'lari
RKERaporPage = RKERaporPenceresi






