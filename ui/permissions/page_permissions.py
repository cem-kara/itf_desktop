from __future__ import annotations

# UI page title or route -> permission key mapping.
PAGE_PERMISSIONS: dict[str, str] = {
    "Katsayı Protokolleri": "admin.panel",
    "HBYS Referans Import": "admin.panel",
    # Dashboard
    "Genel Bakış": "personel.read",  # Dashboard en az okuma yetkisi gerektirir
    
    # Personel
    "Personel Listesi": "personel.read",
    "Personel Ekle": "personel.write",
    "Sağlık Takip": "personel.read",
    "Sağlık Takip": "personel.read",
    "İzin Takip ve FHSZ Yönetim": "personel.write",
    "İzin Takip ve FHSZ Yönetim": "personel.write",

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
    "Log Görüntüleyici": "admin.panel",
    "Yedek Yönetimi": "admin.panel",
    "Yedek Yönetimi": "admin.panel",
    "Ayarlar": "admin.panel",
    "Yıl Sonu İzin": "admin.panel",
    "Yıl Sonu İzin": "admin.panel",
    "Dış Alan HBYS Referansları": "admin.panel",  # veya uygun bir yetki anahtarı

    #dis alan
    "DIS_ALAN_READ": "dis_alan.read",
    "DIS_ALAN_WRITE": "dis_alan.write"

}
