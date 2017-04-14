"""Docs here."""
import copy
import warnings

from regraph.parser import parser
from regraph.utils import (keys_by_value,
                           make_canonical_commands)
from regraph.category_op import (identity,
                                 check_homomorphism,
                                 pullback_complement,
                                 pushout)
from regraph import primitives
from regraph.exceptions import (ReGraphWarning, ParsingError, RuleError,
                                GraphError)


class Rule(object):
    """
    Class implements a rewriting rule.

    A rewriting rule consists of the three graphs:
    `p` - preserved part, `lhs` - left hand side,
    `rhs` - right hand side, and two mappings
    p -> lhs, p -> rhs. The rule can be type preserving or not,
    which is set by the attribute `ignore_types`
    """

    def __init__(self, p, lhs, rhs, p_lhs=None, p_rhs=None):
        """Initialize a rule by p, lhs and rhs and two homomorphisms:
        p -> lhs & p -> rhs. By default the homomorphisms are None, and
        they are created as Homomorphism.identity(p, lhs) etc with the
        correspondance according to the node names."""
        if not p_lhs:
            self.p_lhs = identity(p, lhs)
        else:
            check_homomorphism(p, lhs, p_lhs)
            self.p_lhs = copy.deepcopy(p_lhs)

        if not p_rhs:
            self.p_rhs = identity(p, rhs)
        else:
            check_homomorphism(p, rhs, p_rhs)
            self.p_rhs = copy.deepcopy(p_rhs)

        self.p = copy.deepcopy(p)
        self.lhs = copy.deepcopy(lhs)
        self.rhs = copy.deepcopy(rhs)

        return

    @classmethod
    def from_transform(cls, pattern, commands=None):
        """Initialize a rule from the transformation.

        On input takes a pattern which is used as LHS of the rule,
        as an optional argument transformation commands can be provided,
        by default the list of commands is empty and all P, LHS and RHS
        are initialized to be the same graph (pattern), later on
        when transformations are applied P and RHS are being updated.
        If list of commands is specified, these commands are simplified,
        transformed to the canonical order, and applied to P, LHS & RHS.
        """
        p = copy.deepcopy(pattern)
        lhs = copy.deepcopy(pattern)
        rhs = copy.deepcopy(pattern)
        p_lhs = dict([(n, n) for n in pattern.nodes()])
        p_rhs = dict([(n, n) for n in pattern.nodes()])

        rule = cls(p, lhs, rhs, p_lhs, p_rhs)

        # if the commands are provided, perform respecitive transformations
        if commands:
            # 1. make the commands canonical
            commands = make_canonical_commands(p, commands, p.is_directed())
            # 2. apply the commands

            command_strings = [
                c for block in commands if len(block) > 0 for c in block.splitlines()
            ]

            actions = []
            for command in command_strings:
                try:
                    parsed = parser.parseString(command).asDict()
                    actions.append(parsed)
                except:
                    raise ParsingError("Cannot parse command '%s'" % command)

            for action in actions:
                if action["keyword"] == "clone":
                    node_name = None
                    if "node_name" in action.keys():
                        node_name = action["node_name"]
                    rule.clone_node(action["node"], node_name)
                elif action["keyword"] == "merge":
                    node_name = None
                    if "node_name" in action.keys():
                        node_name = action["node_name"]
                    merged_node = rule.merge_nodes(
                        action["nodes"],
                        node_name)
                elif action["keyword"] == "add_node":
                    name = None
                    attrs = {}
                    if "node" in action.keys():
                        name = action["node"]
                    if "attributes" in action.keys():
                        attrs = action["attributes"]
                    rule.add_node(name, attrs)
                elif action["keyword"] == "delete_node":
                    rule.remove_node(action["node"])
                elif action["keyword"] == "add_edge":
                    attrs = {}
                    if "attributes" in action.keys():
                        attrs = action["attributes"]
                    rule.add_edge(
                        action["node_1"],
                        action["node_2"],
                        attrs)
                elif action["keyword"] == "delete_edge":
                    rule.remove_edge(
                        action["node_1"],
                        action["node_2"])
                elif action["keyword"] == "add_node_attrs":
                    rule.add_node_attrs(
                        action["node"],
                        action["attributes"])
                elif action["keyword"] == "add_edge_attrs":
                    rule.add_edge_attrs(
                        action["node_1"],
                        action["node_2"],
                        action["attributes"])
                elif action["keyword"] == "delete_node_attrs":
                    rule.remove_node_attrs(
                        action["node"],
                        action["attributes"])
                elif action["keyword"] == "delete_edge_attrs":
                    rule.remove_edge_attrs(
                        action["node_1"],
                        action["node_2"],
                        action["attributes"])
                else:
                    raise ParsingError("Unknown command %s" % action["keyword"])
        return rule

    def __eq__(self, rule):
        return (
            primitives.equal(self.p, rule.p) and
            primitives.equal(self.lhs, rule.lhs) and
            primitives.equal(self.rhs, rule.rhs) and
            self.p_lhs == rule.p_lhs and
            self.p_rhs == rule.p_rhs
        )

    def __str__(self):
        return "Preserved part\n%s\n%s\n" % (self.p.node, self.p.edges()) +\
               "Left hand side\n%s\n%s\n" % (self.lhs.node, self.lhs.edges()) +\
               "P->L Homomorphism : %s\n" % self.p_lhs +\
               "Right hand side\n%s\n%s\n" % (self.rhs.node, self.rhs.edges()) +\
               "P->R Homomorphism : %s\n" % self.p_rhs

    def __doc__(self):
        return(
            "An instance of rule is an instance of `p` (preserved part), " +\
            "`lhs` (lef-hand side of the rule) and `rhs` (right-hand side) graphs " +\
            "together with two mappings p -> lhs & p -> rhs."
        )

    def add_node(self, node_id, attrs=None):
        """Add node to the graph."""
        if node_id not in self.rhs.nodes():
            p_keys = keys_by_value(self.p_rhs, node_id)
            # here we check for the nodes with the same name in the lhs
            for k in p_keys:
                lhs_key = self.p_lhs[k]
                if lhs_key == node_id:
                    raise RuleError(
                        "Node with the id '%s' already exists in the left hand side of the rule" %
                        node_id
                    )
            primitives.add_node(self.rhs, node_id, attrs)
        else:
            raise RuleError(
                "Node with the id '%s' already exists in the right hand side of the rule" %
                node_id
            )

    def remove_node_rhs(self, n):
        p_keys = keys_by_value(self.p_rhs, n)
        for p_node in p_keys:
            primitives.remove_node(self.p, p_node)
            del self.p_rhs[p_node]
        primitives.remove_node(self.rhs, n)

    def remove_node(self, n):
        """Remove a node in the graph."""
        # remove corresponding nodes from p and rhs
        p_keys = keys_by_value(self.p_lhs, n)
        for k in p_keys:
            if k in self.p.nodes():
                primitives.remove_node(self.p, k)
            if self.p_rhs[k] in self.rhs.nodes():
                primitives.remove_node(self.rhs, self.p_rhs[k])
                affected_nodes = keys_by_value(self.p_rhs, self.p_rhs[k])
                for node in affected_nodes:
                    del self.p_rhs[node]
            del self.p_lhs[k]
        return

    def add_edge_rhs(self, n1, n2, attrs=None):
        primitives.add_edge(self.rhs, n1, n2, attrs)

    def add_edge(self, n1, n2, attrs=None):
        """Add an edge in the graph."""
        # Find nodes in p mapping to n1 & n2
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise RuleError(
                    "Node with the id '%s' does not exist in the preserved part of the rule" % k2
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise RuleError(
                        "Node with the id '%s' does not exist in the preserved part of the rule" % k2
                    )
                rhs_key_1 = self.p_rhs[k1]
                rhs_key_2 = self.p_rhs[k2]
                if self.rhs.is_directed():
                    if (rhs_key_1, rhs_key_2) in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' already exists in the right hand side of the rule" % 
                            (rhs_key_1, rhs_key_2)
                        )
                    primitives.add_edge(self.rhs, rhs_key_1, rhs_key_2, attrs)
                else:
                    if (rhs_key_1, rhs_key_2) in self.rhs.edges() or\
                       (rhs_key_2, rhs_key_1) in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' already exists in the right hand side of the rule" % 
                            (rhs_key_1, rhs_key_2)
                        )
                    primitives.add_edge(self.rhs, rhs_key_1, rhs_key_2, attrs)
        return

    def remove_edge_rhs(self, node1, node2):
        """Remove edge from the rhs of the graph"""
        primitives.remove_edge(self.rhs, node1, node2)
        for pn1 in keys_by_value(self.p_rhs, node1):
            for pn2 in keys_by_value(self.p_rhs, node2):
                try:
                    primitives.remove_edge(self.p, pn1, pn2)
                except GraphError:
                    continue

    def remove_edge(self, n1, n2):
        """Remove edge from the graph."""
        # Find nodes in p mapping to n1 & n2
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        # Remove edge from the preserved part & rhs of the rule
        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise RuleError(
                    "Node with the id '%s' does not exist in the preserved part" % k1
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise RuleError(
                        "Node with the id '%s' does not exist in the preserved part" % k2
                    )
                rhs_key_1 = self.p_rhs[k1]
                rhs_key_2 = self.p_rhs[k2]
                if self.p.is_directed():
                    if (k1, k2) not in self.p.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the preserved part of the rule " %
                            (k1, k2)
                        )
                    if (rhs_key_1, rhs_key_2) not in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the right hand side of the rule " %
                            (rhs_key_1, rhs_key_2)
                        )
                    primitives.remove_edge(self.p, k1, k2)
                    primitives.remove_edge(self.rhs, rhs_key_1, rhs_key_2)
                else:
                    if (k1, k2) not in self.p.edges() and (k2, k1) not in self.p.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the preserved part of the rule " %
                            (k1, k2)
                        )
                    if (rhs_key_1, rhs_key_2) not in self.rhs.edges() and\
                       (rhs_key_2, rhs_key_1) not in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the right hand side of the rule " %
                            (rhs_key_1, rhs_key_2)
                        )
                    primitives.remove_edge(self.p, k1, k2)
        return

    def clone_rhs_node(self, node, new_name=None):
        """clone a rhs node"""
        if node not in self.rhs.nodes():
            raise RuleError(
                "Node '%s' is not a node of right hand side" %
                node
            )
        p_keys = keys_by_value(self.p_rhs, node)
        if len(p_keys) == 0:
            primitives.clone_node(self.rhs, node, new_name)
        elif len(p_keys) == 1:
            primitives.clone_node(self.rhs, node, new_name)
            new_p_node = primitives.clone_node(self.p, p_keys[0])
            self.p_rhs[new_p_node] = new_name
            self.p_lhs[new_p_node] = self.p_lhs[p_keys[0]]
        else:
            raise RuleError("Cannot clone node that is result of merge!")

    def clone_node(self, n, node_name=None):
        """Clone a node of the graph."""
        p_new_nodes = []
        rhs_new_nodes = []
        p_keys = keys_by_value(self.p_lhs, n)
        for k in p_keys:

            p_new_node = primitives.clone_node(self.p, k)
            p_new_nodes.append(p_new_node)
            rhs_new_node = primitives.clone_node(self.rhs, self.p_rhs[k])
            rhs_new_nodes.append(rhs_new_node)
            # self.p_lhs[k] = n
            self.p_lhs[p_new_node] = n
            self.p_rhs[p_new_node] = rhs_new_node
        return (p_new_nodes, rhs_new_nodes)

    def merge_nodes_rhs(self, n1, n2, new_name):
        if n1 not in self.rhs.nodes():
            raise RuleError("Node '%s' is not a node of the rhs" % n1)
        if n2 not in self.rhs.nodes():
            raise RuleError("Node '%s' is not a node of the rhs" % n2)
        primitives.merge_nodes(self.rhs, [n1, n2], node_name=new_name)
        for (source, target) in self.p_rhs.items():
            if target == n1 or target == n2:
                self.p_rhs[source] = new_name

    def merge_nodes(self, n1, n2, node_name=None):
        """Merge two nodes of the graph."""
        # Update graphs
        new_name = None
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        nodes_to_merge = set()
        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise RuleError(
                    "Node with the id '%s' does not exist in the preserved part of the rule" % k1
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise RuleError(
                        "Node with the id '%s' does not exist in the preserved part of the rule" % k2
                    )
                nodes_to_merge.add(self.p_rhs[k1])
                nodes_to_merge.add(self.p_rhs[k2])

        new_name = primitives.merge_nodes(
            self.rhs,
            list(nodes_to_merge),
            node_name=node_name
        )
        # Update mappings
        keys = p_keys_1 + p_keys_2
        for k in keys:
            self.p_rhs[k] = new_name
        return new_name

    def add_node_attrs_rhs(self, n, attrs):
        if n not in self.rhs.nodes():
            raise RuleError("Node %s does not exist in the right hand side of the rule" % n)
        primitives.add_node_attrs(self.rhs, n, attrs)

    def add_node_attrs(self, n, attrs):
        """Add node attributes to a node in the graph."""
        if n not in self.lhs.nodes():
            raise RuleError("Node '%s' does not exist in the left hand side of the rule" % n)
        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise RuleError("Node '%s' is being removed by the rule, cannot add attributes" % n)
        for k in p_keys:
            primitives.add_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def remove_node_attrs_rhs(self, n, attrs):
        if n not in self.rhs.nodes():
            raise RuleError("Node '%s' does not exist in the right hand side of the rule" % n)

        p_keys = keys_by_value(self.p_rhs, n)
        for p_node in p_keys:
            primitives.remove_node_attrs(self.p, p_node, attrs)
        primitives.remove_node_attrs(self.rhs, n, attrs)

    def remove_node_attrs(self, n, attrs):
        """Remove nodes attributes from a node in the graph."""
        if n not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n)

        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise RuleError(
                "Node '%s' is being removed by the rule, cannot remove attributes" % n)

        for k in p_keys:
            primitives.remove_node_attrs(self.p, k, attrs)
            primitives.remove_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def update_node_attrs(self, n, attrs):
        """Update attributes of a node."""
        if n not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n)

        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise RuleError(
                "Node '%s' is being removed by the rule, cannot update attributes" % n)
        for k in p_keys:
            self.p.node[k] = None
            primitives.update_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def add_edge_attrs(self, n1, n2, attrs):
        """Add attributes to an edge."""
        if n1 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n1
            )

        if n2 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n2
            )

        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )
            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    primitives.add_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        else:
            if (n1, n2) not in self.lhs.edges() and (n2, n1) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    primitives.add_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        return

    def remove_edge_attrs(self, n1, n2, attrs):
        """Remove edge attributes from an edge in the graph."""
        if n1 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n1
            )
        if n2 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n2
            )
        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    primitives.remove_edge_attrs(self.p, k1, k2, attrs)
                    primitives.remove_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        else:
            if (n1, n2) not in self.lhs.edges() and (n2, n1) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )
            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    primitives.remove_edge_attrs(
                        self.p,
                        k1,
                        k2,
                        attrs
                    )
                    primitives.remove_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        return

    def update_edge_attrs(self, n1, n2, attrs):
        """Update the attributes of an edge with a new set `attrs`."""
        if n1 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n1
            )
        if n2 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" % n2
            )
        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)

            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
                    n2
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
                    n1
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.p.edge[k1][k2] = None
                    primitives.update_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        else:
            if (n1, n2) not in self.lhs.edges() and (n2, n1) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.p.edge[k1][k2] = None
                    primitives.update_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        return

    def merge_node_list(self, node_list, node_name=None):
        """Merge a list of nodes."""
        if len(node_list) > 1:
            node_name = self.merge_nodes(
                node_list[0],
                node_list[1],
                node_name)
            for i in range(2, len(node_list)):
                node_name = self.merge_nodes(node_list[i], node_name, node_name)
        else:
            warnings.warn(
                "Cannot merge less than two nodes!", ReGraphWarning
            )

    def to_json(self):
        """Convert the rule to json repr."""
        json_data = {}
        json_data["lhs"] = primitives.graph_to_json(self.lhs)
        json_data["p"] = primitives.graph_to_json(self.p)
        json_data["rhs"] = primitives.graph_to_json(self.rhs)
        json_data["p_lhs"] = self.p_lhs
        json_data["p_rhs"] = self.p_rhs
        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create a rule obj from json repr."""
        lhs = primitives.graph_from_json(json_data["lhs"])
        p = primitives.graph_from_json(json_data["p"])
        rhs = primitives.graph_from_json(json_data["rhs"])
        p_lhs = json_data["p_lhs"]
        p_rhs = json_data["p_rhs"]
        rule = cls(p, lhs, rhs, p_lhs, p_rhs)
        return rule

    def apply_to(self, graph, instance):
        """Perform graph rewriting with returning new G'."""
        g_m, p_g_m, g_m_g = pullback_complement(
            self.p, self.lhs, graph, self.p_lhs, instance
        )
        g_prime, g_m_g_prime, rhs_g_prime = pushout(
            self.p, g_m, self.rhs, p_g_m, self.p_rhs, total=True
        )
        return g_prime
