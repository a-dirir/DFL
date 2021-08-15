import numpy as np
from FL.node import FLNode
from os import path
from utils.util import save_file


for i in range(10):
    node = FLNode(node_id=i)
    # tmp = np.random((9,10)) * (i+1)
    tmp = np.random.random((9,10))
    for j in range(9):
        save_file(tmp[j].tobytes(), path.join(node.working_dir, 'FLProcesses', 'FLProcess_0', 'data'),
                   f'Node_{node.node_id}_Block_{j}.csv', node)
