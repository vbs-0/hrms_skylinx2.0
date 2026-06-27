import mimetypes
import os
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

@deconstructible
class SafeMimeValidator:
    """
    Validates that the file uploaded has a safe MIME type and extension.
    Blocks potentially executable/malicious files like .html, .exe, .php, etc.
    """
    
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # docx
        'text/plain',
        'text/csv',
    ]
    
    ALLOWED_EXTENSIONS = [
        '.pdf', '.jpg', '.jpeg', '.png', '.gif',
        '.xls', '.xlsx', '.doc', '.docx', '.txt', '.csv'
    ]

    def __init__(self, allowed_mimetypes=None, allowed_extensions=None):
        if allowed_mimetypes is not None:
            self.allowed_mimetypes = allowed_mimetypes
        else:
            self.allowed_mimetypes = self.ALLOWED_MIME_TYPES
            
        if allowed_extensions is not None:
            self.allowed_extensions = allowed_extensions
        else:
            self.allowed_extensions = self.ALLOWED_EXTENSIONS

    def __call__(self, value):
        # Check extension
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                _("File extension '%(extension)s' is not allowed. Allowed extensions are: '%(allowed_extensions)s'."),
                params={
                    'extension': ext,
                    'allowed_extensions': "', '".join(self.allowed_extensions)
                },
                code='invalid_extension'
            )
            
        # Check MIME type based on python's mimetypes module (since python-magic might not be installed)
        mime_type, _ = mimetypes.guess_type(value.name)
        if mime_type and mime_type not in self.allowed_mimetypes:
            raise ValidationError(
                _("File type '%(mime_type)s' is not allowed. Allowed types are: '%(allowed_mimetypes)s'."),
                params={
                    'mime_type': mime_type,
                    'allowed_mimetypes': "', '".join(self.allowed_mimetypes)
                },
                code='invalid_mimetype'
            )
            
    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.allowed_mimetypes == other.allowed_mimetypes and
            self.allowed_extensions == other.allowed_extensions
        )
