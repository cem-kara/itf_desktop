# -*- coding: utf-8 -*-
"""BaseTableDelegate - Tüm table delegate'ler için temel sınıf."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtGui import QColor, QPainter, QBrush


class BaseTableDelegate(QStyledItemDelegate):
    """
    Tüm custom table delegate'ler için temel sınıf.
    
    Subclass'lar şu metodları override edebilir:
    - paint() - özel çizim
    - sizeHint() - satır yüksekliği
    - editorEvent() - mouse/keyboard olayları
    """
    
    # Status kolor haritası (subclass'lar override edebilir)
    STATUS_COLORS = {
        "Aktif": "#51CF66",      # Yeşil
        "Pasif": "#868E96",      # Gri
        "İzinli": "#339AF0",     # Mavi
        "Kapandı": "#51CF66",    # Yeşil
        "Açık": "#FF6B6B",       # Kırmızı
        "Bekleme": "#FFA500",    # Turuncu
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_row = -1

    def set_hover_row(self, row: int):
        """Hover'daki satırı belirt."""
        self._hover_row = row

    def sizeHint(self, option, index):
        """Varsayılan satır yüksekliği: 46px."""
        return QSize(100, 46)

    def paint(self, painter: QPainter, option, index):
        """
        Temel çizim: seçim/hover arkaplanı.
        
        Subclass'lar override edip kustomize edebilir.
        """
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Seçim/hover arka planı
        self._paint_background(painter, option, index)

        # Varsayılan metin çizimi
        super().paint(painter, option, index)
        
        painter.restore()

    def _paint_background(self, painter: QPainter, option, index):
        """Seçim ve hover arka planını çiz."""
        from PySide6.QtWidgets import QStyle
        from ui.styles import DarkTheme
        
        C = DarkTheme
        rect = option.rect
        row = index.row()
        
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hover = row == self._hover_row

        if is_selected:
            c = QColor(C.BTN_PRIMARY_BG)
            c.setAlpha(60)
            painter.fillRect(rect, c)
        elif is_hover:
            c = QColor(C.TEXT_PRIMARY)
            c.setAlpha(10)
            painter.fillRect(rect, c)

    def get_status_color(self, status: str) -> str:
        """Status'a göre renk döndür."""
        return self.STATUS_COLORS.get(status, "#666666")

    def get_status_background(self, status: str) -> str:
        """Status'a göre arka plan rengini döndür."""
        color_map = {
            "Aktif": "#E6F9EF",
            "Pasif": "#F1F3F5",
            "İzinli": "#E7F5FF",
            "Kapandı": "#E6F9EF",
            "Açık": "#FFE5E5",
            "Bekleme": "#FFF4E6",
        }
        return color_map.get(status, "#FFFFFF")
