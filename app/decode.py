"""
Logika dekódování AUSKEY z Lidl Silvercrest SmartKey Gateway.
Převzato z lidl_auskey_decode_v0.3.py
"""
from binascii import unhexlify
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def _aschar(b):
    """Převede byte na signed char."""
    return struct.unpack("b", bytes([b & 0xFF]))[0]


def _decode_kek(a):
    """Dekóduje KEK (Key Encryption Key) z raw bytes."""
    if len(a) != 16:
        raise ValueError(f"KEK incorrect length. Should be 16 was {len(a)}")
    kek = []
    for b in a:
        c1 = _aschar(a[0] * b)
        c2 = _aschar((a[0] * b) // 0x5d)
        kek += [_aschar(c1 + c2 * -0x5d + ord('!'))]
    return bytes(kek)


def _get_bytes(hex_string):
    """
    Parsuje hex string a vrací bytes.
    Podporuje formát s nebo bez ':' prefixu.
    """
    hex_string = hex_string.replace(" ", "").replace("\t", "").split(":")
    return unhexlify(hex_string[0] if len(hex_string) == 1 else hex_string[1])


def decode_auskey(kek_hex: str, auskey_line1: str, auskey_line2: str) -> dict:
    """
    Dekóduje AUSKEY a root password z KEK a encrypted AUSKEY.
    
    Args:
        kek_hex: Hex string KEK (jeden řádek)
        auskey_line1: První řádek encrypted AUSKEY (hex)
        auskey_line2: Druhý řádek encrypted AUSKEY (hex)
    
    Returns:
        dict s 'auskey' a 'root_password'
    
    Raises:
        ValueError: Pokud jsou vstupy neplatné
    """
    try:
        # Dekódování KEK
        kek_bytes = _get_bytes(kek_hex)
        kek = _decode_kek(kek_bytes)
        
        # Parsování encrypted AUSKEY
        encoded_key = _get_bytes(auskey_line1) + _get_bytes(auskey_line2)
        
        # AES ECB dekódování
        cipher = Cipher(algorithms.AES(kek), modes.ECB())
        decryptor = cipher.decryptor()
        auskey_bytes = decryptor.update(encoded_key) + decryptor.finalize()
        
        # Konverze na string
        auskey = auskey_bytes.decode("ascii")
        root_password = auskey[-8:]
        
        return {
            "auskey": auskey,
            "root_password": root_password
        }
    except Exception as e:
        raise ValueError(f"Chyba při dekódování: {str(e)}")
