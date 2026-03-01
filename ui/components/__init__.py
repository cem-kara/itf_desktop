# -*- coding: utf-8 -*-
"""UI Components package for REPYS"""

# Formatted widgets
from ui.components.formatted_widgets import (
    apply_title_case_formatting,
    apply_uppercase_formatting,
    apply_lowercase_formatting,
    apply_phone_number_formatting,
    apply_numeric_only,
    apply_combo_title_case_formatting,
    create_title_case_line_edit,
    create_uppercase_line_edit,
    create_numeric_line_edit,
    create_phone_line_edit
)

__all__ = [
    # Formatting functions
    'apply_title_case_formatting',
    'apply_uppercase_formatting',
    'apply_lowercase_formatting',
    'apply_phone_number_formatting',
    'apply_numeric_only',
    'apply_combo_title_case_formatting',
    # Widget factory functions
    'create_title_case_line_edit',
    'create_uppercase_line_edit',
    'create_numeric_line_edit',
    'create_phone_line_edit',
]
