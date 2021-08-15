from flask import send_file, request, Flask, make_response
from os import path
from FL.process import FLProcess
from Crypto.request import SecureRequest
from utils.blocks_manager import BlocksManager
from utils.util import read_file, get_time_difference, convert_to_bytes


class Server:
    def __init__(self, node_id, fl_process_id):
        self.node_id = node_id
        self.fl_process_id = fl_process_id
        self.fl_process = FLProcess(node_id=node_id, fl_process_id=fl_process_id)
        self.fl_process.start()
        self.fl_process_config = self.fl_process.config["fl_process_config"]
        self.participants = self.fl_process.config['participants']
        self.available_nodes = [self.participants[i]['node_id'] for i in range(len(self.participants))]
        self.current_stage = 0
        self.lookup = {}
        self.blocks_manager = BlocksManager(node_id, self.available_nodes, self.fl_process_config['num_blocks'])
        self.build_lookup()

        self.app = Flask(__name__)
        self.routes()
        self.app.run(port=self.participants[self.lookup[node_id]]["port"],
                     host=self.participants[self.lookup[node_id]]['host'])

    def build_lookup(self):
        for index, node in enumerate(self.participants):
            self.lookup[node['node_id']] = index

    def is_authorized(self, requester_id, msg):
        role = msg['role']
        if role == 'V':
            return self.blocks_manager.is_validator(requester_id, msg["block_num"],self.available_nodes)
        elif role == 'J':
            return self.blocks_manager.is_judge(requester_id, msg["block_num"],self.available_nodes)
        elif role == 'M':
            return requester_id in self.available_nodes

        return False

    def routes(self):
        @self.app.route('/', methods=["GET"])
        def heart_beat():
            if True:
                return make_response(f"I am still available", 200)
            else:
                return make_response(f"I am not available", 400)

        @self.app.route('/set_nodes', methods=["POST"])
        def set_available_nodes():
            self.current_stage += 1
            data = request.get_json()

            peer_key_encryption = convert_to_bytes(self.participants[self.lookup[self.node_id]]['encryption_key'])
            req = SecureRequest(self.fl_process.node, peer_key_encryption)
            msg = req.process_request(data)
            if msg is None:
                return make_response(f"Authentication Fails", 401)
            else:
                self.available_nodes = msg['nodes']
                return make_response(f"Success", 200)


        @self.app.route('/getFile', methods=["POST"])
        def return_requested_block():
            data = request.get_json()
            requester_id = data["requester_id"]
            req = SecureRequest(self.fl_process.node, convert_to_bytes(data['encryption_key']))
            msg = req.process_request(data)
            if msg is None:
                return make_response(f"Authentication Fails", 401)

            if not self.is_authorized(requester_id, msg):
                return make_response(f"Authorization Fails", 402)

            file_path = path.join(self.fl_process.fl_directory, msg['directory'])
            file_name = msg['filename']
            try:
                response = make_response(send_file(path.join(file_path,file_name)))
                meta_data = read_file(file_path, file_name, info_only=True)
                response.headers['meta_data'] = req.prepare_request(meta_data)
                return response
            except Exception as e:
                return make_response(f"There is an error, make sure you send a valid request", 404)

