
import pytest

from python_testing_crawler import Crawler
from python_testing_crawler.clients import DummyClient


def test_valid_css_selectors():
    Crawler(
        client=DummyClient(),
        ignore_css_selectors=['a.class', 'form#id']
    )


def test_invalid_css_selectors():
    with pytest.raises(ValueError):
        Crawler(
            client=DummyClient(),
            ignore_css_selectors=['£$%RT']
        )
