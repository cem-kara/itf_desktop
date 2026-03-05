"""
BakimService teste — Bakım servisi test kası
"""
import pytest
from unittest.mock import MagicMock, patch
from core.services.bakim_service import BakimService


@pytest.fixture
def mock_registry():
    """Mock RepositoryRegistry döndür"""
    registry = MagicMock()
    return registry


@pytest.fixture
def bakim_svc(mock_registry):
    """BakimService örneği döndür"""
    return BakimService(mock_registry)


class TestBakimServiceInitialize:
    """Başlatma testleri"""
    
    def test_init_gerekliyor_registry(self):
        """None registry'yle başlatılamaz"""
        with pytest.raises(ValueError):
            BakimService(None)
    
    def test_init_registry_kaydedilir(self, mock_registry):
        """Registry kaydedilir"""
        svc = BakimService(mock_registry)
        assert svc._r is mock_registry


class TestGetBakimListesi:
    """get_bakim_listesi metodunun testleri"""
    
    def test_tumunu_getir_bos(self, bakim_svc, mock_registry):
        """Boş liste döndür"""
        mock_registry.get("Periyodik_Bakim").get_all.return_value = []
        result = bakim_svc.get_bakim_listesi()
        assert result == []
    
    def test_tumunu_getir_tarih_siralama(self, bakim_svc, mock_registry):
        """Planlanan tarihe göre DESC sırala"""
        veri = [
            {"Planid": 1, "PlanlananTarih": "2026-01-15"},
            {"Planid": 2, "PlanlananTarih": "2026-02-10"},
            {"Planid": 3, "PlanlananTarih": "2026-01-01"},
        ]
        mock_registry.get("Periyodik_Bakim").get_all.return_value = veri
        
        result = bakim_svc.get_bakim_listesi()
        
        assert len(result) == 3
        assert result[0]["Planid"] == 2  # 2026-02-10 (en yeni)
        assert result[1]["Planid"] == 1  # 2026-01-15
        assert result[2]["Planid"] == 3  # 2026-01-01 (en eski)
    
    def test_cihaz_id_filtrele(self, bakim_svc, mock_registry):
        """Cihaz ID'sine göre filtrele"""
        veri = [
            {"Planid": 1, "Cihazid": "CIH001", "PlanlananTarih": "2026-01-01"},
            {"Planid": 2, "Cihazid": "CIH002", "PlanlananTarih": "2026-02-01"},
            {"Planid": 3, "Cihazid": "CIH001", "PlanlananTarih": "2026-03-01"},
        ]
        mock_registry.get("Periyodik_Bakim").get_all.return_value = veri
        
        result = bakim_svc.get_bakim_listesi(cihaz_id="CIH001")
        
        assert len(result) == 2
        assert all(r["Cihazid"] == "CIH001" for r in result)
        # DESC sırala
        assert result[0]["Planid"] == 3  # 2026-03-01
        assert result[1]["Planid"] == 1  # 2026-01-01
    
    def test_hata_guncelleme(self, bakim_svc, mock_registry):
        """Repository hatası boş liste döndür"""
        mock_registry.get("Periyodik_Bakim").get_all.side_effect = Exception("DB hatası")
        result = bakim_svc.get_bakim_listesi()
        assert result == []


class TestGetBakimTipleri:
    """get_bakim_tipleri metodunun testleri"""
    
    def test_turler_alindi(self, bakim_svc, mock_registry):
        """Bakım türlerini bul"""
        sabitler = [
            {"Kod": "BakimTipi", "MenuEleman": "Yağlama"},
            {"Kod": "BakimTipi", "MenuEleman": "Kontrol"},
            {"Kod": "BakimTipi", "MenuEleman": "Temizlik"},
            {"Kod": "DigerKod", "MenuEleman": "Yağlama"},  # Farklı kod, dahil edilmeyecek
        ]
        mock_registry.get("Sabitler").get_all.return_value = sabitler
        
        result = bakim_svc.get_bakim_tipleri()
        
        assert len(result) == 3
        assert "Yağlama" in result
        assert "Kontrol" in result
        assert "Temizlik" in result
    
    def test_turler_alfabetik_siralı(self, bakim_svc, mock_registry):
        """Türler alfabetik sıralı"""
        sabitler = [
            {"Kod": "BakimTipi", "MenuEleman": "Zincir"},
            {"Kod": "BakimTipi", "MenuEleman": "Arge"},
            {"Kod": "BakimTipi", "MenuEleman": "Temizlik"},
        ]
        mock_registry.get("Sabitler").get_all.return_value = sabitler
        
        result = bakim_svc.get_bakim_tipleri()
        
        assert result == ["Arge", "Temizlik", "Zincir"]
    
    def test_tekrarlar_temizlendi(self, bakim_svc, mock_registry):
        """Tekrarlayan türler temizlenir"""
        sabitler = [
            {"Kod": "BakimTipi", "MenuEleman": "Yağlama"},
            {"Kod": "BakimTipi", "MenuEleman": "Yağlama"},
            {"Kod": "BakimTipi", "MenuEleman": "Kontrol"},
        ]
        mock_registry.get("Sabitler").get_all.return_value = sabitler
        
        result = bakim_svc.get_bakim_tipleri()
        
        assert len(result) == 2
        assert result.count("Yağlama") == 1


