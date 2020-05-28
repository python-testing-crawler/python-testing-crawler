# Python Testing Crawler   :snake: :stethoscope: :spider:
[![PyPI version](https://badge.fury.io/py/python-testing-crawler.svg)](https://badge.fury.io/py/python-testing-crawler)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/python-testing-crawler.svg)](https://pypi.python.org/pypi/python-testing-crawler/)
[![GitHub license](https://img.shields.io/github/license/python-testing-crawler/python-testing-crawler)](https://github.com/python-testing-crawler/python-testing-crawler/blob/master/LICENSE.txt)
[![GitHub Actions (Tests)](https://github.com/python-testing-crawler/python-testing-crawler/workflows/Tests/badge.svg)](https://github.com/python-testing-crawler/python-testing-crawler)

_A crawler for automated functional testing of a web application_

Crawling a server-side-rendered web application is a _low cost_ way to get _low quality_ test coverage of your JavaScript-light web application.

If you have only partial test coverage of your routes, but still want to protect against silly mistakes, then this is for you. 

Features:

* Selectively spider pages and resources, or just request them
* Submit forms, and control what values to send
* Ignore links by source using CSS selectors
* Fail fast or collect many errors
* Configurable using straightforward rules

Works with the test clients for [Flask](https://flask.palletsprojects.com/en/1.1.x/testing/) (inc [Flask-WebTest](https://flask-webtest.readthedocs.io/en/latest/)), [Django](https://docs.djangoproject.com/en/3.0/topics/testing/tools/) and [WebTest](https://docs.pylonsproject.org/projects/webtest/en/latest/).

## Why should I use this?

Here's an example: [_Flaskr_](https://flask.palletsprojects.com/en/1.1.x/tutorial/), the Flask tutorial application has [166 lines of test code](https://github.com/pallets/flask/tree/master/examples/tutorial/tests) to achieve 100% test coverage.

[Using Python Testing Crawler](https://github.com/python-testing-crawler/flaskr/blob/master/tests/test_crawl.py) in a similar way to the Usage example below, we can hit 73% with very little effort. Disclaimer: Of course! It's not the same quality or utility of testing! But it is better than no tests, a complement to hand-written unit or functional tests and a useful stopgap.

## Installation

```
$ pip install python-testing-crawler
```

## Usage

Create a crawler using your framework's existing test client, tell it where to start and what rules to obey, then set it off:

```python
from python_testing_crawler import Crawler
from python_testing_crawler import Rule, Request, Ignore, Allow

def test_crawl_all():
    client = ## ... existing testing client
    ## ... any setup ...
    crawler = Crawler(
        client=my_testing_client,
        initial_paths=['/'],
        rules=[
            Rule("a", '/.*', "GET", Request()),
        ]
    )
    crawler.crawl()
```

This will crawl all anchor links to relative addresses beginning "/". Any exceptions encountered will be collected and presented at the end of the crawl. For **more power** see the Rules section below.

If you need to authorise the client's session, e.g. login, then you should that before creating the Crawler.

It is also a good idea to create enough data, via fixtures or otherwise, to expose enough endpoints.

### How do I setup a test client?

It depends on your framework:

* Flask: https://flask.palletsprojects.com/en/1.1.x/testing/
* Django: https://docs.djangoproject.com/en/3.0/topics/testing/tools/

## Crawler Options

| Param | Description |
| --- | --- |
| `initial_paths` |  list of paths/URLs to start from
| `rules` | list of Rules to control the crawler; see below
| `path_attrs` | list of attribute names to extract paths/URLs from; defaults to "href" -- include "src" if you want to check e.g. `<link>`, `<script>` or even `<img>`
| `ignore_css_selectors` | any elements matching this list of CSS selectors will be ignored when extracting links
| `ignore_form_fields` | list of form input names to ignore when determining the identity/uniqueness of a form. Include CSRF token field names here.
| `max_requests` | Crawler will raise an exception if this limit is exceeded
| `capture_exceptions` | upon encountering an exception, keep going and fail at the end of the crawl instead of during (default `True`)
| `output_summary` | print summary statistics and any captured exceptions and tracebacks at the end of the crawl (default `True`)
| `should_process_handlers` | list of "should process" handlers; see Handlers section
| `check_response_handlers` | list of "check response" handlers; see Handlers section

## Rules

The crawler has to be told what URLs to follow, what forms to post and what to ignore, using Rules.

Rules are made of four parameters:

```Rule(<source element regex>, <target URL/path regex>, <HTTP method>, <action to take>)```

These are matched against every HTML element that the crawler encounters, with the last matching rule winning.

Actions must be one of the following objects:

1. `Request(only=False, params=None)` -- follow a link or submit a form
    - `only=True` will retrieve a page/resource but _not_ spider its links.
    -  the dict `params` allows you to specify _overrides_ for a form's default values
1. `Ignore()` -- do nothing / skip
1. `Allow(status_codes)` -- allow a HTTP status in the supplied list, i.e. do not consider it an error.


### Example Rules

#### Follow all local/relative links

```python
HYPERLINKS_ONLY_RULE_SET = [
    Rule('a', '/.*', 'GET', Request()),
    Rule('area', '/.*', 'GET', Request()),
]
```

#### Request but do not spider all links

```python
REQUEST_ONLY_EXTERNAL_RULE_SET = [
    Rule('a', '.*', 'GET', Request(only=True)),
    Rule('area', '.*', 'GET', Request(only=True)),
]
```

This is useful for finding broken links.  You can also check `<link>` tags from the `<head>` if you include the following rule _plus_ set the Crawler's `path_attrs` to `("HREF", "SRC")`.

```Rule('link', '.*', 'GET', Request())```

#### Submit forms with GET or POST

```python
SUBMIT_GET_FORMS_RULE_SET = [
    Rule('form', '.*', 'GET', Request())
]

SUBMIT_POST_FORMS_RULE_SET = [
    Rule('form', '.*', 'POST', Request())
]
```

Forms are submitted with their default values, unless overridden using `Request(params={...})` for a specific form target or excluded using (globally) using the `ignore_form_fields` parameter to `Crawler` (necessary for e.g. CSRF token fields).

#### Allow some routes to fail

```python
PERMISSIVE_RULE_SET = [
    Rule('.*', '.*', 'GET', Allow([*range(400, 600)])),
    Rule('.*', '.*', 'POST', Allow([*range(400, 600)]))
]
```

If any HTTP error (400-599) is encountered for any request, allow it; do not error.

## Crawl Graph

The crawler builds up a graph of your web application. It can be interrogated via `crawler.graph` when the crawl is finished.

See [the graph module](python_testing_crawler/graph.py) for the defintion of `Node` objects.

## Handlers

Two hooks points are provided. These operate on `Node` objects (see above).

### Whether to process a Node

Using `should_process_handlers`, you can register functions that take a `Node` and return a `bool` of whether the Crawler should "process" -- follow a link or submit a form -- or not.

### Whether a response is acceptable

Using `check_response_handlers`, you can register functions that take a `Node` and response object (specific to your test client) and return a bool of whether the response should constitute an error.

If your function returns `True`, the Crawler with throw an exception.

## Examples

There are currently Flask and Django examples in [the tests](tests/).

See https://github.com/python-testing-crawler/flaskr for an example of integrating into an existing application, using Flaskr, the Flask tutorial application.

