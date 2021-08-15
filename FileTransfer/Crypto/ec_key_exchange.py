from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from os import path, getcwd
from utils.util import convert_to_string, convert_to_bytes


class ECKeyExchange:
    def __init__(self, generate_keys=False):
        if generate_keys:
            self.generate_keys()
        self.shared_keys = {}

    def generate_keys(self):
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def get_key(self):
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes

    def store_keys(self, directory_path=getcwd()):
        private_key_bytes = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_key_str = convert_to_string(private_key_bytes)
        with open(path.join(directory_path,"private_key_encryption.pem"), "w") as f:
            f.write(private_key_str)

        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_str = convert_to_string(public_key_bytes)
        with open(path.join(directory_path,"public_key_encryption.pem"), "w") as f:
            f.write(public_key_str)

    def load_keys(self, directory_path=getcwd()):
        with open(path.join(directory_path, "private_key_encryption.pem"), "r") as f:
            private_key_bytes = convert_to_bytes(f.read())
            self.private_key = serialization.load_pem_private_key(private_key_bytes, password=None)

        with open(path.join(directory_path, "public_key_encryption.pem"), "r") as f:
            public_key_bytes = convert_to_bytes(f.read())
            self.public_key = serialization.load_pem_public_key(public_key_bytes)

    def clean_cache(self):
        self.shared_keys = {}

    def get_shared_key(self, peer_public_key):
        try:
            peer_public_key = serialization.load_pem_public_key(peer_public_key)

            shared_key = self.private_key.exchange(peer_public_key)
            derived_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"").derive(shared_key)
            return derived_key
        except:
            return None

