# database/google/signals.py
"""
Google işlemleri için Qt sinyalleri.

Bu modül hata bildirimlerini UI'a iletmek için sinyaller sağlar.
"""

import threading
from PySide6.QtCore import QObject, Signal


class GoogleBaglantiSinyalleri(QObject):
    """
    Google bağlantı hatalarını bildirmek için sinyal sınıfı.
    
    Thread-safe singleton pattern kullanır.
    """
    
    # Sinyal: (başlık, mesaj)
    hata_olustu = Signal(str, str)
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Doğrudan instance oluşturmayın, get_instance() kullanın"""
        super().__init__()
    
    @classmethod
    def get_instance(cls) -> 'GoogleBaglantiSinyalleri':
        """Thread-safe singleton instance döndürür"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = GoogleBaglantiSinyalleri()
        return cls._instance
    
    def emit_hata(self, baslik: str, mesaj: str):
        """Hata sinyali gönder"""
        self.hata_olustu.emit(baslik, mesaj)
