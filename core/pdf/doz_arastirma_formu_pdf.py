# -*- coding: utf-8 -*-
"""
core/pdf/doz_arastirma_formu_pdf.py
═══════════════════════════════════════════════════════════════
RADAT RD.F43 Doz Araştırma Formu → PDF üretici.

reportlab kullanır (zaten requirements.txt'te mevcut).

Kullanım
--------
from core.pdf.doz_arastirma_formu_pdf import DozArastirmaFormuPDF

    pdf = DozArastirmaFormuPDF(form_verisi)   # get_form_data() çıktısı
    yol = pdf.kaydet("/tmp/form.pdf")         # dosya yolunu döndürür
"""
from __future__ import annotations

import os
import tempfile
from datetime import date
from typing import Optional

# ── reportlab ────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


def _register_turkish_fonts() -> tuple[str, str]:
    """
    Türkçe karakter destekli font kaydeder.
    Önce DejaVuSans (Linux/Mac), bulamazsa Windows Arial dener.
    Döndürür: (normal_font_adı, bold_font_adı)
    """
    # Aday font yolları — normal + bold çiftleri
    adaylar = [
        # DejaVu — Linux/Mac, geniş unicode
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        # Liberation Sans — Arial muadili, Linux
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        # Windows — Arial
        ("C:/Windows/Fonts/arial.ttf",
         "C:/Windows/Fonts/arialbd.ttf"),
        # Windows — Calibri (Office ile gelir)
        ("C:/Windows/Fonts/calibri.ttf",
         "C:/Windows/Fonts/calibrib.ttf"),
        # macOS
        ("/Library/Fonts/Arial.ttf",
         "/Library/Fonts/Arial Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ]

    for normal_yol, bold_yol in adaylar:
        try:
            if not (os.path.exists(normal_yol) and os.path.exists(bold_yol)):
                continue
            font_adi = "TRFont"
            font_bold = "TRFont-Bold"
            if font_adi not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_adi, normal_yol))
                pdfmetrics.registerFont(TTFont(font_bold, bold_yol))
                pdfmetrics.registerFontFamily(
                    font_adi,
                    normal=font_adi,
                    bold=font_bold,
                )
            return font_adi, font_bold
        except Exception:
            continue

    # Hiçbiri bulunamazsa Helvetica döner (Türkçe kırık ama çökmez)
    return _FONT_NORMAL, _FONT_BOLD


# Modül yüklendiğinde fontları kaydet
_FONT_NORMAL, _FONT_BOLD = _register_turkish_fonts()

# ── Renk paleti ──────────────────────────────────────────────
C_KIRMIZI   = colors.HexColor("#c0392b")
C_TURUNCU   = colors.HexColor("#e67e22")
C_KOYU_MAV  = colors.HexColor("#1a2a4a")
C_MAV       = colors.HexColor("#2c3e6b")
C_ACIK_MAV  = colors.HexColor("#eaf0fb")
C_TEHLIKE   = colors.HexColor("#fde8e8")
C_UYARI     = colors.HexColor("#fef9e7")
C_CIZGI     = colors.HexColor("#bdc3d1")
C_YESIL_BG  = colors.HexColor("#eafaf1")
C_YESIL     = colors.HexColor("#1e8449")
C_GRIS_HUCR = colors.HexColor("#f2f4f7")
C_SIYAH     = colors.black
C_BEYAZ     = colors.white


def _evet_hayir(veri: dict, anahtar: str) -> str:
    v = str(veri.get(anahtar) or "").strip()
    if v.lower() == "evet":
        return "☑ Evet  ☐ Hayır"
    return "☐ Evet  ☑ Hayır"


def _bool_check(veri: dict, anahtar: str) -> str:
    v = veri.get(anahtar)
    return "☑" if v else "☐"


def _val(veri: dict, anahtar: str, varsayilan: str = "—") -> str:
    v = veri.get(anahtar)
    if v is None or str(v).strip() == "" or str(v).strip() == "0":
        return varsayilan
    return str(v).strip()


