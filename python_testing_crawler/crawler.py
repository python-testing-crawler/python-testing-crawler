# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import Optional, Iterable, List, Callable
from copy import copy
from queue import Queue
from urllib.parse import urlparse
from itertools import chain
import traceback
import logging

import soupsieve

from .rules import Rule, Request, Ignore, Allow
from .graph import DirectedGraph, Node
from .clients import detect_and_wrap_client
from .exn import HttpStatusError, TooManyRequestsError, UnexpectedResponseError
from .utils import underlined
from .constants import HREF
from .constants import GET, POST
from .constants import USABLE_SCHEMES


LOGGER_NAME = 'python-testing-crawler'
logging.getLogger(LOGGER_NAME).addHandler(logging.NullHandler())


class Crawler:

    def __init__(
        self,
        client,
        *,
        initial_paths: Iterable[str] = None,
        rules: Iterable[Rule] = None,
        path_attrs: Iterable[str] = (HREF,),
        ignore_css_selectors: Iterable = None,
        ignore_form_fields: Iterable[str] = None,
        max_requests: Optional[int] = None,
        capture_exceptions: bool = True,
        output_summary: bool = True,
        should_process_handlers: Iterable[Callable] = None,
        check_response_handlers: Iterable[Callable] = None,
    ):
        # params
        self._client = client
        self.initial_paths = list(initial_paths or [])
        self.rules = list(rules or [])
        self.path_attrs = tuple(path_attrs)
        self.ignore_css_selectors = list(ignore_css_selectors or [])
        self.ignore_form_fields = list(ignore_form_fields or [])
        self.max_requests = max_requests
        self.capture_exceptions = capture_exceptions
        self.output_summary = output_summary

        # data structures
        self.queue: Queue = Queue()
        self.graph = DirectedGraph()
        self.tracebacks: List = []

        # handler lists
        self.should_process_handlers = list(should_process_handlers or [])
        self.check_response_handlers = list(check_response_handlers or [])

        # check css selectors
        for selector in self.ignore_css_selectors:
            try:
                soupsieve.compile(selector)
            except soupsieve.SelectorSyntaxError as e:
                msg = f"Invalid CSS selector '{selector}' (see parent exception)"
                raise ValueError(msg) from e

        # detect client and construct wrapper
        self.client = detect_and_wrap_client(self._client, ignore_css_selectors)

        # get logger
        self.logger = logging.getLogger(LOGGER_NAME)

    def crawl(self):
        # check initial paths
        if not self.initial_paths:
            raise ValueError("Need some initial paths")

        # check rules
        if not self.rules:
            raise ValueError("Need some rules!")

        # add initial entries
        self.logger.info("Starting crawl...")
        self.logger.info(f"Initial paths: {self.initial_paths}")
        for path in self.initial_paths:
            node = Node(path=path, source=None)
            self.graph.add_node(node)
            self.queue.put(node)

        # main loop
        count = 0
        while not self.queue.empty():
            next_node = self.queue.get()
            self.process_node(next_node)
            count += 1

            if count == self.max_requests:
                raise TooManyRequestsError(count)

        # handle any captured tracebacks
        if self.output_summary:
            print(underlined("Results of Testing Crawler") + "\n")
            print(f"Encountered {len(self.graph.encountered_paths)} endpoints.")
            print(f"Visited {len(self.graph.visited_paths)} endpoints.\n")
            if self.tracebacks:
                print(underlined(f"Summary of {len(self.tracebacks)} error(s)"))
                for (node, exc, tb) in self.tracebacks:
                    print()
                    self.print_exception_request(exc, node)
                print("\n" + underlined("Full tracebacks") + "\n")
                for (node, exc, tb) in self.tracebacks:
                    self.print_exception_request(exc, node)
                    print(''.join(tb.format()) + "\n")

        # finally fail if captured tracebacks
        if self.tracebacks:
            assert False, f"Encountered {len(self.tracebacks)} exception(s) whilst crawling"

    def should_process(self, node):
        # follow only http schemes
        scheme = urlparse(node.path).scheme
        if scheme and scheme not in USABLE_SCHEMES:
            self.logger.info(f"Invalid scheme '{scheme} prevented processing of {node}")
            return False

        # find matching rule
        final_matching_rule = None
        for rule in self.rules:
            if isinstance(rule.action, (Request, Ignore)) and rule.match(node):
                final_matching_rule = rule
        if not final_matching_rule:
            self.logger.info(f"Lack of matching Rule prevented processing of {node}")
            return False
        if not isinstance(final_matching_rule.action, Request):
            self.logger.info(f"{final_matching_rule} prevented processing of {node}")
            return False

        # try registered handlers
        for fn in self.should_process_handlers:
            if not fn(node):
                self.logger.info(f"Handler {fn} prevented processing of {node}")
                return

        # ok
        return True

    def should_extract(self, node):
        final_matching_rule = None
        for rule in self.rules:
            if isinstance(rule.action, Request) and rule.match(node):
                final_matching_rule = rule
        if final_matching_rule and final_matching_rule.action.only:
            self.logger.info(f"{final_matching_rule} prevented extraction from {node}")
            return False
        return True

    def process_node(self, node):
        self.logger.info(f"Processing {node} ...")

        # determine if should proceed
        if not self.should_process(node):
            return

        # record requested
        node.requested = True

        # make request and check the response
        try:
            response = self.make_request(node)
            self.check_response(node, response)
        except (Exception if self.capture_exceptions else ()) as e:
            tb = traceback.TracebackException.from_exception(e)
            self.tracebacks.append((node, e, tb))
            return
        except Exception as e:
            self.print_exception_request(e, node)
            raise e

        # bail if response not valid for extraction
        if not self.client.is_valid_for_extraction(response):
            self.logger.info(f"Response was not valid for extraction for {node}")
            return

        # bail if don't want to extract
        if not self.should_extract(node):
            return

        # extract onwards links and forms
        self.logger.info(f"Extracting from {node}")
        link_nodes = self.client.extract(response, None, self.path_attrs)
        form_nodes = [*self.client.extract_forms(
            node.path, response, ignore_form_fields=self.ignore_form_fields
        )]

        # walk potentially new nodes
        for potential_new_node in chain(link_nodes, form_nodes):
            existing_child_node = self.graph.get_node_by_id(potential_new_node.id)
            already_encountered = bool(existing_child_node)
            child_node = existing_child_node or potential_new_node

            if not already_encountered:
                self.graph.add_node(child_node)
                self.queue.put(child_node)

            # record link to graph
            self.graph.add_edge(node, child_node)

    def make_request(self, node):
        # decide client method
        if node.method == GET:
            fn = self.client.get
        elif node.method == POST:
            fn = self.client.post
        else:
            raise ValueError(f"Unsupported method: {node.method}")

        # determine additional input fields
        params = copy(node.params)
        for rule in self.rules:
            if isinstance(rule.action, Request) and rule.match(node):
                params.update(rule.action.params)

        # make request
        self.logger.info(
            f"Requesting: {node.method} {node.path}"
            + (f" with {params}" if params else "")
        )
        return fn(node.path, params)

    def status_code_ok(self, node):
        if node.status_code is None:
            raise ValueError("No status code")

        # accept 20x and 30x series
        if node.status_code // 100 in {2, 3}:
            return True

        # check allowances
        allowances = (
            rule for rule in self.rules
            if isinstance(rule.action, Allow)
        )
        for allowance in allowances:
            match = allowance.match(node)
            if match and node.status_code in allowance.action.status_codes:
                self.logger.info(f"{allowance} allowed HTTP {node.status_code} for {node}")
                return True

        # decide if failure
        return False

    def check_response(self, node, response):
        # fail selected HTTP status codes
        node.status_code = response.status_code
        status_code_is_failure = not self.status_code_ok(node)
        if status_code_is_failure:
            raise HttpStatusError(response.status_code)

        # try registered handlers
        for fn in self.check_response_handlers:
            if not fn(node, response):
                raise UnexpectedResponseError(node, response, fn)

    @classmethod
    def print_exception_request(cls, exc, node: Node):
        print(f"{node.method} {node.path}")
        if node.params:
            print(f"Params: {node.params}")
        print(f"=> {repr(exc)}")
