# -*- coding: utf-8 -*-
"""Cihaz listesi tablo delegate'i - BaseTableDelegate'den extend."""

from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from PySide6.QtWidgets import QStyle

from ui.components.base_table_delegate import BaseTableDelegate
from ui.styles import DarkTheme
from ui.styles.components import ComponentStyles
from ui.pages.cihaz.models.cihaz_list_model import COLUMNS, CihazTableModel

C = DarkTheme


class CihazDelegate(BaseTableDelegate):
    """Özel hücre çizimi: iki satır metin + durum pill + aksiyon butonları."""

    BTN_W, BTN_H, BTN_GAP = 54, 26, 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._btn_rects: dict[tuple, QRect] = {}

    def sizeHint(self, option, index):
        return QSize(COLUMNS[index.column()][2], 46)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            row = index.row()
            col = index.column()
            key = COLUMNS[col][0]
            rect = option.rect

            # Arka plan çizimi (BaseTableDelegate'den)
            self._paint_background(painter, option, index)

            raw = index.model().data(index, CihazTableModel.RAW_ROW_ROLE)
            if raw is None:
                return

            # Custom çizim
            if key == "_cihaz":
                self._draw_two(
                    painter,
                    rect,
                    str(raw.get("Cihazid", "")),
                    str(raw.get("CihazTipi", "") or "—"),
                    mono_top=True,
                )
            elif key == "_marka_model":
                self._draw_two(
                    painter,
                    rect,
                    str(raw.get("Marka", "") or "—"),
                    str(raw.get("Model", "") or "—"),
                )
            elif key == "_seri":
                self._draw_two(
                    painter,
                    rect,
                    str(raw.get("SeriNo", "") or "—"),
                    str(raw.get("NDKSeriNo", "") or "—"),
                    mono_top=True,
                )
            elif key == "Birim":
                self._draw_two(
                    painter,
                    rect,
                    str(raw.get("AnaBilimDali", "") or "—"),
                    str(raw.get("Birim", "") or "—"),
                )
            elif key == "DemirbasNo":
                self._draw_mono(painter, rect, str(raw.get("DemirbasNo", "") or "—"))
            elif key == "Durum":
                self._draw_status_pill(painter, rect, str(raw.get("Durum", "") or "—"))
            elif key == "_actions":
                is_sel = bool(option.state & QStyle.StateFlag.State_Selected)
                is_hover = row == self._hover_row
                if is_hover or is_sel:
                    self._draw_action_btns(painter, rect, row)
                else:
                    for k in list(self._btn_rects):
                        if k[0] == row:
                            del self._btn_rects[k]
        finally:
            painter.restore()

    def _draw_two(self, p, rect, top, bottom, mono_top=False):
        pad = 8
        r1 = QRect(rect.x() + pad, rect.y() + 4, rect.width() - pad * 2, 17)
        r2 = QRect(rect.x() + pad, rect.y() + 21, rect.width() - pad * 2, 14)
        p.setFont(QFont("Courier New", 10) if mono_top else QFont("Segoe UI", 11, QFont.Medium))
        p.setPen(QColor(C.TEXT_PRIMARY))
        p.drawText(
            r1,
            Qt.AlignVCenter | Qt.AlignLeft,
            p.fontMetrics().elidedText(top, Qt.ElideRight, r1.width()),
        )
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(C.TEXT_MUTED))
        p.drawText(
            r2,
            Qt.AlignVCenter | Qt.AlignLeft,
            p.fontMetrics().elidedText(bottom, Qt.ElideRight, r2.width()),
        )

    def _draw_mono(self, p, rect, text):
        pad = 8
        r = QRect(rect.x() + pad, rect.y(), rect.width() - pad * 2, rect.height())
        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor(C.TEXT_PRIMARY))
        p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, p.fontMetrics().elidedText(text, Qt.ElideRight, r.width()))

    def _draw_status_pill(self, p, rect, text):
        text = text or "—"
        r = QRect(rect.x() + 8, rect.y() + 9, rect.width() - 16, 22)
        bg = ComponentStyles.get_status_color(text)
        fg = ComponentStyles.get_status_text_color(text)
        br, bgc, bb, ba = bg
        p.setBrush(QBrush(QColor(br, bgc, bb, ba)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 11, 11)
        p.setPen(QColor(fg))
        p.setFont(QFont("Segoe UI", 9, QFont.Medium))
        p.drawText(r, Qt.AlignCenter, text)

    def _draw_action_btns(self, p, rect, row):
        labels = [
            ("detay", "Detay", C.BTN_PRIMARY_BG, C.BTN_PRIMARY_TEXT),
            ("edit", "Duzenle", C.BTN_SECONDARY_BG, C.TEXT_PRIMARY),
            ("bakim", "Bakim", C.BTN_SUCCESS_BG, C.BTN_SUCCESS_TEXT),
        ]
        x = rect.x() + 8
        y = rect.center().y() - int(self.BTN_H / 2)
        for key, label, bg, fg in labels:
            btn_rect = QRect(x, y, self.BTN_W, self.BTN_H)
            p.setBrush(QBrush(QColor(bg)))
            p.setPen(QPen(QColor(C.BORDER_STRONG)))
            p.drawRoundedRect(btn_rect, 6, 6)
            p.setPen(QColor(fg))
            p.setFont(QFont("Segoe UI", 9, QFont.Medium))
            p.drawText(btn_rect, Qt.AlignCenter, label)
            self._btn_rects[(row, key)] = btn_rect
            x += self.BTN_W + self.BTN_GAP

    def get_action_at(self, row: int, pos: QPoint) -> str | None:
        for (r, key), rect in self._btn_rects.items():
            if r == row and rect.contains(pos):
                return key
        return None
