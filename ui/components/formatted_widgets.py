# -*- coding: utf-8 -*-
"""
Otomatik formatlama özellikli Qt Widget'ları.
Kullanıcı girdilerini gerçek zamanlı olarak formatlar.
"""
from PySide6.QtWidgets import QLineEdit, QComboBox
from core.text_utils import turkish_title_case


def apply_title_case_formatting(line_edit: QLineEdit):
    """
    QLineEdit'e otomatik Title Case formatting ekler.
    Kullanıcı yazarken her kelimenin ilk harfi büyük yapılır.
    
    Args:
        line_edit: Formatlama uygulanacak QLineEdit widget
        
    Usage:
        >>> line_edit = QLineEdit()
        >>> apply_title_case_formatting(line_edit)
        >>> # Kullanıcı "ahmet cem" yazarsa otomatik "Ahmet Cem" olur
    """
    def on_text_changed():
        # Cursor pozisyonunu kaydet
        cursor_pos = line_edit.cursorPosition()
        current_text = line_edit.text()
        
        # Boşsa işlem yapma
        if not current_text:
            return
        
        # Tamamen boşluk karakteriyse işlem yapma
        if current_text.isspace():
            return
        
        # Title case uygula
        formatted_text = turkish_title_case(current_text)
        
        # Metin değiştiyse güncelle
        if formatted_text != current_text:
            # Signal'i geçici olarak blokla (sonsuz döngü önleme)
            line_edit.blockSignals(True)
            line_edit.setText(formatted_text)
            line_edit.blockSignals(False)
            
            # Cursor'u metnin sonuna koy (metin trim edildikten sonra)
            # Bu, kullanıcı yazarken en doğal davranış
            line_edit.setCursorPosition(len(formatted_text))
    
    line_edit.textChanged.connect(on_text_changed)


def apply_uppercase_formatting(line_edit: QLineEdit):
    """
    QLineEdit'e otomatik uppercase formatting ekler.
    
    Args:
        line_edit: Formatlama uygulanacak QLineEdit widget
    """
    def on_text_changed():
        cursor_pos = line_edit.cursorPosition()
        current_text = line_edit.text()
        
        if not current_text:
            return
        
        from core.text_utils import turkish_upper
        formatted_text = turkish_upper(current_text)
        
        if formatted_text != current_text:
            line_edit.blockSignals(True)
            line_edit.setText(formatted_text)
            line_edit.blockSignals(False)
            line_edit.setCursorPosition(min(cursor_pos, len(formatted_text)))
    
    line_edit.textChanged.connect(on_text_changed)


def apply_lowercase_formatting(line_edit: QLineEdit):
    """
    QLineEdit'e otomatik lowercase formatting ekler.
    
    Args:
        line_edit: Formatlama uygulanacak QLineEdit widget
    """
    def on_text_changed():
        cursor_pos = line_edit.cursorPosition()
        current_text = line_edit.text()
        
        if not current_text:
            return
        
        from core.text_utils import turkish_lower
        formatted_text = turkish_lower(current_text)
        
        if formatted_text != current_text:
            line_edit.blockSignals(True)
            line_edit.setText(formatted_text)
            line_edit.blockSignals(False)
            line_edit.setCursorPosition(min(cursor_pos, len(formatted_text)))
    
    line_edit.textChanged.connect(on_text_changed)


def apply_phone_number_formatting(line_edit: QLineEdit):
    """
    QLineEdit'e otomatik telefon numarası formatting ekler.
    Format: 0XXX XXX XX XX
    
    Args:
        line_edit: Formatlama uygulanacak QLineEdit widget
    """
    def on_text_changed():
        cursor_pos = line_edit.cursorPosition()
        current_text = line_edit.text()
        
        if not current_text:
            return
        
        from core.text_utils import format_phone_number
        formatted_text = format_phone_number(current_text)
        
        if formatted_text != current_text:
            line_edit.blockSignals(True)
            line_edit.setText(formatted_text)
            line_edit.blockSignals(False)
            # Telefon formatında cursor pozisyonu daha karmaşık
            line_edit.setCursorPosition(min(cursor_pos + 1, len(formatted_text)))
    
    line_edit.textChanged.connect(on_text_changed)


def apply_numeric_only(line_edit: QLineEdit):
    """
    QLineEdit'e sadece rakam girişi kısıtlaması ekler.
    
    Args:
        line_edit: Kısıtlama uygulanacak QLineEdit widget
    """
    def on_text_changed():
        cursor_pos = line_edit.cursorPosition()
        current_text = line_edit.text()
        
        if not current_text:
            return
        
        # Sadece rakamları tut
        numeric_only = ''.join(c for c in current_text if c.isdigit())
        
        if numeric_only != current_text:
            line_edit.blockSignals(True)
            line_edit.setText(numeric_only)
            line_edit.blockSignals(False)
            line_edit.setCursorPosition(min(cursor_pos, len(numeric_only)))
    
    line_edit.textChanged.connect(on_text_changed)


def apply_combo_title_case_formatting(combo: QComboBox):
    """
    Editable QComboBox'a otomatik Title Case formatting ekler.
    
    Args:
        combo: Formatlama uygulanacak QComboBox (editable olmalı)
        
    Usage:
        >>> combo = QComboBox()
        >>> combo.setEditable(True)
        >>> apply_combo_title_case_formatting(combo)
    """
    if not combo.isEditable():
        return
    
    line_edit = combo.lineEdit()
    if line_edit:
        apply_title_case_formatting(line_edit)


# Widget factory fonksiyonları (isteğe bağlı - kolaylık için)

def create_title_case_line_edit(**kwargs) -> QLineEdit:
    """
    Otomatik Title Case formatlama özellikli QLineEdit oluşturur.
    
    Args:
        **kwargs: QLineEdit constructor parametreleri
        
    Returns:
        Formatlanmış QLineEdit
    """
    line_edit = QLineEdit(**kwargs)
    apply_title_case_formatting(line_edit)
    return line_edit


def create_uppercase_line_edit(**kwargs) -> QLineEdit:
    """
    Otomatik uppercase formatlama özellikli QLineEdit oluşturur.
    
    Args:
        **kwargs: QLineEdit constructor parametreleri
        
    Returns:
        Formatlanmış QLineEdit
    """
    line_edit = QLineEdit(**kwargs)
    apply_uppercase_formatting(line_edit)
    return line_edit


def create_numeric_line_edit(**kwargs) -> QLineEdit:
    """
    Sadece rakam girişi özellikli QLineEdit oluşturur.
    
    Args:
        **kwargs: QLineEdit constructor parametreleri
        
    Returns:
        Kısıtlanmış QLineEdit
    """
    line_edit = QLineEdit(**kwargs)
    apply_numeric_only(line_edit)
    return line_edit


def create_phone_line_edit(**kwargs) -> QLineEdit:
    """
    Otomatik telefon numarası formatlama özellikli QLineEdit oluşturur.
    
    Args:
        **kwargs: QLineEdit constructor parametreleri
        
    Returns:
        Formatlanmış QLineEdit
    """
    line_edit = QLineEdit(**kwargs)
    apply_phone_number_formatting(line_edit)
    return line_edit
