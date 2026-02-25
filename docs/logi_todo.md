# LOGI_TODO - Login + RBAC Oncelik ve Teknik Gorev Listesi

Tarih: 2026-02-25
Kapsam: Kullanici girisi + rol/yetki (RBAC) + menu ve sayfa guard

## 1) Oncelikler (logi_todo)
1. P0 - Veri modeli ve migration
2. P0 - Auth servisleri (kimlik dogrulama + yetki kontrol)
3. P0 - Login akisi (UI dialog + main gate)
4. P1 - Menu filtreleme (yetkisiz sayfa gizle)
5. P1 - Sayfa guard (yetkisiz erisim engeli)
6. P2 - Aksiyon bazli yetki (ekle/sil/guncelle)
7. P2 - Audit ve guvenlik sertlestirme
8. P3 - Testler ve smoke senaryolar

## 2) Is Paketleri (Acceptance + Test)
1. IP-01 Veri modeli ve migration
Kapsam: Users, Roles, Permissions, UserRoles, RolePermissions (opsiyonel AuthAudit) tablolari.
Cikis: v15 migration ve temel seed.
Kabul: Bos DB ve upgrade senaryosu basarili; unique/FK kurallari net.
Test: migration testleri (bos DB + upgrade).
2. IP-02 Auth servisleri
Kapsam: authenticate, password hash/verify, authorization resolve, session context.
Cikis: core/auth altinda servisler.
Kabul: Basarili/basarisiz login ve rol bazli izin hesaplari dogru.
Test: unit test seti (auth + authorization).
3. IP-03 Login akisi (UI)
Kapsam: LoginDialog + main gate.
Cikis: login olmadan MainWindow acilmasin.
Kabul: Basarili login -> app acilir; basarisiz -> hata mesaji.
Test: manuel UI smoke + basit dialog testleri.
4. IP-04 Menu filtreleme
Kapsam: Sidebar yuklemesinde permission kontrolu.
Cikis: Yetkisiz menuler gizlenir.
Kabul: Rol bazli menu farki net.
Test: rol bazli menu snapshot.
5. IP-05 Sayfa guard
Kapsam: _on_menu_clicked veya _create_page icinde guard.
Cikis: Yetkisiz sayfaya erisim engeli.
Kabul: Page map by-pass yok.
Test: yetkisiz erisim denemesi.
6. IP-06 Aksiyon bazli yetki
Kapsam: Ekle/sil/guncelle buton ve handler kontrolleri.
Cikis: UI ve backend guard birlikte.
Kabul: Yetkisiz rol aksiyonu calistiramaz.
Test: action-level yetki testleri.
7. IP-07 Audit ve guvenlik sertlestirme
Kapsam: AuthAudit, sifre politikasi, lockout, ilk giris sifre degistirme.
Cikis: temel guvenlik katmani.
Kabul: Basarisiz login limiti ve audit log kaydi calisir.
Test: login rate limit ve audit kaydi testi.
8. IP-08 Testler ve smoke
Kapsam: auth/authorization + menu guard + page guard testleri.
Cikis: tek komutla calisan test seti.
Kabul: pytest ile temiz gecis.
Test: CI benzeri tek komut.

## 3) Test Case Sablonu (kisa)
TestAdi: <kisa ve benzersiz ad>
OnKosul: <gerekli veriler ve rol>
Adimlar: <1-3 net adim>
Beklenen: <dogrulama>
Not: <log id / hata mesaji varsa>

## 4) Hazirlanan Iskeletler (2026-02-25)
Not: Sadece yeni dosyalar eklendi, mevcut dosyalara dokunulmadi.
Eklenen: core/auth/__init__.py
Eklenen: core/auth/auth_service.py
Eklenen: core/auth/password_hasher.py
Eklenen: core/auth/authorization_service.py
Eklenen: core/auth/session_context.py
Eklenen: core/auth/permission_keys.py
Eklenen: core/auth/permission_map.py
Eklenen: ui/auth/__init__.py
Eklenen: ui/auth/login_dialog.py
Eklenen: ui/admin/__init__.py
Eklenen: ui/admin/admin_panel.py
Eklenen: ui/admin/users_view.py
Eklenen: ui/admin/roles_view.py
Eklenen: ui/admin/permissions_view.py
Eklenen: ui/admin/audit_view.py
Eklenen: ui/guards/__init__.py
Eklenen: ui/guards/page_guard.py
Eklenen: ui/permissions/__init__.py
Eklenen: ui/permissions/page_permissions.py
Eklenen: database/auth_repository.py
Eklenen: database/permission_repository.py
Eklenen: scripts/seed_admin.py
Eklenen: tests/test_auth_service.py
Eklenen: tests/test_authorization_service.py
Eklenen: tests/test_login_dialog.py

## 4.1) RBAC Taslaklari (docs/rbac_drafts) (2026-02-25)
Not: Asil dosyalara dokunulmadan, tam guncellenmis taslak kopyalar olusturuldu.
Taslak: docs/rbac_drafts/main.pyw
Taslak: docs/rbac_drafts/database/migrations.py
Taslak: docs/rbac_drafts/database/sqlite_manager.py
Taslak: docs/rbac_drafts/ui/main_window.py
Taslak: docs/rbac_drafts/ui/sidebar.py
Taslak: docs/rbac_drafts/ui/auth/login_dialog.py
Taslak: docs/rbac_drafts/core/di.py
Taslak: docs/rbac_drafts/ayarlar.json
Taslak: docs/rbac_drafts/core/auth/password_hasher.py
Taslak: docs/rbac_drafts/ui/admin/admin_panel.py
Taslak: docs/rbac_drafts/ui/admin/__init__.py
Taslak: docs/rbac_drafts/ui/auth/__init__.py
Taslak: docs/rbac_drafts/permissions_standard.md
Taslak: docs/rbac_drafts/page_permission_matrix.md
Taslak: docs/rbac_drafts/role_matrix.md
Taslak: docs/rbac_drafts/login_flow.md
Taslak: docs/rbac_drafts/guard_flow.md
Taslak: docs/rbac_drafts/seed_strategy.md
Taslak: docs/rbac_drafts/test_plan.md
Taslak: docs/rbac_drafts/risk_rollback.md