class TestGetCihazListesi:
    """get_cihaz_listesi ve get_cihaz metodlarının testleri"""
    
    def test_cihaz_listesi_alindi(self, bakim_svc, mock_registry):
        """Cihaz listesini al"""
        cihazlar = [
            {"Cihazid": "CIH001", "CihazAdi": "Torba"},
            {"Cihazid": "CIH002", "CihazAdi": "Pompa"},
        ]
        mock_registry.get("Cihazlar").get_all.return_value = cihazlar
        
        result = bakim_svc.get_cihaz_listesi()
        
        assert len(result) == 2
        assert result[0]["CihazAdi"] == "Torba"
    
    def test_tek_cihaz_alindi(self, bakim_svc, mock_registry):
        """Tek cihazı ID'ye göre al"""
        cihaz = {"Cihazid": "CIH001", "CihazAdi": "Torba"}
        mock_registry.get("Cihazlar").get_by_pk.return_value = cihaz
        
        result = bakim_svc.get_cihaz("CIH001")
        
        assert result["CihazAdi"] == "Torba"
        mock_registry.get("Cihazlar").get_by_pk.assert_called_once_with("CIH001")
    
    def test_tek_cihaz_bulunamadi(self, bakim_svc, mock_registry):
        """Cihaz bulunamazsa None döndür"""
        mock_registry.get("Cihazlar").get_by_pk.return_value = None
        result = bakim_svc.get_cihaz("NONEXISTENT")
        assert result is None


class TestKaydet:
    """Bakım kaydı ekleme/güncelleme testleri"""
    
    def test_insert_basarili(self, bakim_svc, mock_registry):
        """Yeni bakım kaydı eklendi"""
        mock_repo = MagicMock()
        mock_registry.get.return_value = mock_repo
        
        veri = {
            "Cihazid": "CIH001",
            "BakimTipi": "Yağlama",
            "PlanlananTarih": "2026-01-15"
        }
        
        result = bakim_svc.kaydet(veri, guncelle=False)
        
        assert result is True
        mock_repo.insert.assert_called_once_with(veri)
    
    def test_update_basarili(self, bakim_svc, mock_registry):
        """Bakım kaydı güncellendi"""
        mock_repo = MagicMock()
        mock_registry.get.return_value = mock_repo
        
        veri = {
            "Planid": "1",
            "Cihazid": "CIH001",
            "BakimTipi": "Kontrol",
        }
        
        result = bakim_svc.kaydet(veri, guncelle=True)
        
        assert result is True
        mock_repo.update.assert_called_once_with("1", veri)
    
    def test_update_bez_planid(self, bakim_svc, mock_registry):
        """UPDATE'te Planid olmadan başarısız"""
        veri = {"Cihazid": "CIH001"}
        result = bakim_svc.kaydet(veri, guncelle=True)
        assert result is False
    
    def test_kaydet_hatası(self, bakim_svc, mock_registry):
        """Veritabanı hatası başarısızlıkla döner"""
        mock_repo = MagicMock()
        mock_repo.insert.side_effect = Exception("DB hatası")
        mock_registry.get.return_value = mock_repo
        
        veri = {"Cihazid": "CIH001"}
        result = bakim_svc.kaydet(veri, guncelle=False)
        
        assert result is False


class TestSil:
    """Bakım silme testleri"""
    
    def test_sil_basarili(self, bakim_svc, mock_registry):
        """Bakım kaydı silindi"""
        mock_repo = MagicMock()
        mock_registry.get.return_value = mock_repo
        
        result = bakim_svc.sil("1")
        
        assert result is True
        mock_repo.delete.assert_called_once_with("1")
    
    def test_sil_hatası(self, bakim_svc, mock_registry):
        """Silme hatası başarısızlıkla döner"""
        mock_repo = MagicMock()
        mock_repo.delete.side_effect = Exception("DB hatası")
        mock_registry.get.return_value = mock_repo
        
        result = bakim_svc.sil("1")
        
        assert result is False
