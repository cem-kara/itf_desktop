# -*- coding: utf-8 -*-
"""
AuthAudit tablosundaki başarısız giriş kayıtlarını silerek lockout'u kaldırır.
Kullanım: python reset_lockout.py
"""
import sqlite3
import sys
import os

# DB yolunu otomatik bul
script_dir = os.path.dirname(os.path.abspath(__file__))
candidates = [
    os.path.join(script_dir, "data", "repys.db"),
    os.path.join(script_dir, "repys.db"),
    os.path.join(script_dir, "database.db"),
    os.path.join(script_dir, "data", "database.db"),
]

db_path = None
for p in candidates:
    if os.path.exists(p):
        db_path = p
        break

if not db_path:
    # Tüm alt klasörlerde ara
    for root, dirs, files in os.walk(script_dir):
        for f in files:
            if f.endswith(".db"):
                db_path = os.path.join(root, f)
                break
        if db_path:
            break

if not db_path:
    print("❌ Veritabanı dosyası bulunamadı.")
    sys.exit(1)

print(f"📂 DB: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Mevcut başarısız kayıt sayısını göster
    cur.execute("SELECT COUNT(*) FROM AuthAudit WHERE Success = 0")
    count = cur.fetchone()[0]
    print(f"🔍 Başarısız giriş kaydı: {count} adet")

    # Son 1 saatteki başarısız kayıtları sil
    cur.execute("""
        DELETE FROM AuthAudit
        WHERE Success = 0
        AND CreatedAt >= datetime('now', '-1 hour')
    """)
    deleted = cur.rowcount
    conn.commit()
    conn.close()

    print(f"✅ {deleted} kayıt silindi — lockout kaldırıldı.")
    print("Uygulamayı yeniden başlatın ve tekrar giriş yapın.")

except sqlite3.OperationalError as e:
    print(f"❌ Hata: {e}")
    sys.exit(1)
