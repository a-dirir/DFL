import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from uuid import uuid4


class AES:
    def __init__(self, key=None):
        self.aad = uuid4().bytes
        self.nonce = os.urandom(16)

        if key is None:
            self.key = AESGCM.generate_key(bit_length=256)
        else:
            self.key = key

        self.aes = AESGCM(self.key)

    def encrypt(self, msg_bytes):
        try:
            msg_encrypted = self.aes.encrypt(self.nonce, msg_bytes, self.aad)
            return self.nonce, msg_encrypted, self.aad
        except:
            return None, None, None

    def decrypt(self, nonce, cipher_text, aad):
        try:
            return self.aes.decrypt(nonce, cipher_text, aad)
        except:
            return None
