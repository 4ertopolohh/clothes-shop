from cryptography.fernet import Fernet
from django.conf import settings


def encrypt(value):
    return (
        Fernet(settings.ENCRYPTION_KEY.encode()).encrypt(value.encode())
        if value
        else b""
    )


def decrypt(value):
    return (
        Fernet(settings.ENCRYPTION_KEY.encode()).decrypt(bytes(value)).decode()
        if value
        else ""
    )
