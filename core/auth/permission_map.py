from __future__ import annotations

# Map UI routes/titles to permission keys.
# Keep this separate so UI can import without touching DB layer.

PAGE_PERMISSIONS: dict[str, str] = {
    # Dashboard
    "Genel Bakış": "personel.read",  # Dashboard en az okuma yetkisi gerektirir
    
    # PERSONEL Grubu
    "Personel Listesi": "personel.read",
    "Personel Ekle": "personel.write",
    "Sağlık Takip": "personel.read",
    "İzin Takip ve FHSZ Yönetim": "personel.write",
    
    # CİHAZ Grubu
    "Cihaz Listesi": "cihaz.read",
    "Cihaz Ekle": "cihaz.write",
    "Teknik Hizmetler": "cihaz.write",
    
    # RKE Grubu
    "RKE Envanter": "cihaz.read",
    "RKE Muayene": "cihaz.write",
    "RKE Raporlama": "cihaz.read",
    
    # YÖNETİCİ İŞLEMLERİ Grubu
    "Yıl Sonu İzin": "admin.panel",
    "Log Görüntüleyici": "admin.panel",
    "Yedek Yönetimi": "admin.panel",
    "Ayarlar": "admin.panel",
    "Admin Panel": "admin.panel",
}
