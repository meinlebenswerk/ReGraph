import networkx as nx

from nose.tools import raises

from regraph.library.rules import Rule
from regraph.library.utils import assert_graph_eq


class TestRule(object):

    def __init__(self):
        # Define meta-model for rules
        # self.meta_model = TypedDiGraph()

        # self.meta_model.add_node('black_square', 'square')
        # self.meta_model.add_node('white_square', 'square')
        # self.meta_model.add_node('black_circle', 'circle')
        # self.meta_model.add_node('white_circle', 'circle')

        # self.meta_model.add_edges_from([
        #         ('black_square', 'black_square'),
        #         ('black_square', 'white_square'),
        #         ('black_square', 'white_circle'),
        #         ('white_square', 'black_circle'),
        #         ('black_circle', 'white_circle'),
        #         ('white_circle', 'black_square')
        #     ])

        # Define the left hand side of the rule
        self.pattern = nx.DiGraph()
        self.pattern.add_node(1)
        self.pattern.add_node(2)
        self.pattern.add_node(3)
        self.pattern.add_node(4, {'a': 1})

        self.pattern.add_edges_from([
            (1, 2),
            (3, 2),
            (2, 3, {'a': {1}}),
            (4, 1)
        ])

        # Define preserved part of the rule
        self.p = nx.DiGraph()
        self.p.add_node('a')
        self.p.add_node('b')
        self.p.add_node('c')
        self.p.add_node('d', {'a': 1})

        self.p.add_edges_from([
            ('a', 'b'),
            ('b', 'c', {'a': {1}}),
            ('d', 'a')
        ])

        # Define the right hand side of the rule
        self.rhs = nx.DiGraph()
        self.rhs.add_node('x')
        self.rhs.add_node('y')
        self.rhs.add_node('z')
        self.rhs.add_node('s', {'a': 1})
        self.rhs.add_node('t')

        self.rhs.add_edges_from([
            ('x', 'y'),
            ('y', 'z', {'a': {1}}),
            ('s', 'x'),
            ('t', 'y')
        ])

        # Define mappings
        self.p_lhs = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.p_rhs = {'a': 'x', 'b': 'y', 'c': 'z', 'd': 's'}
        return

    def test_add_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_node('g', {'a': 1})
        assert_graph_eq(rule.p, self.p)
        assert_graph_eq(rule.lhs, self.pattern)
        assert('g' in rule.rhs)
        assert(rule.rhs.node['g'] == {'a': set([1])})
        return

    def test_remove_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_node(2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert('b' not in rule.p.nodes())
        assert(('a', 'b') not in rule.p.edges())
        assert(('b', 'c') not in rule.p.edges())
        assert('y' not in rule.rhs.nodes())
        assert(('x', 'y') not in rule.rhs.edges())
        assert(('t', 'y') not in rule.rhs.edges())
        assert(('y', 'z') not in rule.rhs.edges())
        return

    def test_add_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_edge(4, 2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert_graph_eq(rule.p, self.p)
        assert(('s', 'y') in rule.rhs.edges())
        return

    @raises(ValueError)
    def test_remove_non_existing_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_edge(3, 2)
        return

    def test_remove_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_edge(1, 2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert(('d', 'a') in rule.p.edges())
        assert(('s', 'x') in rule.rhs.edges())
        return

    def test_clone_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.clone_node(2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert('b1' in rule.p.nodes())
        assert('y1' in rule.rhs.nodes())
        assert(('a', 'b1') in rule.p.edges())
        assert(('b1', 'c') in rule.p.edges())
        assert(('x', 'y1') in rule.rhs.edges())
        assert(('t', 'y1') in rule.rhs.edges())
        return

    def test_merge_nodes(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        new_name = rule.merge_nodes(1, 4)
        assert_graph_eq(rule.lhs, self.pattern)
        assert_graph_eq(rule.p, self.p)
        assert(new_name in rule.rhs.nodes())
        assert((new_name, new_name) in rule.rhs.edges())
        assert((new_name, 'y') in rule.rhs.edges())
        return

    def test_add_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_node_attrs(1, {'a': 1})
        assert(rule.rhs.node['x'] == {'a': {1}})
        rule.add_node_attrs(4, {'a': 1})
        assert(rule.rhs.node['s'] == {'a': {1}})
        rule.add_node_attrs(4, {'a': 2})
        assert(rule.rhs.node['s'] == {'a': {1, 2}})
        rule.add_node_attrs(4, {'b': 1})
        assert(rule.rhs.node['s'] == {'a': {1, 2}, 'b': {1}})
        return

    def test_remove_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_node_attrs(4, {'a': 2})
        rule.remove_node_attrs(4, {'a': 1})
        assert(rule.p.node['d'] == {'a': set()})
        assert(rule.rhs.node['s'] == {'a': set([2])})
        return

    def test_update_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.update_node_attrs(4, {'b': 2})
        assert(rule.p.node['d'] is None)
        assert(rule.rhs.node['s'] == {'b': {2}})
        return

    def test_add_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_edge_attrs(4, 1, {'amazing': True})
        assert_graph_eq(rule.p, self.p)
        assert(rule.rhs.edge['s']['x'] == {'amazing': {True}})
        return

    def test_remove_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_edge_attrs(2, 3, {'a': set()})
        assert(rule.p.edge['b']['c'] == {'a': {1}})
        assert(rule.rhs.edge['y']['z'] == {'a': {1}})
        rule.remove_edge_attrs(2, 3, {'a': {1}})
        assert(rule.p.edge['b']['c'] == {'a': set()})
        assert(rule.rhs.edge['y']['z'] == {'a': set()})
        return

    def test_update_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.update_edge_attrs(2, 3, {'b': 1})
        assert(rule.p.edge['b']['c'] is None)
        assert(rule.rhs.edge['y']['z'] == {'b': {1}})
        return

    def merge_node_list(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.merge_node_list([2, 3], 'wow_name')
        assert(rule.lhs == self.pattern)
        assert(rule.p == self.p)
        assert('wow_name' in rule.rhs.nodes())
        assert(('wow_name', 'wow_name') in rule.rhs.edges())
        assert(('wow_name', 'y') in rule.rhs.edges())

    def test_all(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.clone_node(2)
        rule.remove_node(1)
        # print(rule)

    def test_from_script(self):
        commands = "clone 2 as 21.\nadd_node 'a' {'a': 1}.\ndelete_node 3."
        rule = Rule.from_transform(self.pattern, commands=commands)
        assert('a' in rule.rhs.nodes())
        assert('21' in rule.rhs.nodes())
        assert(3 not in rule.rhs.nodes())