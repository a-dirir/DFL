from binascii import hexlify, unhexlify
from time import time
from hashlib import sha256
from Crypto.aes import AES
from os import getcwd, path
import json



def find_element(element, arr):
    for idx, val in enumerate(arr):
        if val == element:
            return idx
    return -1


def convert_to_string(msg):
    return str(hexlify(msg), encoding='utf8')


def convert_to_bytes(msg):
    return unhexlify(bytes(msg, encoding='utf8'))


def get_current_time():
    return int(time())


def get_time_difference(given_time):
    return int(given_time - time())


def hash_msg(msg):
    return sha256(msg).digest()


def save_file(data_bytes, file_path, file_name, node):
    data_hash = hash_msg(data_bytes)

    aes = AES()
    aes_key = aes.key
    nonce, cipher_data, aad = aes.encrypt(data_bytes)
    cipher_hash = hash_msg(cipher_data)

    signature_data = node.signer.sign_message(data_hash)
    signature_cipher = node.signer.sign_message(cipher_hash)


    with open(path.join(file_path, file_name), 'wb') as f:
        f.write(cipher_data)
        with open(path.join(file_path, f'{path.splitext(file_name)[0]}_info.json'), 'w') as d:
            info = {
                "aes_key": convert_to_string(aes_key),
                "nonce": convert_to_string(nonce),
                "aad": convert_to_string(aad),
                "hash_data": data_hash.hex(),
                "hash_cipher": cipher_hash.hex(),
                "signature_data": convert_to_string(signature_data),
                "signature_cipher": convert_to_string(signature_cipher),
                "size": len(cipher_data)
            }
            d.write(json.dumps(info))


def read_file(file_path, file_name, info_only=False):
    with open(path.join(file_path, f'{path.splitext(file_name)[0]}_info.json'), 'r') as f:
        info = json.loads(f.read())
        if info_only:
            return info
        aes_key = convert_to_bytes(info['aes_key'])
        nonce = convert_to_bytes(info['nonce'])
        aad = convert_to_bytes(info['aad'])
        aes = AES(key=aes_key)
        with open(path.join(file_path, file_name), 'rb') as d:
            data_bytes = aes.decrypt(nonce, d.read(), aad)
            if data_bytes is not None:
                return data_bytes, info

    return None, None


def save_peer_file(cipher_block, file_path, file_name, info):
    with open(path.join(file_path, file_name), 'wb') as f:
        f.write(cipher_block)
        with open(path.join(file_path, f'{path.splitext(file_name)[0]}_info.json'), 'w') as d:
            d.write(json.dumps(info))


