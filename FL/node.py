import requests, time, pickle
import shutil
from os import mkdir, path

from Crypto.aes import AES
from Crypto.digital_signatures import DigitalSigner
from Crypto.ec_key_exchange import ECKeyExchange
import utils.util as util


root_directory: str = path.normpath('D:\DFL')
control_server: str = "http://127.0.0.1:5000"


class FLNode:
    def __init__(self, **kwargs):
        if kwargs.get('node_id') is None:
            self.encryptor_ec = ECKeyExchange(generate_keys=True)
            self.signer = DigitalSigner(generate_keys=True)
            self.node_id = self.create_new_node()
            if self.node_id == -1:
                return

            self.working_dir = path.join(root_directory, f'Node_{self.node_id}')
            self.store_node_info()
        else:
            self.encryptor_ec = ECKeyExchange()
            self.signer = DigitalSigner()
            self.node_id = kwargs['node_id']
            self.working_dir = path.join(root_directory, f'Node_{self.node_id}')
            self.load_node_info()

    def sign_message(self, msg) -> dict:
        msg_bytes = pickle.dumps(msg)
        signature = util.convert_to_string(self.signer.sign_message(msg_bytes))
        signature_key = util.convert_to_string(self.signer.get_key())
        encryption_key = util.convert_to_string(self.encryptor_ec.get_key())
        return {
            'msg': util.convert_to_string(msg_bytes),
            'signature': signature,
            'signature_key': signature_key,
            'encryption_key': encryption_key
        }

    def create_new_node(self) -> int:
        msg = {
            "signature_key": util.convert_to_string(self.signer.get_key()),
            "encryption_key": util.convert_to_string(self.encryptor_ec.get_key())
        }
        msg = self.sign_message(msg)
        response = requests.post(f"{control_server}/createNewNode", json=msg).json()
        if response['status'] == 200:
            return response['node_id']
        else:
            return -1

    def store_node_info(self) -> None:
        if path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)

        mkdir(self.working_dir, 644)
        mkdir(path.join(self.working_dir, f'FLProcesses'), 644)
        self.encryptor_ec.store_keys(self.working_dir)
        self.signer.store_keys(self.working_dir)

    def load_node_info(self):
        self.encryptor_ec.load_keys(self.working_dir)
        self.signer.load_keys(self.working_dir)

    def delete_node(self):
        msg = {
            "node_id": self.node_id,
            "signature_key": util.convert_to_string(self.signer.get_key())
        }
        msg = self.sign_message(msg)

        response = requests.post(f"{control_server}/deleteNode", json=msg).json()
        if response['status'] == 200:
            shutil.rmtree(self.working_dir)
            return True
        else:
            return False

    def create_new_fl_process(self, **kwargs):
        msg = {
            "node_id": self.node_id, 'fl_name': kwargs['name'], 'file_extension': kwargs['file_extension'],
            'num_blocks': kwargs['num_blocks'], 'participation_end': int(time.time() + kwargs['pp']),
            'serving_end': int(time.time() + kwargs['pp'] + kwargs['sp']),'num_validators':3,
            "signature_key": util.convert_to_string(self.signer.get_key())
        }


        msg = self.sign_message(msg)
        response = requests.post(f"{control_server}/createNewFLProcess", json=msg).json()
        if response['status'] == 200:
            return response['fl_process_id']
        else:
            return -1

