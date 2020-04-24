import os

import django
from django.conf import settings
from django.test.utils import get_runner
from django.test.client import Client

from tests.webapps.django import tutorial_mysite

from python_testing_crawler import Crawler
from .example_rules import (
    PERMISSIVE_ALL_ELEMENTS_RULE_SET,
    SUBMIT_GET_FORMS_RULE_SET,
    SUBMIT_POST_FORMS_RULE_SET,
)


def test_crawl_all(monkeypatch):
    path = tutorial_mysite.__path__[0]
    with monkeypatch.context() as patch:
        patch.chdir(path)
        patch.syspath_prepend(path)

        os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
        django.setup()
        from django.core import management
        management.call_command("migrate")
        management.call_command("loaddata", "polls/fixtures/fixtures.json")

        TestRunner = get_runner(settings)
        test_runner = TestRunner()
        client = Client()

        crawler = Crawler(
            client=client,
            initial_paths=['/', '/polls'],
            rules=(
                PERMISSIVE_ALL_ELEMENTS_RULE_SET +
                SUBMIT_GET_FORMS_RULE_SET +
                SUBMIT_POST_FORMS_RULE_SET
            ),
            ignore_form_fields={'csrfmiddlewaretoken'},
            capture_exceptions=False,
        )
        crawler.crawl()

        # check urls
        for i in range(1, 4):
            assert f"/polls/{i}/" in crawler.graph.visited_paths
            assert f"/polls/{i}/vote" in crawler.graph.visited_paths