class DozArastirmaFormuPDF:
    """
    DozArastirmaFormuDialog.get_form_data() sözlüğünden PDF üretir.

    Parameters
    ----------
    form_verisi : dict  —  Dialog'un get_form_data() çıktısı
    """

    SAYFA_W, SAYFA_H = A4
    SOL = 1.8 * cm
    SAG = 1.8 * cm
    UST = 1.5 * cm
    ALT = 1.5 * cm

    def __init__(self, form_verisi: dict):
        self._v = form_verisi
        self._styles = getSampleStyleSheet()

    # ─── Yardımcılar ──────────────────────────────────────────

    def _style(self, name="Normal", size=8, bold=False,
               color=None, align=TA_LEFT) -> object:
        from copy import copy
        s = copy(self._styles[name])
        s.fontSize   = size
        s.leading    = size + 3
        s.textColor  = color or C_SIYAH
        s.alignment  = align
        s.fontName   = _FONT_BOLD if bold else _FONT_NORMAL
        return s

    def _p(self, metin: str, **kwargs) -> Paragraph:
        return Paragraph(metin, self._style(**kwargs))

    def _tablo(self, data: list, col_widths: list,
               row_heights=None, style_extra=None) -> Table:
        t = Table(data, colWidths=col_widths,
                  rowHeights=row_heights, repeatRows=0)
        base = [
            ("FONTNAME",  (0, 0), (-1, -1), _FONT_NORMAL),
            ("FONTSIZE",  (0, 0), (-1, -1), 7.5),
            ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",(0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("GRID",      (0, 0), (-1, -1), 0.4, C_CIZGI),
        ]
        if style_extra:
            base += style_extra
        t.setStyle(TableStyle(base))
        return t

    @property
    def _ic_gen(self):
        return self.SAYFA_W - self.SOL - self.SAG

    # ─── Ana üretici ──────────────────────────────────────────

    def kaydet(self, dosya_yolu: Optional[str] = None) -> str:
        """
        PDF'i üretir ve dosya_yolu'na yazar.
        dosya_yolu=None → geçici dosya oluşturulur.
        Döndürür: dosya yolu (str)
        """
        if dosya_yolu is None:
            fd, dosya_yolu = tempfile.mkstemp(suffix=".pdf",
                                              prefix="DozArastirmaFormu_")
            os.close(fd)

        doc = SimpleDocTemplate(
            dosya_yolu,
            pagesize=A4,
            leftMargin=self.SOL,
            rightMargin=self.SAG,
            topMargin=self.UST,
            bottomMargin=self.ALT,
            title="Doz Araştırma Formu",
            author="REPYS",
        )

        hikaye = []
        hikaye += self._baslik_blogu()
        hikaye += self._bolum_a()
        hikaye += self._bolum_b()
        hikaye += self._bolum_c()
        hikaye += self._alt_bilgi()

        doc.build(hikaye)
        return dosya_yolu

    # ─── Başlık ───────────────────────────────────────────────

    def _baslik_blogu(self) -> list:
        w = self._ic_gen
        v = self._v

        # Üst bilgi bandı
        baslik = self._tablo(
            [[
                self._p("<b>DOZ ARAŞTIRMA FORMU</b>",
                        size=13, bold=True, color=C_BEYAZ, align=TA_LEFT),
                self._p("TAEK / RADAT<br/>RD.F43 Rev.01 — 10.10.2022",
                        size=7, color=C_ACIK_MAV, align=TA_RIGHT),
            ]],
            [w * 0.65, w * 0.35],
            row_heights=[28],
            style_extra=[
                ("BACKGROUND", (0, 0), (-1, -1), C_KOYU_MAV),
                ("TEXTCOLOR",  (0, 0), (-1, -1), C_BEYAZ),
                ("FONTNAME",   (0, 0), (0,  0),  _FONT_BOLD),
                ("GRID",       (0, 0), (-1, -1), 0, C_KOYU_MAV),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )

        # Doz seviyesi uyarı bandı
        try:
            hp10 = float(v.get("OlculenDoz") or 0)
        except (ValueError, TypeError):
            hp10 = 0.0

        if hp10 >= 5.0:
            uyari_renk = C_TEHLIKE
            uyari_metin = f"⛔  TEHLİKE — Ölçülen Doz: {hp10:.3f} mSv  (Eşik: 5,0 mSv)"
            metin_renk  = C_KIRMIZI
        elif hp10 >= 2.0:
            uyari_renk = C_UYARI
            uyari_metin = f"⚠  UYARI — Ölçülen Doz: {hp10:.3f} mSv  (Eşik: 2,0 mSv)"
            metin_renk  = C_TURUNCU
        else:
            uyari_renk  = None
            uyari_metin = None
            metin_renk  = None

        blok = [baslik, Spacer(1, 4)]

        if uyari_metin:
            uyari_tablo = self._tablo(
                [[self._p(f"<b>{uyari_metin}</b>", size=8.5,
                          bold=True, color=metin_renk)]],
                [w],
                row_heights=[20],
                style_extra=[
                    ("BACKGROUND", (0, 0), (-1, -1), uyari_renk),
                    ("GRID", (0, 0), (-1, -1), 0.5, metin_renk),
                ]
            )
            blok += [uyari_tablo, Spacer(1, 4)]

        return blok

    # ─── Bölüm A — Dozimetri Servisi Bilgileri ───────────────

    def _bolum_a(self) -> list:
        w = self._ic_gen
        v = self._v

        baslik = self._tablo(
            [[self._p("<b>A — Dozimetri Servisi Tarafından Doldurulacaktır</b>",
                      size=8, bold=True, color=C_BEYAZ)]],
            [w], row_heights=[16],
            style_extra=[("BACKGROUND", (0, 0), (-1, -1), C_MAV),
                         ("GRID", (0, 0), (-1, -1), 0, C_MAV)]
        )

        # Dozimetre tipi checkboxları
        tip = str(v.get("DozimetriTipi") or "").upper()
        tip_metin = (
            f"{'☑' if 'TLD' in tip else '☐'} TLD   "
            f"{'☑' if 'OSL' in tip else '☐'} OSL   "
            f"{'☑' if 'NÖTRON' in tip or 'NOTRON' in tip else '☐'} Nötron   "
            f"{'☑' if 'ELEK' in tip else '☐'} Elektronik"
        )

        sol_w = w * 0.5
        sag_w = w * 0.5

        def _satir(lbl, deger):
            return [
                self._p(f"<b>{lbl}</b>", size=7.5, bold=True,
                        color=colors.HexColor("#3a3a3a")),
                self._p(deger or "—", size=8),
            ]

        sol_data = [
            _satir("Adı Soyadı:",      _val(v, "AdSoyad")),
            _satir("TC Kimlik No:",    _val(v, "TCKimlik")),
            _satir("Kuruluş Adı:",     _val(v, "KurulusAdi")),
            _satir("Kuruluş Kodu:",    _val(v, "KurulusKodu")),
            _satir("Uygulama Alanı:", _val(v, "UygulamaAlani")),
            _satir("Mesleği:",         _val(v, "Meslek")),
        ]
        sag_data = [
            _satir("Yıl / Periyot:",   f"{_val(v,'Yil')} / {_val(v,'Periyot')}"),
            _satir("Süre:",             _val(v, "Sure")),
            _satir("Ölçülen Doz:",     f"{_val(v,'OlculenDoz')} mSv"),
            _satir("Dozimetre No:",    _val(v, "DozimetreNo")),
            _satir("Dozimetre Tipi:",  tip_metin),
            _satir("Form No:",         _val(v, "FormNo")),
        ]

        sol_tablo = self._tablo(sol_data, [sol_w * 0.38, sol_w * 0.62])
        sag_tablo = self._tablo(sag_data, [sag_w * 0.40, sag_w * 0.60])

        grid = self._tablo(
            [[sol_tablo, sag_tablo]],
            [sol_w, sag_w],
            style_extra=[("GRID", (0, 0), (-1, -1), 0, C_BEYAZ),
                         ("VALIGN", (0, 0), (-1, -1), "TOP")]
        )

        return [baslik, grid, Spacer(1, 6)]

    # ─── Bölüm B — Kullanıcı Soruları ────────────────────────

    def _bolum_b(self) -> list:
        w = self._ic_gen
        v = self._v

        baslik = self._tablo(
            [[self._p("<b>B — Dozimetre Kullanıcısı Tarafından Doldurulacaktır</b>",
                      size=8, bold=True, color=C_BEYAZ)]],
            [w], row_heights=[16],
            style_extra=[("BACKGROUND", (0, 0), (-1, -1), C_MAV),
                         ("GRID", (0, 0), (-1, -1), 0, C_MAV)]
        )

        soru_w_no   = 0.6 * cm
        soru_w_soru = w * 0.44
        soru_w_cvp  = w - soru_w_no - soru_w_soru

        def _soru(no, soru, cevap, aciklama="", bg=None):
            row = [
                self._p(f"<b>{no}</b>", size=7.5, bold=True),
                self._p(soru, size=7.5),
                self._p(cevap, size=7.5),
            ]
            extra = []
            if bg:
                extra += [("BACKGROUND", (0, 0), (-1, -1), bg)]
            if aciklama:
                acik_row = [
                    self._p(""),
                    self._p("<i>Açıklama:</i>", size=7),
                    self._p(aciklama, size=7.5),
                ]
                return [row, acik_row], extra
            return [row], extra

        # Kaynak checkboxları
        kaynak = (
            f"{_bool_check(v,'KaynakXIsini')} X-ışını   "
            f"{_bool_check(v,'KaynakKapali')} Kapalı kaynak   "
            f"{_bool_check(v,'KaynakAcik')} Açık kaynak   "
            f"{_bool_check(v,'KaynakTesis')} Tesis"
        )
        if v.get("KaynakDiger"):
            kaynak += f"   ☑ Diğer: {v['KaynakDiger']}"

        # Korunma checkboxları
        korunma = (
            f"{_bool_check(v,'KorunmaParavan')} Paravan   "
            f"{_bool_check(v,'KorunmaOnluk')} Önlük   "
            f"{_bool_check(v,'KorunmaGozluk')} Gözlük   "
            f"{_bool_check(v,'KorunmaTiroid')} Tiroid   "
            f"{_bool_check(v,'KorunmaEldiven')} Eldiven"
        )

        # Pozisyon checkboxları
        pozisyon = (
            f"{_bool_check(v,'DzPositionYaka')} Yaka   "
            f"{_bool_check(v,'DzPositionKemer')} Kemer   "
            f"{_bool_check(v,'DzPositionGomlek')} Gömlek   "
            f"{_bool_check(v,'DzPositionOnlukUst')} Önlük üstü   "
            f"{_bool_check(v,'DzPositionOnlukAlt')} Önlük altı   "
            f"{_bool_check(v,'DzPositionElBilek')} El/Bilek"
        )

        # S5 ek bilgi
        s5_ek = ""
        if v.get("S5_SureSaat"):
            s5_ek += f"Süre: {v['S5_SureSaat']} saat"
        if v.get("S5_MesafeM"):
            s5_ek += f"  Mesafe: {v['S5_MesafeM']} m"

        tablo_data  = []
        style_extra = [
            ("BACKGROUND", (0, 0), (0, -1), C_GRIS_HUCR),
            ("FONTNAME",   (0, 0), (0, -1), _FONT_BOLD),
        ]

        sorular = [
            ("1", "Radyasyon kaynağıyla çalışılan iş günü ve günlük çalışma süresi",
             f"{_val(v,'CalismaGunSayisi','0')} gün / "
             f"{_val(v,'GunlukCalismaSaat','0')} saat", ""),
            ("2", "Maruz kalınan radyasyonun kaynağı", kaynak, ""),
            ("3", "Dozimetreyi başkası kullandı mı?",
             _evet_hayir(v, "S3_BaskasıKullandi"),
             _val(v, "S3_Aciklama", "")),
            ("4", "Kullanılmadığı zamanlarda radyasyon alanında mı muhafaza edildi?",
             _evet_hayir(v, "S4_RadAlaniMuhafaza"),
             _val(v, "S4_Aciklama", "")),
            ("5", "Radyasyon alanında bırakıldı veya unutuldu mu?",
             _evet_hayir(v, "S5_RadAlaniUnutuldu"),
             (s5_ek + "  " + _val(v, "S5_Aciklama", "")).strip()),
            ("6", "Tetkik/tedavi sırasında yanlışlıkla yanında bulunduruldu mu?",
             _evet_hayir(v, "S6_TetkikSirasinda"),
             _val(v, "S6_Aciklama", "")),
            ("7", "Radyasyondan korunma donanımları", korunma, ""),
            ("8", "Dozimetrenin kullanıldığı yer", pozisyon, ""),
            ("9", "Dozimetrede radyoaktif kirlilik oldu mu?",
             _evet_hayir(v, "S9_RadKirlilik"),
             _val(v, "S9_Izotop", "")),
        ]

        for no, soru, cevap, acik in sorular:
            rows, ex = _soru(no, soru, cevap, acik)
            tablo_data += rows
            style_extra += ex

        soru_tablo = self._tablo(
            tablo_data,
            [soru_w_no, soru_w_soru, soru_w_cvp],
            style_extra=style_extra
        )

        # Yorum satırı
        yorum_items = []
        if v.get("Yorum_HataliKullanim"): yorum_items.append("Hatalı kullanım")
        if v.get("Yorum_CalKosulu"):      yorum_items.append("Çalışma koşulu")
        if v.get("Yorum_KasitliIsinlama"):yorum_items.append("Kasıtlı ışınlanma")
        if v.get("Yorum_Diger"):          yorum_items.append(v["Yorum_Diger"])
        yorum_metin = " | ".join(yorum_items) if yorum_items else "—"

        yorum_tablo = self._tablo(
            [[self._p("<b>Kullanıcı Yorumu:</b>", size=7.5, bold=True),
              self._p(yorum_metin, size=7.5)]],
            [3 * cm, w - 3 * cm],
            style_extra=[("BACKGROUND", (0, 0), (0, 0), C_GRIS_HUCR)]
        )

        aciklama_tablo = self._tablo(
            [[self._p("<b>Açıklama:</b>", size=7.5, bold=True),
              self._p(_val(v, "KullaniciAciklama", ""), size=7.5)]],
            [3 * cm, w - 3 * cm],
            row_heights=[28],
            style_extra=[("BACKGROUND", (0, 0), (0, 0), C_GRIS_HUCR),
                         ("VALIGN", (0, 0), (-1, -1), "TOP")]
        )

        return [baslik, soru_tablo, Spacer(1, 3),
                yorum_tablo, aciklama_tablo, Spacer(1, 6)]

    # ─── Bölüm C — RK Sorumlusu ──────────────────────────────

    def _bolum_c(self) -> list:
        w = self._ic_gen
        v = self._v

        baslik = self._tablo(
            [[self._p("<b>C — Radyasyondan Korunma Sorumlusu Tarafından Doldurulacaktır</b>",
                      size=8, bold=True, color=C_BEYAZ)]],
            [w], row_heights=[16],
            style_extra=[("BACKGROUND", (0, 0), (-1, -1), C_MAV),
                         ("GRID", (0, 0), (-1, -1), 0, C_MAV)]
        )

        soru_w_no   = 0.6 * cm
        soru_w_soru = w * 0.50
        soru_w_cvp  = w - soru_w_no - soru_w_soru

        sorular_c = [
            ("1", "Tesiste / kaynakta / çalışma koşullarında değişiklik oldu mu?",
             _evet_hayir(v, "SC1_TesisDegisim"),
             _val(v, "SC1_Aciklama", "")),
            ("2", "Kişi radyasyondan korunma konusunda yeterli bilgiye sahip mi?",
             _evet_hayir(v, "SC2_KorunmaBilgi"), ""),
            ("3", "Kişiye hizmet içi eğitim verildi mi?",
             _evet_hayir(v, "SC3_Egitim"), ""),
            ("4", "Periyotta olağan dışı bir durum oldu mu?",
             _evet_hayir(v, "SC4_OlaganDisi"),
             _val(v, "SC4_Aciklama", "")),
            ("5", "Aynı ortamda çalışan diğer kişilerin dozunda artış oldu mu?",
             _evet_hayir(v, "SC5_DigerArtis"),
             _val(v, "SC5_Aciklama", "")),
            ("6", "Çalışma ortamında radyasyon ölçümlerinde artış izlendi mi?",
             _evet_hayir(v, "SC6_RadArtis"),
             _val(v, "SC6_Aciklama", "")),
        ]

        tablo_data  = []
        style_extra = [
            ("BACKGROUND", (0, 0), (0, -1), C_GRIS_HUCR),
            ("FONTNAME",   (0, 0), (0, -1), _FONT_BOLD),
        ]

        for no, soru, cevap, acik in sorular_c:
            tablo_data.append([
                self._p(f"<b>{no}</b>", size=7.5, bold=True),
                self._p(soru, size=7.5),
                self._p(cevap, size=7.5),
            ])
            if acik:
                tablo_data.append([
                    self._p(""),
                    self._p("<i>Açıklama:</i>", size=7),
                    self._p(acik, size=7.5),
                ])

        soru_tablo = self._tablo(
            tablo_data,
            [soru_w_no, soru_w_soru, soru_w_cvp],
            style_extra=style_extra
        )

        # Hesaplanan doz
        try:
            h_doz = float(v.get("HesaplananDoz") or 0)
            h_doz_metin = f"{h_doz:.3f} mSv"
        except (ValueError, TypeError):
            h_doz_metin = "—"

        hesap_tablo = self._tablo(
            [[self._p("<b>7. Hesaplanmış Doz Değeri:</b>", size=7.5, bold=True),
              self._p(f"<b>{h_doz_metin}</b>", size=9, bold=True,
                      color=C_KIRMIZI if h_doz_metin != "—" and float(v.get("HesaplananDoz") or 0) >= 5 else C_SIYAH),
              self._p("(Doz hızı × Süre)", size=7, color=colors.grey)]],
            [4 * cm, 3 * cm, w - 7 * cm],
            row_heights=[18],
            style_extra=[("BACKGROUND", (0, 0), (0, 0), C_GRIS_HUCR),
                         ("FONTNAME",   (0, 0), (0, 0), _FONT_BOLD)]
        )

        # Sorumlu yorumu
        yorum_s = []
        if v.get("Sor_HataliKullanim"): yorum_s.append("Hatalı kullanım")
        if v.get("Sor_CalKosulu"):      yorum_s.append("Çalışma koşulu")
        if v.get("Sor_KasitliIsinlama"):yorum_s.append("Kasıtlı ışınlanma")
        if v.get("Sor_Diger"):          yorum_s.append(v["Sor_Diger"])
        yorum_s_metin = " | ".join(yorum_s) if yorum_s else "—"

        yorum_sor_tablo = self._tablo(
            [[self._p("<b>Sorumlu Yorumu:</b>", size=7.5, bold=True),
              self._p(yorum_s_metin, size=7.5)]],
            [3.5 * cm, w - 3.5 * cm],
            style_extra=[("BACKGROUND", (0, 0), (0, 0), C_GRIS_HUCR)]
        )

        aciklama_sor = self._tablo(
            [[self._p("<b>Sorumlu Açıklaması:</b>", size=7.5, bold=True),
              self._p(_val(v, "SorumluAciklama", ""), size=7.5)]],
            [3.5 * cm, w - 3.5 * cm],
            row_heights=[28],
            style_extra=[("BACKGROUND", (0, 0), (0, 0), C_GRIS_HUCR),
                         ("VALIGN", (0, 0), (-1, -1), "TOP")]
        )

        # İmza bloğu
        imza_tablo = self._tablo(
            [[
                self._p("Dozimetre Kullanıcısı\nAdı Soyadı / İmza",
                        size=7, align=TA_CENTER),
                self._p("Radyasyondan Korunma Sorumlusu\nAdı Soyadı / İmza",
                        size=7, align=TA_CENTER),
                self._p("Yetkili Kişi\nAdı Soyadı / İmza",
                        size=7, align=TA_CENTER),
            ]],
            [w / 3] * 3,
            row_heights=[36],
            style_extra=[
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",     (0, 0), (-1, -1), "BOTTOM"),
                ("BACKGROUND", (0, 0), (-1, -1), C_ACIK_MAV),
            ]
        )

        return [baslik, soru_tablo, Spacer(1, 3),
                hesap_tablo, yorum_sor_tablo, aciklama_sor,
                Spacer(1, 8), imza_tablo, Spacer(1, 6)]

    # ─── Alt bilgi ────────────────────────────────────────────

    def _alt_bilgi(self) -> list:
        w = self._ic_gen
        uyari = (
            "⚠  Bu formun en geç <b>10 iş günü</b> içerisinde eksiksiz doldurularak "
            "RADAT ve NDK'ya gönderilmesi gerekmektedir. "
            "Dozimetrelerin hatalı kullanılması veya kasıtlı ışınlanması durumunda "
            "\"Hesaplanmış Doz Değeri\" belirlenmeden gönderilen formlar kabul edilmez."
        )
        uyari_tablo = self._tablo(
            [[self._p(uyari, size=6.5, color=colors.HexColor("#666666"))]],
            [w],
            style_extra=[("BACKGROUND", (0, 0), (-1, -1), C_GRIS_HUCR),
                         ("GRID", (0, 0), (-1, -1), 0.3, C_CIZGI)]
        )

        tarih = date.today().strftime("%d.%m.%Y")
        meta_tablo = self._tablo(
            [[self._p(f"REPYS — Dozimetre Takip Sistemi", size=6.5,
                      color=colors.grey),
              self._p(f"Üretim Tarihi: {tarih}", size=6.5,
                      color=colors.grey, align=TA_RIGHT)]],
            [w * 0.6, w * 0.4],
            style_extra=[("GRID", (0, 0), (-1, -1), 0, C_BEYAZ)]
        )

        return [uyari_tablo, Spacer(1, 4), meta_tablo]
