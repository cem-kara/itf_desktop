"""Core package for REPYS"""

# Text utilities
from core.text_utils import (
    turkish_title_case,
    turkish_upper,
    turkish_lower,
    capitalize_first_letter,
    normalize_whitespace,
    format_phone_number,
    sanitize_filename
)

# Validators
from core.validators import (
    validate_tc_kimlik_no,
    validate_email,
    validate_phone_number,
    validate_not_empty,
    validate_length,
    validate_numeric,
    validate_alphanumeric,
    validate_date_format
)

__all__ = [
    # Text utilities
    'turkish_title_case',
    'turkish_upper',
    'turkish_lower',
    'capitalize_first_letter',
    'normalize_whitespace',
    'format_phone_number',
    'sanitize_filename',
    # Validators
    'validate_tc_kimlik_no',
    'validate_email',
    'validate_phone_number',
    'validate_not_empty',
    'validate_length',
    'validate_numeric',
    'validate_alphanumeric',
    'validate_date_format',
]
