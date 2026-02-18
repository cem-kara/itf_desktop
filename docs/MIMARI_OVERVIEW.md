# Mimari Overview

## Genel Yapi

Katmanlar:
- UI: `ui/` (PySide6)
- Core: `core/` (config, logger, utils)
- DB: `database/` (SQLite + repository + sync)
- Sync: `database/sync_service.py`, `database/sync_worker.py`
- Google entegrasyon: `database/google/*`

## Veri Akisi (Ozet)

1. UI -> RepositoryRegistry -> SQLite
2. SyncWorker (QThread) -> SyncService -> Google Sheets

## Offline/Online Mod Mimarisi

Mode secimi:
1) `ITF_APP_MODE` env
2) `ayarlar.json` `app_mode`
3) `database/credentials.json` yoksa offline
4) varsayilan online

Adapter katmani:
- `database/cloud_adapter.py`
  - `OnlineCloudAdapter`: Google Drive/Sheets
  - `OfflineCloudAdapter`: yerel dosya kopyalama (offline upload)

Storage hedefi cozumu:
- `database/google/utils.py::resolve_storage_target(all_sabit, folder_name)`
  - Online: `Aciklama` -> Drive ID
  - Offline: `MenuEleman` -> klasor adi

## Klasorler

- `data/local.db`: SQLite
- `data/offline_uploads/<klasor>`: offline yuklemeler
- `logs/`: uygulama loglari
