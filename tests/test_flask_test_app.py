
import pytest
import webtest
import flask

from tests.webapps.flask.app import create_app, lookup_requests

from python_testing_crawler import Crawler, Rule, Request, Ignore, Allow
from python_testing_crawler.exn import HttpStatusError, UnexpectedResponseError
from python_testing_crawler.constants import GET, POST
from python_testing_crawler.constants import ANCHOR, FORM
from python_testing_crawler.constants import HREF, SRC
from .example_rules import (
    PERMISSIVE_ALL_ELEMENTS_RULE_SET,
    PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
    REQUEST_EXTERNAL_RESOURCE_LINKS_RULE_SET,
    SUBMIT_GET_FORMS_RULE_SET,
    SUBMIT_POST_FORMS_RULE_SET,
)


# client factories

class FlaskTestClientFactory:

    def __init__(self, flask_app):
        self.flask_app = flask_app

    def get_client(self):
        return self.flask_app.test_client()


class WebTestClientFactory:

    def __init__(self, flask_app):
        self.flask_app = flask_app

    def get_client(self):
        return webtest.TestApp(self.flask_app)


# utils

def get_response_content(response):
    if isinstance(response, flask.wrappers.Response):
        return response.data.decode(response.charset)
    elif isinstance(response, webtest.response.TestResponse):
        return response.unicode_body
    else:
        raise TypeError(type(response))


# fixtures

@pytest.fixture
def app():
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture(params=[FlaskTestClientFactory, WebTestClientFactory])
def client(request, app):  # request = fixture request
    factory_cls = request.param
    client = factory_cls(app).get_client()
    return client


DIRECTLY_ACCESSIBLE_URLS = {
    '/',
    '/abort/with/400',
    '/abort/with/500',
    '/page-a',
    '/page-b',
    '/page-c',
    '/page-c?query=foo',
    '/page-d',
    '/page-gallery',
    '/image-map-target',
    '/redirect/with/301',
    '/redirect/with/302',
    '/redirect-target',
}


def test_crawl_all(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
    )
    crawler.crawl()

    # check everything visited
    assert crawler.graph.visited_paths == DIRECTLY_ACCESSIBLE_URLS

    # check status codes recorded
    expected_status_codes = {path: 200 for path in DIRECTLY_ACCESSIBLE_URLS}
    expected_status_codes['/redirect/with/301'] = 301
    expected_status_codes['/redirect/with/302'] = 302
    expected_status_codes['/abort/with/400'] = 400
    expected_status_codes['/abort/with/500'] = 500
    for path, status_code in expected_status_codes.items():
        assert crawler.graph.get_nodes_by_path(path)[0].status_code == status_code


def test_inclusion(app, client):
    wanted_urls = {'/', '/page-a'}
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=[
            Rule(ANCHOR, '^/$', GET, Request()),
            Rule(ANCHOR, '^/page-a$', GET, Request())
        ]
    )
    crawler.crawl()
    assert crawler.graph.visited_paths == wanted_urls


def test_exclusion(app, client):
    unwanted_urls = {'/page-d'}
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET + [
            Rule(ANCHOR, '^/page-d$', GET, Ignore())
        ]
    )
    crawler.crawl()
    assert crawler.graph.visited_paths == DIRECTLY_ACCESSIBLE_URLS - unwanted_urls


def test_ignore_anchor_by_id(app, client):
    unwanted_urls = {'/page-d'}
    selectors_to_ignore = ['a#menu-link-page-d-id']
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
        ignore_css_selectors=selectors_to_ignore
    )
    crawler.crawl()
    assert crawler.graph.visited_paths == DIRECTLY_ACCESSIBLE_URLS - unwanted_urls


def test_ignore_anchor_by_class(app, client):
    unwanted_urls = {'/page-d'}
    selectors_to_ignore = ['a.menu-link-page-d-class']
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
        ignore_css_selectors=selectors_to_ignore
    )
    crawler.crawl()
    assert crawler.graph.visited_paths == DIRECTLY_ACCESSIBLE_URLS - unwanted_urls


def test_should_process_handlers(app, client):
    unwanted_urls = {'/page-d'}

    def should_not_proess_page_d(node):
        return node.path != '/page-d'

    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
        should_process_handlers=[should_not_proess_page_d]
    )
    crawler.crawl()
    assert crawler.graph.visited_paths == DIRECTLY_ACCESSIBLE_URLS - unwanted_urls


def test_submit_forms_by_get(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET + SUBMIT_GET_FORMS_RULE_SET,
    )
    crawler.crawl()

    # check we found and submitted the form
    submitted_forms = [form for form in crawler.graph.get_nodes_by_source(FORM) if form.requested]
    assert len(submitted_forms) == 1
    form = submitted_forms[0]
    submissions = [
        entry for entry
        in lookup_requests(app, path=form.path, method=form.method)
        if entry.params
    ]
    assert len(submissions) == 1

    # check we visited the onward link
    assert '/form-submitted-by-get-onward-link' in crawler.graph.visited_paths


