import threading
import time
from FL.server import Server
from FL.client1 import Client

if __name__ == '__main__':
    pass


def run(node_id, fl_process_id):
    server_thread = threading.Thread(target=Server, args= (node_id, fl_process_id), daemon=True)
    client_thread = threading.Thread(target=Client, args=(node_id, fl_process_id), daemon=True)

    server_thread.start()
    client_thread.start()
    server_thread.join(120)
    client_thread.join(180)

    # run(7,1)








