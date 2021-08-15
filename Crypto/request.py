from Crypto.aes import AES
from FL.node import FLNode
from utils.util import convert_to_bytes, convert_to_string
import pickle


class SecureRequest:
    def __init__(self, node: FLNode, peer_ec_key: bytes):
        self.node = node
        self.shared_key = self.node.encryptor_ec.get_shared_key(peer_ec_key)
        self.aes = AES(self.shared_key)

    def prepare_request(self, msg):
        msg_byte = pickle.dumps(msg)
        signature = self.node.signer.sign_message(msg_byte)
        nonce, msg_cipher, aad = self.aes.encrypt(msg_byte)

        if signature is None or msg_cipher is None:
            return None

        request = {
            "requester_id": self.node.node_id,
            "msg": msg_cipher,
            "nonce": nonce,
            "aad": aad,
            "signature": signature,
            "signature_key": self.node.signer.get_key(),
            "encryption_key": self.node.encryptor_ec.get_key(),
        }

        for key in request.keys():
            if type(request[key]) == bytes:
                request[key] = convert_to_string(request[key])

        return request

    def process_request(self, request):
        for key in request.keys():
            if type(request[key]) == str:
                request[key] = convert_to_bytes(request[key])

        shared_key = self.node.encryptor_ec.get_shared_key(request['encryption_key'])
        nonce, aad = request['nonce'], request['aad']
        aes = AES(key=shared_key)
        msg_byte = aes.decrypt(nonce, request['msg'], aad)
        if self.node.signer.verify_other_signatures(request['signature'],msg_byte, request['signature_key']):
            return pickle.loads(msg_byte)
        else:
            return None
