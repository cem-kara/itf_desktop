"""
DokumanService Test Suite

Kapsam:
- Başlatma doğrulaması
- get_belgeler: entity filtresi ve doğru SonucYonetici döndürme
- sil
- upload_and_save: offline mod (SonucYonetici döndürür)

Not: Tüm metodlar SonucYonetici döndürür. Test'ler SonucYonetici.basarili ve SonucYonetici.veri'yi doğrular.
"""
import pytest
from unittest.mock import MagicMock, patch
from core.services.dokuman_service import DokumanService


# ─────────────────────────────────────────────────────────────
#  Fixture'lar
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def reg():
    return MagicMock()


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def svc(db, reg):
    return DokumanService(db, reg)


# ─────────────────────────────────────────────────────────────
#  Başlatma
# ─────────────────────────────────────────────────────────────

class TestInit:
    def test_none_db_ile_olusturulur(self, reg):
        s = DokumanService(None, reg)
        assert s is not None

    def test_registry_saklanir(self, db, reg):
        s = DokumanService(db, reg)
        assert s._registry is reg


# ─────────────────────────────────────────────────────────────
#  get_belgeler
# ─────────────────────────────────────────────────────────────

class TestGetBelgeler:
    def test_entity_filtresi(self, svc, reg):
        reg.get("Dokumanlar").get_where.return_value = [
            {"EntityType": "personel", "EntityId": "111", "BelgeTuru": "Diploma",   "Belge": "d1.pdf"},
            {"EntityType": "personel", "EntityId": "111", "BelgeTuru": "Sertifika", "Belge": "s1.pdf"},
        ]
        result = svc.get_belgeler("personel", "111")
        assert result.basarili is True
        assert len(result.veri) == 2
        assert all(d["EntityId"] == "111" for d in result.veri)

    def test_entity_sadece_tip(self, svc, reg):
        """Entity ID olmadan sadece tip ile filtrele."""
        reg.get("Dokumanlar").get_where.return_value = [
            {"EntityType": "cihaz", "EntityId": "C01", "BelgeTuru": "Lisans", "Belge": "l1.pdf"},
            {"EntityType": "cihaz", "EntityId": "C02", "BelgeTuru": "Lisans", "Belge": "l2.pdf"},
        ]
        result = svc.get_belgeler("cihaz")
        assert result.basarili is True
        assert len(result.veri) == 2

    def test_eslesme_yok_bos_liste(self, svc, reg):
        reg.get("Dokumanlar").get_where.return_value = []
        result = svc.get_belgeler("personel", "999")
        assert result.basarili is True
        assert result.veri == []

    def test_repo_hatasi(self, svc, reg):
        reg.get("Dokumanlar").get_where.side_effect = Exception("Hata")
        result = svc.get_belgeler("personel", "111")
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  upload_and_save — offline mod
# ─────────────────────────────────────────────────────────────

class TestUploadAndSave:
    def test_offline_mod_local_path_kaydeder(self, svc, reg, tmp_path):
        """
        Offline modda dosya yerel diske kopyalanır,
        DrivePath boş, mode='local' döner.
        """
        test_file = tmp_path / "rapor.pdf"
        test_file.write_bytes(b"PDF content")

        mock_repo = MagicMock()
        reg.get.return_value = mock_repo

        with patch("core.config.AppConfig.is_online_mode", return_value=False), \
             patch("shutil.copy2"), \
             patch("os.makedirs"):
            result = svc.upload_and_save(
                file_path=str(test_file),
                entity_type="personel",
                entity_id="12345678901",
                belge_turu="SaglikRapor",
                folder_name="Saglik_Raporlari",
                doc_type="Personel_Belge",
                custom_name="test_rapor.pdf",
            )

        assert result.basarili is True
        assert result.veri["mode"] == "local"
        assert result.veri.get("drive_link") in (None, "")

    def test_dosya_bulunamadiysa_basarisiz(self, svc):
        """Var olmayan dosya yolu → ok=False"""
        result = svc.upload_and_save(
            file_path="/tmp/kesinlikle_yok_12345.pdf",
            entity_type="personel",
            entity_id="111",
            belge_turu="Diploma",
            folder_name="Personel_Diploma",
            doc_type="Personel_Belge",
        )
        assert result.basarili is False


# ─────────────────────────────────────────────────────────────
#  sil
# ─────────────────────────────────────────────────────────────

class TestSil:
    def test_sil_basarili(self, svc, reg):
        mock_repo = MagicMock()
        reg.get.return_value = mock_repo
        result = svc.sil("personel", "111", "Diploma", "dosya.pdf")
        assert result.basarili is True
        mock_repo.delete.assert_called_once()

    def test_sil_hatasi_false(self, svc, reg):
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("Hata")
        reg.get.return_value = mock_repo
        result = svc.sil("personel", "111", "Diploma", "dosya.pdf")
        assert result.basarili is False
