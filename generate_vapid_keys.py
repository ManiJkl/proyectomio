"""Genera el par de claves VAPID. Ejecútalo una sola vez y guarda los valores
como variables de entorno en Render (VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY)."""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


key = ec.generate_private_key(ec.SECP256R1())
private = key.private_numbers().private_value.to_bytes(32, 'big')
public = key.public_key().public_bytes(
    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
)
print('VAPID_PUBLIC_KEY=' + b64(public))
print('VAPID_PRIVATE_KEY=' + b64(private))
