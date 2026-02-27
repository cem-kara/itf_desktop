# -*- coding: utf-8 -*-
"""
Personel Modülleri - Services
==============================
Avatar, cache, lazy-loading, dosya yönetimi.
"""

from .personel_avatar_service import (
    PersonelAvatarService,
    LazyLoadingManager,
    AvatarDownloaderWorker,
)
from .personel_file_service import PersonelFileService
from .personel_upload_service import PersonelUploadManager, DriveUploadWorker
from .personel_validators import (
    validate_tc_kimlik_no,
    validate_email,
    generate_username_from_name,
)

__all__ = [
    "PersonelAvatarService",
    "LazyLoadingManager",
    "AvatarDownloaderWorker",
    "PersonelFileService",
    "PersonelUploadManager",
    "DriveUploadWorker",
    "validate_tc_kimlik_no",
    "validate_email",
    "generate_username_from_name",
]
