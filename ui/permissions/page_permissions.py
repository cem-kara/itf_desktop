from __future__ import annotations

# UI page title or route -> permission key mapping.
PAGE_PERMISSIONS: dict[str, str] = {
    # Dashboard
    "Genel Bakış": "personel.read",  # Dashboard en az okuma yetkisi gerektirir
    
    # Personel
    "Personel Listesi": "personel.read",
    "Personel Ekle": "personel.write",
    "Sağlık Takip": "personel.read",
    "SaÄŸlÄ±k Takip": "personel.read",
    "İzin Takip ve FHSZ Yönetim": "personel.write",
    "Ä°zin Takip ve FHSZ YÃ¶netim": "personel.write",

    # Cihaz
    "Cihaz Listesi": "cihaz.read",
    "Cihaz Ekle": "cihaz.write",
    "Teknik Hizmetler": "cihaz.write",

    # RKE
    "RKE Envanter": "cihaz.read",
    "RKE Muayene": "cihaz.write",
    "RKE Raporlama": "cihaz.read",

    # Yönetici
    "Admin Panel": "admin.panel",
    "Log Görüntüleyici": "admin.panel",
    "Log GÃ¶rÃ¼ntÃ¼leyici": "admin.panel",
    "Yedek Yönetimi": "admin.panel",
    "Yedek YÃ¶netimi": "admin.panel",
    "Ayarlar": "admin.panel",
    "Yıl Sonu İzin": "admin.panel",
    "YÄ±l Sonu Ä°zin": "admin.panel",
}
