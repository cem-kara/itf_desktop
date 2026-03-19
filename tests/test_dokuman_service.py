"""
Test DokumanService file path handling
"""
import os
import tempfile
import shutil
from pathlib import Path

def test_dokuman_service_local_path():
    """
    Test eğer personel ile dosya yüklerse, DokumanService
    dosyayı data/offline_uploads/personel/<TC>/ klasörüne kaydeder mi?
    """
import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    
from database.sqlite_manager import SQLiteManager

from database.migrations import MigrationManager
from database.repository_registry import RepositoryRegistry
from core.services.dokuman_service import DokumanService
import tempfile
    
    # Test DB oluştur
    test_db_path = os.path.join(tempfile.gettempdir(), "repys_test_dokuman.db")
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    try:
        # DB'yi migrate et
        migration_mgr = MigrationManager(test_db_path)
        conn = migration_mgr.connect()
        cur = conn.cursor()
        migration_mgr.create_tables(cur)
        migration_mgr._seed_auth_data(cur)
        conn.commit()
        conn.close()
        
        # SQLiteManager'ı başlat
        db = SQLiteManager(test_db_path)
        registry = RepositoryRegistry(db)
        
        # Test dosyası oluştur
        test_file = os.path.join(tempfile.gettempdir(), "test_rapor.pdf")
        with open(test_file, "wb") as f:
            f.write(b"Test PDF content")
        
        # DokumanService ile yükle
        svc = DokumanService(db)
        result = svc.upload_and_save(
            file_path=test_file,
            entity_type="personel",
            entity_id="12345678901",  # Test TC
            belge_turu="SaglikRapor",
            folder_name="Saglik_Raporlari",  # Bu parametreyi etkisiz mi?
            doc_type="Personel_Belge",
            custom_name="12345678901_SaglikRapor_test.pdf",
            iliskili_id="KAYIT_001",
            iliskili_tip="Personel_Saglik_Takip",
        )
        
        print("\n=== UPLOAD RESULT ===")
        print(f"OK: {result['ok']}")
        print(f"Mode: {result['mode']}")
        print(f"LocalPath: {result['local_path']}")
        print(f"DriveLink: {result['drive_link']}")
        print(f"Error: {result['error']}")
        
        # Dokumanlar tablosundan oku
        dokuman_repo = registry.get("Dokumanlar")
        docs = dokuman_repo.get_where({
            "EntityType": "personel",
            "BelgeTuru": "SaglikRapor",
        })
        
        print("\n=== DOKUMANLAR TABLE RECORDS ===")
        for doc in docs:
            print(f"\nBelge: {doc.get('Belge')}")
            print(f"  EntityId: {doc.get('EntityId')}")
            print(f"  LocalPath: {doc.get('LocalPath')}")
            print(f"  DrivePath: {doc.get('DrivePath')}")
            print(f"  IliskiliBelgeID: {doc.get('IliskiliBelgeID')}")
            
            # Path var mı kontrol et
            if doc.get("LocalPath"):
                exists = os.path.exists(doc.get("LocalPath"))
                print(f"  ✅ Dosya var: {exists}" if exists else f"  ❌ Dosya YOHHHH")
        
        # Kontrol: LocalPath'in offline_uploads/personel/<TC> altında olup olmadığını kont
        assert result['ok'], "Upload başarısız oldu"
        assert result['mode'] == 'local', f"Expected 'local' mode, got '{result['mode']}'"
        
        # Path kontrolü
        expected_dir = os.path.join("data", "offline_uploads", "personel", "12345678901")
        assert expected_dir in result['local_path'], \
            f"Path '{result['local_path']}' içermediği '{expected_dir}'"
        
        # Dokumanlar tablosunda LocalPath var mı
        if docs:
            assert docs[0].get("LocalPath"), "LocalPath boş kaydedildi!"
            print("\n✅ TEST PASSED: Dosya doğru yola kaydedildi ve DB'de kayıtlandı")
        else:
            print("\n❌ TEST FAILED: Dokumanlar tablosuna kayıt eklenmedi")
        
    finally:
        # Temizle
        try:
            db.close()
        except:
            pass
        try:
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
        except:
            pass
        try:
            if os.path.exists(test_file):
                os.remove(test_file)
        except:
            pass


if __name__ == "__main__":
    test_dokuman_service_local_path()
