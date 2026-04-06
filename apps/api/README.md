# apps/api

Sprint-1 Adım-5 başlangıç API iskeleti.

## Çalıştırma

```bash
uvicorn apps.api.main:app --reload
```

## Hazır endpoint'ler

- `GET /health`
- `POST /auth/login`
- `GET /auth/me` (Bearer token gerekli)
- `GET /admin/ping` (admin rolü gerekli)

## Demo kullanıcılar (MVP)

- `admin@repys.local` / `admin123`
- `staff@repys.local` / `staff123`

## Not

Bu sürüm MVP amaçlıdır.
- Token yönetimi bellek içidir.
- Üretimde JWT + refresh + Redis/DB session ve gerçek kullanıcı tablosu kullanılmalıdır.
