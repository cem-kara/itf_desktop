from __future__ import annotations

# UI page title or route -> permission key mapping.
PAGE_PERMISSIONS: dict[str, str] = {
    "Katsayı Protokolleri": "admin.panel",
    "HBYS Referans Import": "admin.panel",
    # Dashboard
    "Genel Bakış": "dis_alan.read",  # Dashboard için örnek yeni anahtar

    # Personel
    "Personel Listesi": "dis_alan.read",
    "Personel Ekle": "dis_alan.write",
    "Sağlık Takip": "saglik.read",
    "İzin Takip ve FHSZ Yönetim": "fhsz.write",

    # Cihaz
    "Cihaz Listesi": "cihaz.read",
    "Cihaz Ekle": "cihaz.write",
    "Teknik Hizmetler": "cihaz.write",

    # RKE
    "RKE Envanter": "rke.read",
    "RKE Muayene": "rke.write",
    "RKE Raporlama": "rke.read",

    # Yönetici
    "Admin Panel": "backup.create",
    "Log Görüntüleyici": "dokuman.read",
    "Yedek Yönetimi": "backup.create",
    "Ayarlar": "dokuman.write",
    "Yıl Sonu İzin": "backup.restore",
    "Dış Alan HBYS Referansları": "dis_alan.read",  # veya uygun bir yetki anahtarı

    # Dış Alan
    "Dış Alan Listele": "dis_alan.read",
    "Dış Alan Düzenle": "dis_alan.write",

    # RKE
    "RKE Listele": "rke.read",
    "RKE Düzenle": "rke.write",

    # Sağlık
    "Sağlık Listele": "saglik.read",
    "Sağlık Düzenle": "saglik.write",

    # Dozimetre
    "Dozimetre Listele": "dozimetre.read",
    "Dozimetre Düzenle": "dozimetre.write",

    # FHSZ
    "FHSZ Listele": "fhsz.read",
    "FHSZ Düzenle": "fhsz.write",

    # Doküman
    "Doküman Listele": "dokuman.read",
    "Doküman Düzenle": "dokuman.write",

    # Rapor
    "Rapor Excel": "rapor.excel",
    "Rapor PDF": "rapor.pdf",

    # Yedekleme
    "Yedek Oluştur": "backup.create",
    "Yedek Geri Yükle": "backup.restore"

}
