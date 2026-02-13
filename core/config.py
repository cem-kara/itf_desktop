class AppConfig:
    APP_NAME = "Radyoloji Envanter ve Personel Takip Sistemi"
    VERSION = "1.0.3"

    AUTO_SYNC = True
    SYNC_INTERVAL_MIN = 15
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LOG ROTATION CONFIGURATION (Disk Protection)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Log dosyasının maksimum büyüklüğü (bytes)
    # 10 MB = 10485760, 50 MB = 52428800
    LOG_MAX_BYTES = 10485760  # 10 MB

    # Tutulan backup log dosya sayısı (eski olanlar silinir)
    LOG_BACKUP_COUNT = 5

    # Opsiyonel: Günlük zaman tabanlı rotasyon parametreleri (ileriye dönük)
    LOG_ROTATION_WHEN = "midnight"
    LOG_ROTATION_INTERVAL = 1