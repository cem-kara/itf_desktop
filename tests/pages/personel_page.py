# tests/pages/personel_page.py
class PersonelEklePage:
    def __init__(self, qtbot, db):
        from ui.pages.personel.personel_ekle import PersonelEkle
        self.w = PersonelEkle(db=db)
        qtbot.addWidget(self.w)
        self.w.show()
    
    def tc_gir(self, tc): self.w._tc_edit.setText(tc)
    def ad_gir(self, ad): self.w._ad_edit.setText(ad)
    def kaydet(self, qtbot):
        from PySide6.QtCore import Qt
        qtbot.mouseClick(self.w.btn_kaydet, Qt.MouseButton.LeftButton)