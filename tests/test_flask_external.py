
import pytest
import webtest

from tests.webapps.flask_external.app import create_app

from python_testing_crawler import Crawler
from python_testing_crawler.exn import TooManyRequestsError
from .example_rules import PERMISSIVE_HYPERLINKS_ONLY_RULE_SET, REQUEST_ONLY_EXTERNAL_RULE_SET


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


def test_request_external_without_processing(app, client):
    crawler = Crawler(
        client=client,
        initial_paths=['/'],
        rules=(
            REQUEST_ONLY_EXTERNAL_RULE_SET
            + PERMISSIVE_HYPERLINKS_ONLY_RULE_SET
        )
    )

    crawler.crawl()
    assert len(crawler.graph.visited_paths) == 2  # no onward links from example.com were visited
    node = crawler.graph.get_nodes_by_path("http://www.example.com/")[0]
    assert node
    assert node.requested
