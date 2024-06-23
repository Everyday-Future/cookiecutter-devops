import unittest
from core.daos.graph import Node, Graph


class TestGraphMethods(unittest.TestCase):

    def test_add_node(self):
        """Test adding nodes to the graph."""
        graph = Graph()
        initial_node_count = len(graph.nodes)
        new_node = Node(graph.new_node_value())
        graph.add_node(new_node)
        self.assertEqual(len(graph.nodes), initial_node_count + 1)

    def test_add_edge(self):
        """Test adding edges to the graph."""
        graph = Graph()
        parent_node = Node(graph.new_node_value())
        child_node = Node(graph.new_node_value(), parent=parent_node)
        graph.add_node(parent_node)
        graph.add_node(child_node)
        graph.add_edge(parent_node, child_node)
        self.assertIn((parent_node, child_node), graph.edges)

    def test_is_valid_branch(self):
        """Test the is_valid_branch method."""
        graph = Graph()
        self.assertIn(graph.is_valid_branch(), [True, False])

    def test_new_node_value(self):
        """Test the new_node_value method."""
        graph = Graph()
        value = graph.new_node_value()
        self.assertTrue(isinstance(value, float))

    def test_num_branches(self):
        """Test the num_branches method."""
        graph = Graph()
        branches = graph.num_branches()
        self.assertTrue(1 <= branches <= 4)

    def test_dfs_expansion(self):
        """Test DFS expands the graph correctly."""
        graph = Graph()
        graph.dfs(graph.root, max_depth=2)
        # Assuming each node expands at least once, we expect more than one node
        self.assertGreater(len(graph.nodes), 1)

    def test_bfs_expansion(self):
        """Test BFS expands the graph correctly."""
        graph = Graph()
        graph.bfs(max_depth=2)
        self.assertGreater(len(graph.nodes), 1)

    def test_greedy_best_first_search_expansion(self):
        """Test Greedy Best-First Search expands the graph."""
        graph = Graph()
        graph.greedy_best_first_search(max_depth=2)
        self.assertGreater(len(graph.nodes), 1)

    def test_a_star_search_expansion(self):
        """Test A* Search expands the graph."""
        graph = Graph()
        graph.a_star_search(max_depth=2)
        self.assertGreater(len(graph.nodes), 1)


if __name__ == '__main__':
    unittest.main()
