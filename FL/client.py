import json
import pickle
import numpy as np
import requests
from os import path, mkdir, walk
from FL.process import FLProcess
from FL.server import Server
from utils.util import *
from utils.blocks_manager import BlocksManager
import time
from Crypto.request import SecureRequest
import threading
import logging

logging = logging.getLogger(__name__)

root_directory: str = path.normpath('D:\DFL')


class Client:
    def __init__(self,node_id, fl_process_id):
        self.current_stage = 0
        self.node_id = node_id
        self.fl_process_id = fl_process_id
        self.server_thread = threading.Thread(target=Server, args=(self.node_id, self.fl_process_id), daemon=True)
        self.fl_process = FLProcess(node_id=node_id, fl_process_id=fl_process_id)
        self.fl_process.start()
        self.fl_process_config = self.fl_process.config["fl_process_config"]
        self.participants = self.fl_process.config['participants']
        self.available_nodes = [self.participants[i]['node_id'] for i in range(len(self.participants))]
        self.lookup = {}
        self.build_lookup()
        self.logs = {}
        self.store_logs()
        self.blocks_manager = BlocksManager(node_id, self.available_nodes, self.fl_process_config['num_blocks'])
        self.get_available_nodes()
        time.sleep(2)
        self.download_blocks()
        time.sleep(2)
        self.download_logs()
        time.sleep(5)
        self.evaluate_logs()
        # time.sleep(5)
        # self.aggregate_blocks()
        # time.sleep(5)
        # self.download_blocks_hashes()
        # time.sleep(5)
        # self.print_hashes()

    def build_lookup(self):
        for index, node in enumerate(self.participants):
            self.lookup[node['node_id']] = index

    def store_logs(self):
        save_file(pickle.dumps(self.logs), path.join(self.fl_process.fl_directory, 'logs'),
                  f'Node_{self.node_id}_logs.json', self.fl_process.node)

    def check_availability(self, node):
        host = self.participants[self.lookup[node]]['host']
        port = self.participants[self.lookup[node]]['port']
        try:
            response = requests.get(f"http://{host}:{port}/")
            if response.status_code == 200:
                return True
            else:
                return False
        except:
            return False

    def get_file(self, owner, msg, log_response=False, log_key=None):
        host = self.participants[self.lookup[owner]]['host']
        port = self.participants[self.lookup[owner]]['port']
        peer_key_signature = convert_to_bytes(self.participants[self.lookup[owner]]['signature_key'])
        peer_key_encryption = convert_to_bytes(self.participants[self.lookup[owner]]['encryption_key'])
        req = SecureRequest(self.fl_process.node, peer_key_encryption)
        msg_byte = req.prepare_request(msg)

        try:
            response = requests.post(f"http://{host}:{port}/getFile", json=msg_byte)
            if response.status_code == 200:
                info = req.process_request(json.loads(response.headers['meta_data'].replace("'", "\"")))

                file_path = path.join(self.fl_process.fl_directory, msg['directory'])
                file_hash = hash_msg(response.content)

                is_valid_signature = self.fl_process.node.signer.\
                    verify_other_signatures(convert_to_bytes(info['signature_cipher']), file_hash, peer_key_signature)
                if is_valid_signature:
                    if log_response:
                        self.logs[log_key] = {
                            "stage": self.current_stage,
                            "sender": owner,
                            "receiver": self.node_id,
                            "msg": msg,
                            "hash_cipher": info['hash_cipher'],
                            "signature_cipher": info['signature_cipher'],
                            "signature_key": convert_to_string(peer_key_signature)
                        }
                    save_peer_file(response.content, file_path, msg['filename'], info)
                    return True
        except Exception as e:
            return False

    def download_blocks(self):
        if self.node_id not in [2,3,4]:
            blocks_to_request = self.blocks_manager.get_blocks_to_validate(self.node_id, self.available_nodes)
            if len(blocks_to_request) > 0:

                for block_num in blocks_to_request:
                    for node in self.available_nodes:
                        if node != self.node_id:
                            file_extension = self.fl_process_config["file_extension"]
                            file_name = f'Node_{node}_Block_{block_num}.{file_extension}'
                            msg = {"block_num": block_num, "role": "V", "directory": "data", "filename": file_name}
                            status = self.get_file(node, msg, True, f"{node}_{block_num}_{self.node_id}")

                self.store_logs()
                self.current_stage += 1

    def download_logs(self):
        passive_nodes = self.blocks_manager.get_passive_nodes()
        if self.node_id in passive_nodes:
            return

        nodes = self.blocks_manager.remove_passive_nodes(self.available_nodes)

        for node in nodes:
            if node != self.node_id:
                file_name = f'Node_{node}_logs.json'
                msg = {"role": "M", "directory": "logs", "filename": file_name}
                status = self.get_file(node, msg)

    def get_available_nodes(self):
        self.available_nodes = [self.node_id]
        for node in self.blocks_manager.group_members:
            if node != self.node_id and self.check_availability(node):
                self.available_nodes += [node]

        host = self.participants[self.lookup[self.node_id]]['host']
        port = self.participants[self.lookup[self.node_id]]['port']
        peer_key_encryption = convert_to_bytes(self.participants[self.lookup[self.node_id]]['encryption_key'])
        req = SecureRequest(self.fl_process.node, peer_key_encryption)
        msg_byte = req.prepare_request({"nodes": self.available_nodes})

        try:
            response = requests.post(f"http://{host}:{port}/set_nodes", json=msg_byte)
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            return False

    def evaluate_logs(self):
        evaluations = np.zeros((len(self.available_nodes),
                                self.blocks_manager.num_blocks,
                                len(self.available_nodes)))

        for _, _,filenames in walk(path.join(self.fl_process.fl_directory, 'logs')):
            for filename in filenames:
                if filename.find('_info') == -1:
                    logs = pickle.loads(read_file(path.join(self.fl_process.fl_directory, 'logs'), filename)[0])
                    for log in logs.values():
                        sender_index = find_element(log['sender'], self.available_nodes)
                        receiver_index = find_element(log['receiver'], self.available_nodes)
                        evaluations[sender_index][log['msg']['block_num']][receiver_index] += 1

        self.get_missing_blocks(evaluations)

        return evaluations

    def get_missing_blocks(self, evaluations):
        missing_blocks = []
        passive_nodes = self.blocks_manager.get_passive_nodes()

        for i, sender in enumerate(self.available_nodes):
            for block_num in range(self.blocks_manager.num_blocks):
                for j, receiver in enumerate(self.available_nodes):
                    if sender != receiver and receiver not in passive_nodes:
                        if self.blocks_manager.is_validator(receiver,block_num, self.available_nodes):
                            if evaluations[i][block_num][j] == 0:
                                missing_blocks += [{'sender': sender,'block_num': block_num,'receiver': receiver}]

        print(missing_blocks)

    def loading_block(self, block_num):
        results = []
        for _, _,filenames in walk(path.join(self.fl_process.fl_directory, 'data')):
            for filename in filenames:
                if filename.find('_info') == -1 and filename.find(f'Block_{block_num}') != -1:
                    block_bytes, _ = read_file(path.join(self.fl_process.fl_directory, 'data'), filename)
                    block_data = np.frombuffer(block_bytes, dtype=np.float)
                    results += [block_data]

        return results

    def aggregate_block(self, block_num, size, mul_factor=1000000):
        aggregation_result = np.zeros(size)
        blocks = self.loading_block(block_num)
        for block in blocks:
            aggregation_result += np.array((block * mul_factor), dtype=np.int)

        aggregation_result = aggregation_result / mul_factor
        aggregation_result_hash = hash_msg(aggregation_result.tobytes()).hex()
        return aggregation_result, aggregation_result_hash

    def aggregate_blocks(self):
        final_result = []
        for block_num in self.blocks_manager.get_blocks_to_validate(self.node_id, self.available_nodes):
            _, aggregation_result_hash = self.aggregate_block(block_num,(10))
            final_result += [{
                "block_num": block_num,
                "result_hash": aggregation_result_hash
            }]


        save_file(pickle.dumps(final_result), path.join(self.fl_process.fl_directory, 'aggregation'),
                   f'Node_{self.node_id}_Blocks_Hashes.json', self.fl_process.node)

    def download_blocks_hashes(self):
        passive_nodes = self.blocks_manager.get_passive_nodes()

        if self.node_id in passive_nodes:
            return

        for node in self.available_nodes:
            if node != self.node_id:
                file_name = f'Node_{node}_Blocks_Hashes.json'
                msg = {"role": "M", "directory": "aggregation", "filename": file_name}
                status = self.get_file(node, msg)

    def print_hashes(self):
        print(pickle.loads(read_file(path.join(self.fl_process.fl_directory, 'aggregation'),f'Node_{self.node_id}_Blocks_Hashes.json')[0]))



