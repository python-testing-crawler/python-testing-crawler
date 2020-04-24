# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .constants import HTML_CONTENT_TYPES


def acceptable_content_type(content_type: str) -> bool:
    return content_type.split(';')[0] in HTML_CONTENT_TYPES


def underlined(text: str) -> str:
    return text + "\n" + "-" * len(text)
