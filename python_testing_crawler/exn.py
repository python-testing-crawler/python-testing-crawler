# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

class HttpStatusError(Exception):

    def __init__(self, status_code: int):
        self.status_code = status_code


class TooManyRequestsError(Exception):

    def __init__(self, count: int):
        self.count = count


class UnexpectedResponseError(Exception):

    def __init__(self, node, response, fn):
        self.node = node
        self.response = response
        self.fn = fn
