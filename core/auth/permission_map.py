from __future__ import annotations

# Map UI routes/titles to permission keys.
# Keep this separate so UI can import without touching DB layer.

PAGE_PERMISSIONS: dict[str, str] = {
    # Dashboard
    "Genel Bakış": "dis_alan.read",  # Dashboard için örnek yeni anahtar

    # PERSONEL Grubu
    "Personel Listesi": "personel.read",
    "Personel Ekle": "personel.write",
    "Sağlık Takip": "saglik.read",
    "İzin Takip ve FHSZ Yönetim": "fhsz.write",

    # CİHAZ Grubu
    "Cihaz Listesi": "cihaz.read",
    "Cihaz Ekle": "cihaz.write",
    "Teknik Hizmetler": "cihaz.write",

    # RKE Grubu
    "RKE Envanter": "rke.read",
    "RKE Muayene": "rke.write",
    "RKE Raporlama": "rke.read",

    # Dış Alan
    "Dış Alan Listele": "dis_alan.read",
    "Dış Alan Düzenle": "dis_alan.write",

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
    "Yedek Geri Yükle": "backup.restore",

    # Yönetici
    "Yıl Sonu İzin": "backup.restore",
    "Log Görüntüleyici": "dokuman.read",
    "Yedek Yönetimi": "backup.create",
    "Ayarlar": "dokuman.write",
    "Admin Panel": "backup.create",
}
