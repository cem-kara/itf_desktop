#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tüm projedeki Python dosyalarında PySide6 enum'larını modern API'ye dönüştürme scripti

Kullanım:
    python scripts/fix_all_enums.py

Bu script projedeki tüm .py dosyalarını tarar ve eski PySide6 enum kullanımlarını
modern API formatına çevirir.

Örnek dönüşümler:
    Qt.AlignmentFlag.AlignCenter          -> Qt.AlignmentFlag.AlignCenter
    Qt.ItemDataRole.DisplayRole          -> Qt.ItemDataRole.DisplayRole
    QPainter.RenderHint.Antialiasing   -> QPainter.RenderHint.Antialiasing
    QFont.Weight.Bold              -> QFont.Weight.Bold
    vb.
"""

import os
import re
from pathlib import Path

def fix_enums(content):
    """Tüm enum kullanımlarını modern PySide6 formatına çevir"""
    
    replacements = [
        # Qt.ItemDataRole
        (r'\bQt\.DisplayRole\b', 'Qt.ItemDataRole.DisplayRole'),
        (r'\bQt\.SizeHintRole\b', 'Qt.ItemDataRole.SizeHintRole'),
        (r'\bQt\.TextAlignmentRole\b', 'Qt.ItemDataRole.TextAlignmentRole'),
        (r'\bQt\.UserRole\b', 'Qt.ItemDataRole.UserRole'),
        (r'\bQt\.EditRole\b', 'Qt.ItemDataRole.EditRole'),
        (r'\bQt\.ToolTipRole\b', 'Qt.ItemDataRole.ToolTipRole'),
        (r'\bQt\.StatusTipRole\b', 'Qt.ItemDataRole.StatusTipRole'),
        (r'\bQt\.DecorationRole\b', 'Qt.ItemDataRole.DecorationRole'),
        (r'\bQt\.BackgroundRole\b', 'Qt.ItemDataRole.BackgroundRole'),
        (r'\bQt\.ForegroundRole\b', 'Qt.ItemDataRole.ForegroundRole'),
        (r'\bQt\.CheckStateRole\b', 'Qt.ItemDataRole.CheckStateRole'),
        
        # Qt.AlignmentFlag
        (r'\bQt\.AlignCenter\b', 'Qt.AlignmentFlag.AlignCenter'),
        (r'\bQt\.AlignLeft\b', 'Qt.AlignmentFlag.AlignLeft'),
        (r'\bQt\.AlignRight\b', 'Qt.AlignmentFlag.AlignRight'),
        (r'\bQt\.AlignVCenter\b', 'Qt.AlignmentFlag.AlignVCenter'),
        (r'\bQt\.AlignTop\b', 'Qt.AlignmentFlag.AlignTop'),
        (r'\bQt\.AlignBottom\b', 'Qt.AlignmentFlag.AlignBottom'),
        (r'\bQt\.AlignHCenter\b', 'Qt.AlignmentFlag.AlignHCenter'),
        (r'\bQt\.AlignJustify\b', 'Qt.AlignmentFlag.AlignJustify'),
        
        # Qt.Orientation
        (r'\bQt\.Horizontal\b', 'Qt.Orientation.Horizontal'),
        (r'\bQt\.Vertical\b', 'Qt.Orientation.Vertical'),
        
        # Qt.GlobalColor
        (r'\bQt\.transparent\b', 'Qt.GlobalColor.transparent'),
        (r'\bQt\.white\b', 'Qt.GlobalColor.white'),
        (r'\bQt\.black\b', 'Qt.GlobalColor.black'),
        (r'\bQt\.red\b', 'Qt.GlobalColor.red'),
        (r'\bQt\.green\b', 'Qt.GlobalColor.green'),
        (r'\bQt\.blue\b', 'Qt.GlobalColor.blue'),
        (r'\bQt\.gray\b', 'Qt.GlobalColor.gray'),
        (r'\bQt\.darkGray\b', 'Qt.GlobalColor.darkGray'),
        (r'\bQt\.lightGray\b', 'Qt.GlobalColor.lightGray'),
        
        # Qt.TransformationMode
        (r'\bQt\.SmoothTransformation\b', 'Qt.TransformationMode.SmoothTransformation'),
        (r'\bQt\.FastTransformation\b', 'Qt.TransformationMode.FastTransformation'),
        
        # Qt.PenStyle
        (r'\bQt\.NoPen\b', 'Qt.PenStyle.NoPen'),
        (r'\bQt\.SolidLine\b', 'Qt.PenStyle.SolidLine'),
        (r'\bQt\.DashLine\b', 'Qt.PenStyle.DashLine'),
        
        # Qt.BrushStyle
        (r'\bQt\.NoBrush\b', 'Qt.BrushStyle.NoBrush'),
        (r'\bQt\.SolidPattern\b', 'Qt.BrushStyle.SolidPattern'),
        
        # Qt.TextElideMode
        (r'\bQt\.ElideRight\b', 'Qt.TextElideMode.ElideRight'),
        (r'\bQt\.ElideLeft\b', 'Qt.TextElideMode.ElideLeft'),
        (r'\bQt\.ElideMiddle\b', 'Qt.TextElideMode.ElideMiddle'),
        (r'\bQt\.ElideNone\b', 'Qt.TextElideMode.ElideNone'),
        
        # Qt.CursorShape
        (r'\bQt\.PointingHandCursor\b', 'Qt.CursorShape.PointingHandCursor'),
        (r'\bQt\.ArrowCursor\b', 'Qt.CursorShape.ArrowCursor'),
        (r'\bQt\.WaitCursor\b', 'Qt.CursorShape.WaitCursor'),
        (r'\bQt\.IBeamCursor\b', 'Qt.CursorShape.IBeamCursor'),
        
        # Qt.CaseSensitivity
        (r'\bQt\.CaseInsensitive\b', 'Qt.CaseSensitivity.CaseInsensitive'),
        (r'\bQt\.CaseSensitive\b', 'Qt.CaseSensitivity.CaseSensitive'),
        
        # Qt.ContextMenuPolicy
        (r'\bQt\.CustomContextMenu\b', 'Qt.ContextMenuPolicy.CustomContextMenu'),
        (r'\bQt\.NoContextMenu\b', 'Qt.ContextMenuPolicy.NoContextMenu'),
        (r'\bQt\.DefaultContextMenu\b', 'Qt.ContextMenuPolicy.DefaultContextMenu'),
        
        # Qt.SortOrder
        (r'\bQt\.AscendingOrder\b', 'Qt.SortOrder.AscendingOrder'),
        (r'\bQt\.DescendingOrder\b', 'Qt.SortOrder.DescendingOrder'),
        
        # Qt.CheckState
        (r'\bQt\.Checked\b', 'Qt.CheckState.Checked'),
        (r'\bQt\.Unchecked\b', 'Qt.CheckState.Unchecked'),
        (r'\bQt\.PartiallyChecked\b', 'Qt.CheckState.PartiallyChecked'),
        
        # Qt.ItemFlag
        (r'\bQt\.ItemIsEnabled\b', 'Qt.ItemFlag.ItemIsEnabled'),
        (r'\bQt\.ItemIsSelectable\b', 'Qt.ItemFlag.ItemIsSelectable'),
        (r'\bQt\.ItemIsEditable\b', 'Qt.ItemFlag.ItemIsEditable'),
        
        # Qt.FocusPolicy
        (r'\bQt\.NoFocus\b', 'Qt.FocusPolicy.NoFocus'),
        (r'\bQt\.StrongFocus\b', 'Qt.FocusPolicy.StrongFocus'),
        (r'\bQt\.WheelFocus\b', 'Qt.FocusPolicy.WheelFocus'),
        
        # Qt.WindowModality
        (r'\bQt\.ApplicationModal\b', 'Qt.WindowModality.ApplicationModal'),
        (r'\bQt\.WindowModal\b', 'Qt.WindowModality.WindowModal'),
        
        # Qt.Key
        (r'\bQt\.Key_Return\b', 'Qt.Key.Key_Return'),
        (r'\bQt\.Key_Enter\b', 'Qt.Key.Key_Enter'),
        (r'\bQt\.Key_Escape\b', 'Qt.Key.Key_Escape'),
        (r'\bQt\.Key_Delete\b', 'Qt.Key.Key_Delete'),
        
        # QPainter.RenderHint
        (r'\bQPainter\.Antialiasing\b', 'QPainter.RenderHint.Antialiasing'),
        (r'\bQPainter\.TextAntialiasing\b', 'QPainter.RenderHint.TextAntialiasing'),
        (r'\bQPainter\.SmoothPixmapTransform\b', 'QPainter.RenderHint.SmoothPixmapTransform'),
        
        # QPainter.CompositionMode
        (r'\bQPainter\.CompositionMode_SourceOver\b', 'QPainter.CompositionMode.CompositionMode_SourceOver'),
        
        # QFont.Weight
        (r'\bQFont\.Bold\b', 'QFont.Weight.Bold'),
        (r'\bQFont\.Medium\b', 'QFont.Weight.Medium'),
        (r'\bQFont\.Normal\b', 'QFont.Weight.Normal'),
        (r'\bQFont\.Light\b', 'QFont.Weight.Light'),
        (r'\bQFont\.DemiBold\b', 'QFont.Weight.DemiBold'),
        (r'\bQFont\.ExtraBold\b', 'QFont.Weight.ExtraBold'),
        (r'\bQFont\.Black\b', 'QFont.Weight.Black'),
        
        # QStyle.StateFlag
        (r'\bQStyle\.State_Selected\b', 'QStyle.StateFlag.State_Selected'),
        (r'\bQStyle\.State_Enabled\b', 'QStyle.StateFlag.State_Enabled'),
        (r'\bQStyle\.State_Active\b', 'QStyle.StateFlag.State_Active'),
        (r'\bQStyle\.State_HasFocus\b', 'QStyle.StateFlag.State_HasFocus'),
        (r'\bQStyle\.State_MouseOver\b', 'QStyle.StateFlag.State_MouseOver'),
        
        # QTableView/QAbstractItemView enums
        (r'\bQTableView\.SelectRows\b', 'QTableView.SelectionBehavior.SelectRows'),
        (r'\bQTableView\.SelectColumns\b', 'QTableView.SelectionBehavior.SelectColumns'),
        (r'\bQTableView\.SelectItems\b', 'QTableView.SelectionBehavior.SelectItems'),
        (r'\bQTableView\.SingleSelection\b', 'QTableView.SelectionMode.SingleSelection'),
        (r'\bQTableView\.MultiSelection\b', 'QTableView.SelectionMode.MultiSelection'),
        (r'\bQTableView\.ExtendedSelection\b', 'QTableView.SelectionMode.ExtendedSelection'),
        (r'\bQTableView\.NoSelection\b', 'QTableView.SelectionMode.NoSelection'),
        
        # QAbstractItemView (QTableView parent'ı için)
        (r'\bQAbstractItemView\.SelectRows\b', 'QAbstractItemView.SelectionBehavior.SelectRows'),
        (r'\bQAbstractItemView\.SingleSelection\b', 'QAbstractItemView.SelectionMode.SingleSelection'),
        
        # QHeaderView.ResizeMode
        (r'\bQHeaderView\.Fixed\b', 'QHeaderView.ResizeMode.Fixed'),
        (r'\bQHeaderView\.Stretch\b', 'QHeaderView.ResizeMode.Stretch'),
        (r'\bQHeaderView\.Interactive\b', 'QHeaderView.ResizeMode.Interactive'),
        (r'\bQHeaderView\.ResizeToContents\b', 'QHeaderView.ResizeMode.ResizeToContents'),
        
        # QMessageBox.StandardButton
        (r'\bQMessageBox\.Yes\b', 'QMessageBox.StandardButton.Yes'),
        (r'\bQMessageBox\.No\b', 'QMessageBox.StandardButton.No'),
        (r'\bQMessageBox\.Ok\b', 'QMessageBox.StandardButton.Ok'),
        (r'\bQMessageBox\.Cancel\b', 'QMessageBox.StandardButton.Cancel'),
        (r'\bQMessageBox\.Close\b', 'QMessageBox.StandardButton.Close'),
        (r'\bQMessageBox\.Apply\b', 'QMessageBox.StandardButton.Apply'),
        (r'\bQMessageBox\.Reset\b', 'QMessageBox.StandardButton.Reset'),
        
        # QMessageBox.Icon
        (r'\bQMessageBox\.Warning\b', 'QMessageBox.Icon.Warning'),
        (r'\bQMessageBox\.Information\b', 'QMessageBox.Icon.Information'),
        (r'\bQMessageBox\.Question\b', 'QMessageBox.Icon.Question'),
        (r'\bQMessageBox\.Critical\b', 'QMessageBox.Icon.Critical'),
        
        # QDialog.DialogCode
        (r'\bQDialog\.Accepted\b', 'QDialog.DialogCode.Accepted'),
        (r'\bQDialog\.Rejected\b', 'QDialog.DialogCode.Rejected'),
        
        # QSizePolicy.Policy
        (r'\bQSizePolicy\.Fixed\b', 'QSizePolicy.Policy.Fixed'),
        (r'\bQSizePolicy\.Expanding\b', 'QSizePolicy.Policy.Expanding'),
        (r'\bQSizePolicy\.Minimum\b', 'QSizePolicy.Policy.Minimum'),
        (r'\bQSizePolicy\.Maximum\b', 'QSizePolicy.Policy.Maximum'),
        
        # QFrame.Shape
        (r'\bQFrame\.Box\b', 'QFrame.Shape.Box'),
        (r'\bQFrame\.Panel\b', 'QFrame.Shape.Panel'),
        (r'\bQFrame\.StyledPanel\b', 'QFrame.Shape.StyledPanel'),
        (r'\bQFrame\.HLine\b', 'QFrame.Shape.HLine'),
        (r'\bQFrame\.VLine\b', 'QFrame.Shape.VLine'),
        
        # QFrame.Shadow
        (r'\bQFrame\.Plain\b', 'QFrame.Shadow.Plain'),
        (r'\bQFrame\.Raised\b', 'QFrame.Shadow.Raised'),
        (r'\bQFrame\.Sunken\b', 'QFrame.Shadow.Sunken'),
    ]
    
    modified = False
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            modified = True
        content = new_content
    
    return content, modified


def process_file(file_path):
    """Tek bir dosyayı işle"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Enum'ları düzelt
        fixed_content, modified = fix_enums(content)
        
        if modified:
            # Dosyayı kaydet
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        return False
    except Exception as e:
        print(f"❌ Hata ({file_path}): {e}")
        return False


