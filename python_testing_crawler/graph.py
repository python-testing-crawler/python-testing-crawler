# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from typing import Optional, Tuple, List, Set
from dataclasses import dataclass, field
from collections import defaultdict

from .constants import GET


@dataclass
class Node:
    path: str
    method: str = GET
    params: dict = field(default_factory=dict)
    source: Optional[str] = None
    requested: bool = False
    status_code: Optional[int] = None
    ignore_form_fields: set = field(default_factory=set)

    def __post_init__(self):
        # force method to uppercase
        self.method = self.method.upper()

    @property
    def id(self) -> Tuple:
        return (
            self.method,
            self.path,
            *(
                val for (field, val) in self.params.items()
                if field not in self.ignore_form_fields
            )
        )


class DirectedGraph:

    def __init__(self):
        self.map = {}
        self.adj = defaultdict(lambda: [])

    @property
    def encountered_paths(self) -> Set[str]:
        return set(node.path for node in self.map.values())

    @property
    def visited_paths(self) -> Set[str]:
        return set(node.path for node in self.map.values() if node.requested)

    def add_node(self, node: Node):
        self.map[node.id] = node
        self.adj[node.id] = []

    def add_edge(self, from_node: Node, to_node: Node):
        self.adj[from_node.id].append(to_node)

    def get_node_by_id(self, id: tuple) -> Node:
        return self.map.get(id)

    def get_nodes_by_path(self, path: str) -> List[Node]:
        return [node for node in self.map.values() if node.path == path]

    def get_nodes_by_path_pattern(self, pattern: str) -> List[Node]:
        return [node for node in self.map.values() if re.match(pattern, node.path or "")]

    def get_nodes_by_source(self, source: str) -> List[Node]:
        return [node for node in self.map.values() if node.source == source]

    def get_nodes_by_source_pattern(self, source_pattern: str) -> List[Node]:
        return [node for node in self.map.values() if re.match(source_pattern, node.source or "")]