## 5) Dosya Bazli Teknik Gorev Listesi (Bu dokumana eklenecek)

### database/migrations.py
- Gorev: v15 migration ile Users, Roles, Permissions, UserRoles, RolePermissions (opsiyonel AuthAudit) tablolarini ekle.
- Kabul: Bos DB ve mevcut DB upgrade senaryosu basarili; unique ve FK kurallari net.
- Risk: Mevcut schema ile isim cakismasi.
- Test: migration testleri (bos DB + upgrade).

### database/ (Hazirlik Eksikleri - dokunulmadan birakildi)
- Eksik: v15 migration tanimi (mevcut migrations.py icine eklenmedi).
- Eksik: seed akisi (admin/roles/permissions) uygulama icine baglanmadi.
- Eksik: schema dokumani (tablo/kolon/FK/unique listesi).
- Eksik: rollback/upgrade test senaryolari.
- Not: Bu kalemler "veritabanı hazirligi" icin gerekli ama henuz uygulanmadi.

## 6) Hazirlik Asamasinda Ek Is Kalemleri (Koda Dokunmadan)
- Yetki isimlendirme standardi ve tablo semasi taslagi (dokuman).
- Sayfa -> permission eslesme tablosu (dokuman).
- Rol seti taslagi (admin/operator/viewer) ve default izin matrisi.
- Login akis diyagrami (baslangic -> dialog -> main window).
- Menu filtreleme + page guard karar noktalari (akis notu).
- Seed stratejisi (ilk admin olusturma, sifre politikasi).
- Test plani (auth/authorization/menu/page guard smoke listesi).
- Riskler + rollback plani (migration/seed).
### database/sqlite_manager.py
- Gorev: Yeni tablolar icin temel CRUD ve lookup yardimcilari ekle.
- Kabul: Kullanici/rol/yetki sorgulari tek yerden yapilabilir.
- Risk: UI tarafinda dogrudan SQL yazma devam eder.
- Test: repository testleri (get_user_by_username, get_permissions_for_user).

### core/auth/auth_service.py
- Gorev: authenticate(username, password) ve session user nesnesi.
- Kabul: Yanlis sifre false, dogru sifre true; isActive kontrolu var.
- Risk: Hash dogrulama dogru uygulanmazsa guvenlik acigi.
- Test: unit test (basarili/basarisiz login).

### core/auth/password_hasher.py
- Gorev: hash/verify fonksiyonlari (bcrypt veya argon2).
- Kabul: Hashler geri cozulmez, sabit zamanli verify kullanilir.
- Risk: Yanlis algoritma secimi.
- Test: hash/verify round-trip testi.

### core/auth/authorization_service.py
- Gorev: has_permission(user, permission_key) ve role->permission resolve.
- Kabul: Role based izinler dogru hesaplanir.
- Risk: Cache tutarsizligi varsa stale izin cikabilir.
- Test: rol bazli izin testleri.

### core/auth/session_context.py
- Gorev: Aktif kullaniciyi uygulama genelinde tasiyacak context.
- Kabul: SessionUser her yerden okunabilir; None durumda guard calisir.
- Risk: Global state dogru temizlenmezse baska kullaniciya sarkar.
- Test: basic lifecycle testi.

### ui/auth/login_dialog.py
- Gorev: LoginDialog olustur (kullanici adi + sifre + hata mesaji).
- Kabul: Basarili login -> dialog accept, basarisiz -> mesaj.
- Risk: UI validasyon eksigi.
- Test: manuel UI smoke.

### main.pyw
- Gorev: Uygulama baslangicinda LoginDialog ac; basariliysa MainWindow(session_user) ac.
- Kabul: Login olmadan uygulama acilmaz.
- Risk: Uygulama kapanis akisi bozulabilir.
- Test: manuel akilsmoke (start, cancel, success).

### ui/sidebar.py
- Gorev: Menu yukleme asamasinda yetki kontrolu uygula (ayarlar.json bozulmadan).
- Kabul: Yetkisiz kullanici menude sayfa gormez.
- Risk: Yetkili sayfa yanlislikla gizlenebilir.
- Test: rol bazli menu snapshot.

### ui/main_window.py
- Gorev: _on_menu_clicked veya _create_page icinde sayfa guard.
- Kabul: Yetkisiz sayfaya dogrudan erisim engellenir.
- Risk: Guard by-pass (page map) kalir.
- Test: yetkisiz erisim denemesi.

### ui/pages/* (kritik aksiyonlar)
- Gorev: Ekle/sil/guncelle butonlari icin action-level permission.
- Kabul: Sadece yetkili rol butonlari gorur veya calistirir.
- Risk: UI disable var ama backend guard yoksa acik kalir.
- Test: action-level yetki testleri (manuel + smoke).

### database/seed veya yeni script
- Gorev: Ilk admin kullaniciyi ve temel permissionlari olustur.
- Kabul: Ilk kurulumda admin rolu hazir.
- Risk: Varsayilan sifre guvenlik riski.
- Test: seed calistirma testi.

### tests/
- Gorev: Auth ve authorization icin temel test seti.
- Kabul: Basarili/basarisiz login, rol bazli izin, menu filtre ve page guard testleri.
- Risk: UI testleri eksik kalir.
- Test: pytest ile tek komut.
