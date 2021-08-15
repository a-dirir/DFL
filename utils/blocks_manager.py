import numpy as np
from utils.util import find_element


class BlocksManager:
    def __init__(self, node_id, nodes, num_blocks, num_validators=2):
        self.node_id = node_id
        self.nodes = nodes
        self.num_nodes = len(nodes)
        self.num_blocks = num_blocks
        self.num_validators = num_validators

        if self.num_nodes < self.num_blocks:
            self.num_groups = 1
        else:
            self.num_groups = int(self.num_nodes / self.num_blocks)

        self.mappings = []
        self.create_mappings()
        self.group_mappings, self.group_members = self.set_group_mappings()
        self.lookup = self.build_lookup()

    def build_lookup(self):
        tmp = {}
        for index, node in enumerate(self.nodes):
            tmp[node] = index
        return tmp

    def create_mappings(self):
        passive_nodes_per_group = int(np.ceil((self.num_nodes % self.num_blocks) / self.num_groups))
        group_start = 0

        for i in range(self.num_groups):
            for j in range(self.num_blocks):
                tmp = []
                for k in range(self.num_blocks):
                    index = ((j + k * 2) % self.num_blocks) + i * self.num_blocks + group_start
                    tmp += [self.nodes[int(index)]]
                self.mappings += [[i,j,tmp]]

            tmp = []
            for k in range(passive_nodes_per_group):
                if group_start + k + (i+1) * self.num_blocks < self.num_nodes:
                    index = group_start + k + (i+1) * self.num_blocks
                    tmp += [int(index)]
            self.mappings += [[i, -1,tmp]]
            group_start += passive_nodes_per_group

    def set_group_mappings(self):
        tmp_mappings = []
        tmp_members = []

        for mapping in self.mappings:
            if self.node_id in mapping[2]:
                group_id = mapping[0]
                break

        for mapping in self.mappings:
            if mapping[0] == group_id:
                tmp_mappings += [mapping]
                for node in mapping[2]:
                    if node not in tmp_members and node != self.node_id:
                        tmp_members += [node]

        return tmp_mappings, tmp_members

    def is_validator(self, node_id, block_num, available_nodes):
        block_validators = self.group_mappings[block_num][2]
        node_index = find_element(node_id, block_validators)
        if node_index == -1:
            return False

        count = 0
        for i in range(node_index):
            if block_validators[i] in available_nodes:
                count += 1

        if count < self.num_validators:
            return True
        else:
            return False

    def is_judge(self, node_id, block_num, available_nodes):
        block_validators = self.group_mappings[block_num][2]
        node_index = find_element(node_id, block_validators)
        if node_index == -1:
            return False

        count = 0
        for i in range(node_index):
            if block_validators[i] in available_nodes:
                count += 1

        if count == self.num_validators:
            return True
        else:
            return False

    def get_blocks_to_validate(self, node_id, available_nodes):
        blocks_to_validate = []
        index = 0
        for mapping in self.group_mappings:
            if mapping[1] != -1 and self.is_validator(node_id, mapping[1], available_nodes):
                blocks_to_validate += [mapping[1]]
                index += 1
        return blocks_to_validate

    def get_blocks_to_judge(self, node_id, available_nodes):
        blocks_to_judge = []
        index = 0
        for mapping in self.group_mappings:
            if mapping[1] != -1 and self.is_judge(node_id, mapping[1], available_nodes):
                blocks_to_judge += [mapping[1]]
                index += 1
        return blocks_to_judge

    def get_active_nodes(self):
        return self.group_mappings[0][2]

    def get_passive_nodes(self):
        return self.group_mappings[self.num_blocks][2]

    def remove_passive_nodes(self, available_nodes):
        for passive_node in self.get_passive_nodes():
            index = find_element(passive_node, available_nodes)
            if index != -1:
                available_nodes.pop(index)
        return available_nodes