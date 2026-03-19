#!/usr/bin/env python3
"""
migrations.py dosyasını yenile - _seed_initial_data metodu temiz şekilde yaz
"""

def create_fixed_method():
    """Temiz _seed_initial_data metodu döndür."""
    return '''    def _seed_initial_data(self, cur):
        """
        Sabitler tablosuna başlangıç / sistem verilerini ekler.
        Tatiller tablosuna tatil tarihlerini ekler.
        Yalnızca yeni kurulumda çağrılır; mevcut kayıtların üzerine yazmaz.
        """
        # === SİSTEM SABİTLERİ ===
        sistem_sabitler = [
            ("1",   "Cihaz_Belge_Tur",   "NDK Lisansı",         "Cihazın NDK (Uygunluk Beyanı) Lisansı"),
            ("2",   "Cihaz_Belge_Tur",   "RKS Belgesi",          "Cihazın RKS (Radyasyon Koruma) Belgesi"),
            ("3",   "Cihaz_Belge_Tur",   "Sorumlu Diploması",    "Sorumlu kiŞinin diploması"),
            ("4",   "Cihaz_Belge_Tur",   "Kullanım Klavuzu",     "Cihaz kullanım kılavuzu"),
            ("5",   "Cihaz_Belge_Tur",   "Cihaz Sertifikası",    "Cihaz sertifikası/belgelendirmesi"),
            ("6",   "Cihaz_Belge_Tur",   "Teknik Veri Sayfası",  "Cihazın teknik özellikleri"),
            ("7",   "Cihaz_Belge_Tur",   "Garantı Belgesi",      "Cihaz garanti belgesi"),
            ("101", "Personel_Belge_Tur", "Diploma",             "Personel diploması"),
            ("102", "Personel_Belge_Tur", "Sertifika",           "Personel sertifikası"),
            ("103", "Personel_Belge_Tur", "Ehliyet",             "Personel ehliyet belgesi"),
            ("104", "Personel_Belge_Tur", "Kimlik",              "Personel kimlik belgesi"),
            ("105", "Personel_Belge_Tur", "Diğer",               "Personel diğer belgeler"),
            ("Va9ujcAP", "Hizmet_Sinifi", "Akademik Personel", ""),
            ("ve4VUaVw", "Hizmet_Sinifi", "Asistan Doktor", ""),
            ("emAxxVKJ", "Hizmet_Sinifi", "Hasta Bakımı / Temizlik Hizmetleri", ""),
            ("SKwldxW2", "Hizmet_Sinifi", "Hemşire", ""),
            ("NBuvaVB5", "Hizmet_Sinifi", "Radyasyon Görevlisi", ""),
            ("ztkwmDy6", "Hizmet_Sinifi", "Sekreterya / Memur", ""),
            ("Suy53nUe", "Kadro_Unvani", "Doçent Doktor", ""),
            ("bsvgTcUg", "Kadro_Unvani", "Doktor", ""),
            ("t085Vc7C", "Kadro_Unvani", "Doktor Öğretim Üyesi", ""),
            ("HCNTkUMH", "Kadro_Unvani", "Hemşire", ""),
            ("NP6EJ97a", "Kadro_Unvani", "Radyoloji Teknikeri", ""),
            ("PiA71O6E", "Kadro_Unvani", "Radyoloji Teknisyeni", ""),
            ("Oru7ycw8", "Kadro_Unvani", "Uzman Doktor", ""),
            ("2CrECP60", "Kadro_Unvani", "Profesör Doktor", ""),
            ("2DOEEc84", "Kadro_Unvani", "Radyoloji Teknik Personeli", ""),
            ("dKsSF10v", "İzin_Tipi", "Aylıksız İzin - Askerlik Nedeniyle", ""),
            ("r2IGntPn", "İzin_Tipi", "Aylıksız İzin - Doğum Nedeniyle", ""),
            ("i0M6NNC7", "İzin_Tipi", "Doğum İzni (Eşinin)", "10"),
            ("ao0Kx2d4", "İzin_Tipi", "Doğum Öncesi İzin", "42"),
            ("WWd1z0Cw", "İzin_Tipi", "Doğum Sonrası İzin", "42"),
            ("WmcMwHdW", "İzin_Tipi", "Evlenme-Ölüm İzni", ""),
            ("wZiEkYi6", "İzin_Tipi", "Yıllık İzin", "30"),
            ("1uVpfLkE", "İzin_Tipi", "İdari İzin", ""),
            ("1lg6ylDc", "İzin_Tipi", "Şua İzni", "30"),
            ("5fe67e55", "İzin_Tipi", "Rapor İzni", ""),
            ("65c2c039", "İzin_Tipi", "Mazeret", ""),
            ("f6808862", "Cihaz_Tipi", "Görüntüleme (Radyasyon Kaynaklı)", "XRY"),
            ("f6808863", "Cihaz_Tipi", "Görüntüleme (Diğer)", "GOR"),
            ("f6808864", "Cihaz_Tipi", "Medikal Cihazlar", "MED"),
            ("c165c961", "Garanti_Durum", "Hayır", ""),
            ("64ab0b68", "Garanti_Durum", "Evet", ""),
            ("c6AY34nE", "Lisans_Durum", "Lisansız", ""),
            ("nNDdYjEN", "Lisans_Durum", "Lisanslı", ""),
            ("CeomIRZw", "Lisans_Durum", "Lisans Gerekli Değil", ""),
            ("87338a69", "Kalibrasyon_Durum", "Evet", ""),
            ("87338a70", "Kalibrasyon_Durum", "Hayır", ""),
            ("87338a71", "Bakim_Durum", "Evet", ""),
            ("87338a72", "Bakim_Durum", "Hayır", ""),
            ("b1c78062", "Ariza_Durum", "İşlemde", ""),
            ("b1c78063", "Ariza_Durum", "Parça Bekliyor", ""),
            ("b1c78064", "Ariza_Durum", "Dış Serviste", ""),
            ("b1c78065", "Ariza_Durum", "Kapalı (Çözüldü)", ""),
            ("b1c78066", "Ariza_Durum", "Kapalı (İptal)", ""),
        ]
        
        added_count = 0
        for rowid, kod, menu_eleman, aciklama in sistem_sabitler:
            cur.execute(
                "SELECT COUNT(*) FROM Sabitler WHERE Kod = ? AND MenuEleman = ?",
                (kod, menu_eleman)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Sabitler (Rowid, Kod, MenuEleman, Aciklama) VALUES (?, ?, ?, ?)",
                    (rowid, kod, menu_eleman, aciklama)
                )
                added_count += 1
        
        if added_count > 0:
            logger.info(f"  ✓ Sabitler: {added_count} kayıt eklendi")
        
        # === TATİLLER ===
        tatiller = [
            ("2025-01-01", "Yeni Yıl"),
            ("2025-04-23", "Ulusal Egemenlik Günü"),
            ("2025-05-01", "Emek ve Dayanışma Günü"),
            ("2025-07-15", "Demokrasi ve Milli Birlik Günü"),
            ("2025-08-30", "Zafer Bayramı"),
            ("2025-10-29", "Cumhuriyet Bayramı"),
        ]
        
        added_tatil = 0
        for tarih, ad in tatiller:
            cur.execute(
                "SELECT COUNT(*) FROM Tatiller WHERE Tarih = ?",
                (tarih,)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Tatiller (Tarih, ResmiTatil) VALUES (?, ?)",
                    (tarih, ad)
                )
                added_tatil += 1
        
        if added_tatil > 0:
            logger.info(f"  ✓ Tatillər: {added_tatil} kayıt eklendi")
'''

def main():
from pathlib import Path
import re
    
    migrations_path = Path("database/migrations.py")
    
    with open(migrations_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # _seed_initial_data metodunu bulun ve replace et
    # Pattern: "def _seed_initial_data" den sonraki komple metodu bul
    pattern = r'(    def _seed_initial_data\(self, cur\):.*?)(    def [a-z_]+\(self)'
    
    new_method = create_fixed_method()
    
    # Match bul
    match = re.search(pattern, content, re.DOTALL)
    if match:
        old_method_and_next_def_start = match.group(1)
        
        #Eski metodu sil, yerlerine yenisini koy
        new_content = content.replace(
            old_method_and_next_def_start,
            new_method + "\n\n"
        )
        
        with open(migrations_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print("✓ _seed_initial_data metodu temiz şekilde yazıldı!")
        return True
    else:
        print("Hata: Metod bulunamadı")
        return False

if __name__ == "__main__":
    main()