def main():
    """Ana işlem: Tüm Python dosyalarını tara ve düzelt"""
    # Script'in bulunduğu klasörden proje kök dizinini bul
    script_path = Path(__file__).resolve()
    if script_path.parent.name == 'scripts':
        project_root = script_path.parent.parent
    else:
        project_root = script_path.parent
    
    # Hariç tutulacak klasörler
    exclude_dirs = {
        '__pycache__', '.git', '.venv', 'venv', 'env',
        'node_modules', 'dist', 'build', '.pytest_cache'
    }
    
    # İşlenecek dosyaları bul
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Hariç tutulan klasörleri atla
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    print(f"🔍 Toplam {len(python_files)} Python dosyası bulundu.")
    print("📝 Enum dönüşümleri yapılıyor...\n")
    
    # Dosyaları işle
    modified_count = 0
    for file_path in python_files:
        if process_file(file_path):
            modified_count += 1
            try:
                rel_path = file_path.relative_to(project_root)
            except ValueError:
                rel_path = file_path
            print(f"✅ {rel_path}")
    
    print(f"\n{'='*60}")
    print(f"✨ Tamamlandı!")
    print(f"📊 {modified_count} dosya güncellendi.")
    print(f"📂 {len(python_files) - modified_count} dosya zaten günceldi.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
