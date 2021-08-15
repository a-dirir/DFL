from mongoengine import connect, Document, IntField, DictField, ListField



class Node(Document):
    node_id = IntField(required=True, primary_key=True)
    node_info = DictField(required=True)
    meta = {'collection': 'Nodes'}


class FLProcess(Document):
    fl_process_id = IntField(required=True, primary_key=True)
    fl_process_config = DictField(required=True)
    participants = ListField(DictField(), default=list)

    meta = {'collection': 'FLProcesses'}
