# database/google/signals.py
"""
Google bağlantı ve hata sinyalleri.
"""

import threading
from PySide6.QtCore import QObject, Signal


class GoogleBaglantiSinyalleri(QObject):
    """
    Google servisleri için global sinyal yöneticisi.
    
    Sinyaller:
        hata_olustu(baslik, mesaj)
    """

    hata_olustu = Signal(str, str)

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "GoogleBaglantiSinyalleri":
        """Thread-safe singleton instance döndürür"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = GoogleBaglantiSinyalleri()
        return cls._instance
