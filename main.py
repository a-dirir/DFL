import multiprocessing
import shutil

from FL.node import FLNode
from FL.process import FLProcess
from FL.run import run
from os import path, mkdir
import utils.util as util
import numpy as np
from FL.node import FLNode
from os import path
from utils.util import save_file


def clean_fl_process(num_nodes, fl_id):
    tmp = ['logs','aggregation', 'data']
    for i in range(num_nodes):
        flprocess = FLProcess(i, fl_id)
        for j in tmp:
            directory = path.join(flprocess.fl_directory, j)
            shutil.rmtree(directory)

            mkdir(path.join(flprocess.fl_directory, j))

    for i in range(num_nodes):
        node = FLNode(node_id=i)
        tmp = np.random.random((9,10))
        for j in range(9):
            save_file(tmp[j].tobytes(), path.join(node.working_dir, 'FLProcesses', 'FLProcess_0', 'data'),
                       f'Node_{node.node_id}_Block_{j}.csv', node)


if __name__ == "__main__":
    # clean_fl_process(10, 0)
    processes = []
    for i in range(5):
        processes += [multiprocessing.Process(target=run, args=(i, 0))]
        processes[-1].start()

    for pi in processes:
        pi.join()
