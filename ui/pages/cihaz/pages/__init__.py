# -*- coding: utf-8 -*-
"""Cihaz Modülü - Sayfa paketleri (sadeleştirilmiş girişler)."""

from .listesi import CihazListesiView, CihazListesiPresenter, CihazListesiService, CihazListesiState
from .ekle import CihazEkleView
from .merkez import CihazMerkezView
from .dokuman import CihazDokumanView
from .ariza import ArizaView
from .bakim import BakimView
from .kalibrasyon import KalibrasyonView

__all__ = [
    "CihazListesiView", "CihazListesiPresenter", "CihazListesiService", "CihazListesiState",
    "CihazEkleView", "CihazMerkezView", "CihazDokumanView",
    "ArizaView", "BakimView", "KalibrasyonView",
]