def test_submit_forms_by_post(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET + SUBMIT_POST_FORMS_RULE_SET,
    )
    crawler.crawl()

    # check we found and submitted the form
    submitted_forms = [form for form in crawler.graph.get_nodes_by_source(FORM) if form.requested]
    assert len(submitted_forms) == 1
    form = submitted_forms[0]
    submissions = [
        entry for entry
        in lookup_requests(app, path=form.path, method=form.method)
        if entry.params
    ]
    assert len(submissions) == 1

    # check we visited the onward link
    assert '/form-submitted-by-post-onward-link' in crawler.graph.visited_paths


def test_submit_forms_with_extra_data(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=(
            PERMISSIVE_HYPERLINKS_ONLY_RULE_SET
            + SUBMIT_POST_FORMS_RULE_SET
            + [
                Rule(FORM, ".*", GET, Request(params={'extra': 'extra'})),
                Rule(FORM, ".*", POST, Request(params={'extra': 'extra'})),
            ]
        )
    )
    crawler.crawl()

    # check we always submitted extra data when we submitted any
    submitted_forms = [form for form in crawler.graph.get_nodes_by_source(FORM) if form.requested]
    assert len(submitted_forms) > 1
    for form in submitted_forms:
        entries = lookup_requests(app, form.path, method=form.method)
        for entry in entries:
            if entry.params:
                assert 'extra' in {key for key, val in entry.params}


def test_ignore_form_by_id(app, client):
    selectors_to_ignore = ['form#form-get-id']
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET + SUBMIT_GET_FORMS_RULE_SET,
        ignore_css_selectors=selectors_to_ignore
    )
    crawler.crawl()
    submitted_forms = [form for form in crawler.graph.get_nodes_by_source(FORM) if form.requested]
    assert len(submitted_forms) == 0


def test_ignore_form_by_class(app, client):
    selectors_to_ignore = ['form.form-get-class']
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET + SUBMIT_GET_FORMS_RULE_SET,
        ignore_css_selectors=selectors_to_ignore
    )
    crawler.crawl()
    submitted_forms = [form for form in crawler.graph.get_nodes_by_source(FORM) if form.requested]
    assert len(submitted_forms) == 0


def test_ignore_form_by_name(app, client):
    selectors_to_ignore = ['form[name=form-get-name]']
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET + SUBMIT_GET_FORMS_RULE_SET,
        ignore_css_selectors=selectors_to_ignore
    )
    crawler.crawl()
    submitted_forms = [form for form in crawler.graph.get_nodes_by_source(FORM) if form.requested]
    assert len(submitted_forms) == 0


def test_extract_link_hrefs(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET + \
            REQUEST_EXTERNAL_RESOURCE_LINKS_RULE_SET
    )
    crawler.crawl()
    link_nodes = crawler.graph.get_nodes_by_source("link")
    assert len(link_nodes) == 1
    assert link_nodes[0].path == '/style.css'
    assert link_nodes[0].status_code == 200


def test_extract_srcs(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_ALL_ELEMENTS_RULE_SET,
        path_attrs=(HREF, SRC)
    )
    crawler.crawl()
    img_nodes = crawler.graph.get_nodes_by_source("img")
    assert len(img_nodes) == 1
    assert img_nodes[0].path == '/image.png'
    assert img_nodes[0].status_code == 200


def test_40x_raising_exception(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        capture_exceptions=False,
        rules=[
            Rule(ANCHOR, ".*", GET, Request()),
            Rule(ANCHOR, ".*", GET, Allow([500]))
        ]
    )
    with pytest.raises(HttpStatusError) as excinfo:
        crawler.crawl()
    assert excinfo.value.status_code == 400


def test_40x_trapped_but_allowed(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=[
            Rule(ANCHOR, ".*", GET, Request()),
            Rule(ANCHOR, ".*", GET, Allow([400, 500])),
        ]
    )
    crawler.crawl()


def test_50x_raising_exception(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        capture_exceptions=False,
        rules=[
            Rule(ANCHOR, ".*", GET, Request()),
            Rule(ANCHOR, ".*", GET, Allow([400]))
        ]
    )
    with pytest.raises(HttpStatusError) as excinfo:
        crawler.crawl()
    assert excinfo.value.status_code == 500


def test_50x_trapped_but_allowed(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=[
            Rule(ANCHOR, ".*", GET, Request()),
            Rule(ANCHOR, ".*", GET, Allow([400, 500])),
        ]
    )
    crawler.crawl()


def test_capture_exceptions(app, client, capfd):
    failure_paths = {'/page-c', '/page-d'}
    app.config['FAILURE_PATHS'] = failure_paths
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
        capture_exceptions=True
    )
    with pytest.raises(AssertionError):
        crawler.crawl()
    out, err = capfd.readouterr()
    for path in failure_paths:
        assert f"Exception: Instructed to fail at {path}" in out


def test_check_response_handler_positive_case(app, client):
    def only_page_a_recommends(node, response):
        return (
            'recommend' in get_response_content(response)
            or node.path != '/page-a'
        )
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
        check_response_handlers=[only_page_a_recommends]
    )
    crawler.crawl()


def test_check_response_handler_negative_case(app, client):
    def insist_on_cheshire_cat(node, response):
        return "grin" in get_response_content(response)
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=PERMISSIVE_HYPERLINKS_ONLY_RULE_SET,
        capture_exceptions=False,
        check_response_handlers=[insist_on_cheshire_cat]
    )
    with pytest.raises(UnexpectedResponseError):
        crawler.crawl()
