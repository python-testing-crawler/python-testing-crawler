# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass, field
from typing import Dict, List
import re


class Action:
    pass


class Ignore(Action):
    pass


@dataclass
class Request(Action):
    only: bool = False
    params: Dict[str, str] = field(default_factory=dict)


@dataclass
class Allow(Action):
    status_codes: List[int] = field(default_factory=list)


@dataclass
class Rule:
    source_pattern: str
    path_pattern: str
    method: str
    action: Action

    def match(self, node):
        return all((
            (node.source is None or re.match(self.source_pattern, node.source)),
            self.method == node.method,
            re.match(self.path_pattern, node.path)
        ))
