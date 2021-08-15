import requests, json
from os import mkdir, path
from utils import util
from FL.node import FLNode

root_directory: str = path.normpath('D:\DFL')
control_server: str = "http://127.0.0.1:5000"


class FLProcess:
    def __init__(self, node_id: int, fl_process_id: int):
        self.node = FLNode(node_id=node_id)
        self.fl_process_id = fl_process_id
        self.fl_directory = path.join(path.join(self.node.working_dir, 'FLProcesses'),
                                      f'FLProcess_{self.fl_process_id}')

    def start(self):
        if not path.exists(self.fl_directory):
            participated, response = self.participate()
            if not participated:
                return {'message': response['message'], 'status': response['status']}

            mkdir(path.join(self.fl_directory))
            mkdir(path.join(self.fl_directory, 'data'))
            self.store_fl_process_config(response['fl_process'])
        else:
            self.load_fl_process_config()

    def store_fl_process_config(self, config):
        self.config = config
        with open(path.join(self.fl_directory, 'config.json'), 'w') as f:
            f.write(json.dumps(config))

    def load_fl_process_config(self):
        with open(path.join(self.fl_directory, 'config.json'), 'r') as f:
            self.config = json.loads(f.read())

    def get_info(self, fl_process_id, store_info=False):
        msg = {
            "node_id": self.node.node_id,
            "fl_process_id": fl_process_id,
            "signature_key": util.convert_to_string(self.node.signer.get_key())
        }
        msg = self.node.sign_message(msg)

        response = requests.post(f"{control_server}/getInfo", json=msg).json()
        if response['status'] == 200:
            if store_info:
                self.store_fl_process_config(response['fl_process'])
            return response['fl_process']
        else:
            return {}

    def participate(self):
        msg = {
            "node_id": self.node.node_id,
            "host": "127.0.0.1",
            "port": 5001 + self.node.node_id,
            "fl_process_id": self.fl_process_id,
            "signature_key": util.convert_to_string(self.node.signer.get_key()),
            "encryption_key": util.convert_to_string(self.node.encryptor_ec.get_key())
        }
        msg = self.node.sign_message(msg)

        response = requests.post(f"{control_server}/participate", json=msg).json()

        if response['status'] == 200:
            return True, response
        else:
            return False, response


