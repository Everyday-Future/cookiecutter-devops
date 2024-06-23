import random
from collections import deque
from queue import PriorityQueue
import matplotlib.pyplot as plt


class Node:
    def __init__(self, value, depth=0, parent=None, id=0):
        self.value = value
        self.heuristic_value = random.random()  # Random heuristic value for Greedy and A*
        self.children = []
        self.depth = depth
        self.parent = parent
        self.id = id  # Unique identifier for visualization
        self.g = 0  # Cost from start to node
        self.h = self.heuristic_value  # Heuristic from node to goal (for A*)
        self.f = self.g + self.h  # Total cost


class Graph:
    def __init__(self, root=None, nodes=None, edges=None):
        self.root = root or Node(self.new_node_value(), depth=0)
        nodes = [self.root]
        self.nodes = nodes or []
        self.edges = edges or []

    def add_node(self, node):
        self.nodes.append(node)

    def add_edge(self, parent, child):
        self.edges.append((parent, child))

    def is_valid_branch(self, **kwargs):
        """
        Should we bother to check out this branch?
        """
        return random.choice([True, False])

    def new_node_value(self, **kwargs):
        """
        What is the value of this new attempt?
        """
        return random.random()

    def num_branches(self):
        """
        How many possible new paths could we try from here?
        """
        return random.randint(1, 4)

    def dfs(self, node, max_depth=10):
        if node.depth > max_depth:
            return
        node.id = len(self.nodes)  # Assign ID based on current nodes length
        self.add_node(node)
        if node.parent:
            self.add_edge(node.parent, node)
        branches = self.num_branches()
        for _ in range(branches):
            expand_node = self.is_valid_branch()  # Decide whether to expand from this node
            if expand_node:
                new_node = Node(self.new_node_value(), node.depth + 1, node)
                node.children.append(new_node)
                self.dfs(new_node, max_depth)

    def bfs(self, max_depth=10):
        queue = deque([(self.root, 0)])
        while queue:
            current_node, depth = queue.popleft()
            if depth > max_depth:
                continue
            current_node.id = len(self.nodes)
            self.add_node(current_node)
            if current_node.parent:
                self.add_edge(current_node.parent, current_node)
            branches = self.num_branches()
            for _ in range(branches):
                expand_node = self.is_valid_branch()  # Decide whether to expand from this node
                if expand_node:
                    new_node = Node(self.new_node_value(), current_node.depth + 1, current_node)
                    current_node.children.append(new_node)
                    queue.append((new_node, depth + 1))

    def greedy_best_first_search(self, max_depth=10):
        priority_queue = PriorityQueue()
        self.root.id = len(self.nodes)
        priority_queue.put((self.root.heuristic_value, self.root.id, self.root))
        while not priority_queue.empty():
            _, _, current_node = priority_queue.get()
            if current_node.depth > max_depth:
                continue
            self.add_node(current_node)
            if current_node.parent:
                self.add_edge(current_node.parent, current_node)
            branches = self.num_branches()
            for _ in range(branches):
                expand_node = self.is_valid_branch()  # Decide whether to expand from this node
                if expand_node:
                    new_node = Node(self.new_node_value(), current_node.depth + 1, current_node)
                    new_node.id = len(self.nodes)
                    current_node.children.append(new_node)
                    priority_queue.put((new_node.heuristic_value, new_node.id, new_node))

    def a_star_search(self, max_depth=10):
        priority_queue = PriorityQueue()
        self.root.g = 0  # Actual cost to reach the current node
        self.root.h = self.root.heuristic_value  # Estimated cost from current to goal
        self.root.f = self.root.g + self.root.h  # Total cost
        self.root.id = len(self.nodes)
        priority_queue.put((self.root.f, self.root.id, self.root))
        while not priority_queue.empty():
            _, _, current_node = priority_queue.get()
            if current_node.depth > max_depth:
                continue
            self.add_node(current_node)
            if current_node.parent:
                self.add_edge(current_node.parent, current_node)
            branches = self.num_branches()
            for _ in range(branches):
                expand_node = self.is_valid_branch()  # Decide whether to expand from this node
                if expand_node:
                    new_node_value = self.new_node_value()  # Determine the new node's value
                    new_node = Node(new_node_value, current_node.depth + 1, current_node)
                    new_node.id = len(self.nodes)
                    new_node.g = current_node.g + 1  # Assuming a uniform cost
                    new_node.h = new_node.heuristic_value
                    new_node.f = new_node.g + new_node.h
                    current_node.children.append(new_node)
                    priority_queue.put((new_node.f, new_node.id, new_node))

    def plot(self):
        plt.figure(figsize=(12, 8))
        for parent, child in self.edges:
            plt.plot([parent.depth, child.depth], [parent.id, child.id], 'k-', lw=2)
        for node in self.nodes:
            color = 'blue' if node.value else 'red'
            plt.scatter(node.depth, node.id, color=color, s=100, label=f'Node {node.id}: {node.value}')
        plt.xlabel('Depth')
        plt.ylabel('Node ID')
        plt.title('Graph Exploration')
        plt.show()


def main(search_method='dfs', max_depth=10):
    graph = Graph()
    if search_method == 'dfs':
        graph.dfs(node=graph.root, max_depth=max_depth)
    elif search_method == 'bfs':
        graph.bfs(max_depth)
    elif search_method == 'greedy':
        graph.greedy_best_first_search(max_depth)
    elif search_method == 'a_star':
        graph.a_star_search(max_depth)
    graph.plot()


if __name__ == "__main__":
    main(search_method='a_star', max_depth=10)
