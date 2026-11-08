from urllib.parse import quote
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateImportStorage(FileSystemStorage):
    @property
    def location(self):
        return str(settings.PRIVATE_IMPORT_ROOT)

    @property
    def base_location(self):
        return str(settings.PRIVATE_IMPORT_ROOT)

    def url(self, name):
        return "/admin/catalog/importjob/files/" + quote(name, safe="/")
