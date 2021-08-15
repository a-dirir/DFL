import json
import pickle
from flask import Flask, request, jsonify

from Crypto.digital_signatures import DigitalSigner
from TrustedOracle.db_models import *
from utils.util import *


def validate_request(data):
    encryption_key = convert_to_bytes(data["encryption_key"])
    msg_byte = convert_to_bytes(data['msg'])
    signature_key = convert_to_bytes(data["signature_key"])
    signature = convert_to_bytes(data["signature"])

    authentic = DigitalSigner.verify_other_signatures(signature, msg_byte, signature_key)
    if authentic:
        return True, pickle.loads(msg_byte)
    else:
        return False, None


app = Flask(__name__)


@app.route('/createNewNode', methods=['POST'])
def register_node():
    data = request.get_json()

    authentic, msg = validate_request(data)
    if not authentic:
        return jsonify(status=431, message='Authentication Fails')

    node_id = Node.objects.count()
    Node(node_id=node_id, node_info=msg).save()

    return jsonify(node_id=node_id, status=200, message='You have successfully registered as a node')


@app.route('/deleteNode', methods=['POST'])
def delete_fl_node():
    data = request.get_json()

    authentic, msg = validate_request(data)
    if not authentic:
        return jsonify(status=431, message='Authentication Fails')

    try:
        node = Node.objects(node_id=int(msg["node_id"]))[0]
        if node.node_info['signature_key'] != msg['signature_key']:
            return jsonify(status=433, message='Your ID is not valid')

        node.delete()
        return jsonify(status=200, message='You have successfully deleted FL Node')

    except:
        return jsonify(status=400, message='Error')


@app.route('/createNewFLProcess', methods=['POST'])
def register_fl_process():
    data = request.get_json()

    authentic, msg = validate_request(data)
    if not authentic:
        return jsonify(status=431, message='Authentication Fails')
    try:
        node = Node.objects(node_id=int(msg["node_id"]))[0]
        if node.node_info['signature_key'] != msg['signature_key']:
            return jsonify(status=433, message='Your ID is not valid')

        fl_process_id = FLProcess.objects.count()

        FLProcess(fl_process_id=fl_process_id, fl_process_config=msg).save()

        return jsonify(fl_process_id=fl_process_id, status=200, message='You have successfully registered FL Process')
    except:
        return jsonify(status=400, message='Error')


@app.route('/participate', methods=['POST'])
def participate_in_fl_process():
    data = request.get_json()

    authentic, msg = validate_request(data)
    if not authentic:
        return jsonify(status=431, message='Authentication Fails')

    try:
        node = Node.objects(node_id=int(msg["node_id"]))[0]
        if node.node_info['signature_key'] != msg['signature_key']:
            return jsonify(status=433, message='Your ID is not valid')

        fl_process = FLProcess.objects(fl_process_id=int(msg["fl_process_id"]))

        if get_current_time() > fl_process[0].fl_process_config['participation_end']:
            return jsonify(status=432, message='Participation is over, nodes started serving models')

        fl_process.update_one(push__participants={
            'node_id': node.node_id,
            'host': msg['host'],
            'port': msg['port'],
            'encryption_key': msg['encryption_key'],
            'signature_key': msg['signature_key']
        })

        return jsonify(status=200, message='You have successfully registered FL Process',
                       fl_process=json.loads(fl_process[0].to_json()))

    except:
        return jsonify(status=400, message='Error')


@app.route('/getInfo', methods=['POST'])
def get_info():
    data = request.get_json()

    authentic, msg = validate_request(data)
    if not authentic:
        return jsonify(status=431, message='Authentication Fails')

    try:
        fl_process = FLProcess.objects(fl_process_id=int(msg["fl_process_id"]))[0]
        return jsonify(status=200, fl_process=json.loads(fl_process.to_json()))
    except:
        return jsonify(status=400, message='Error')



if __name__ == "__main__":
    connect("DFL", host="127.0.0.1", port=27017)
    app.run(host="127.0.0.1", port=5000)
