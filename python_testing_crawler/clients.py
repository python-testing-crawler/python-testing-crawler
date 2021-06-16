# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import inspect
from urllib.parse import urldefrag

from bs4 import BeautifulSoup
import soupsieve

from .graph import Node
from .utils import acceptable_content_type
from .constants import FORM, GET


class DummyClient:
    pass


class BaseClientWrapper:

    def get_content(self, response):
        raise NotImplementedError

    def get_content_type(self, response):
        raise NotImplementedError

    def is_valid_for_extraction(self, response):
        return acceptable_content_type(self.get_content_type(response))

    def extract(self, response, element_names, attr_names):
        soup = BeautifulSoup(self.get_content(response), "html.parser")
        filtered_elements = (
            element for element in soup.find_all() if (
                (not element_names or element.name in element_names)
                and not any(
                    soupsieve.match(selector, element) for selector in self.ignore_css_selectors
                )
            )
        )
        for element in filtered_elements:
            for attr_name in attr_names:
                attr = element.get(attr_name)
                if attr:
                    defragged_attr = urldefrag(attr)[0]
                    yield Node(source=element.name, path=defragged_attr)

    def extract_forms(self, path, response, ignore_form_fields=None):
        soup = BeautifulSoup(self.get_content(response), "html.parser")
        form_elements = soup.find_all('form')
        forms = [
            Node(
                source=FORM,
                method=form_element.get('method', GET),
                path=form_element.get('action', path),
                params={
                    input_element['name']: input_element.get('value', '')
                    for input_element
                    in form_element.find_all('input', {'name': True})
                },
                ignore_form_fields=ignore_form_fields
            )
            for form_element in form_elements
            if not any(soupsieve.match(sel, form_element) for sel in self.ignore_css_selectors)
        ]
        return forms


class DummyClientWrapper:

    def __init__(self, client=None, ignore_css_selectors=None):
        self.client = client
        self.ignore_css_selectors = ignore_css_selectors or []


class FlaskClientWrapper(BaseClientWrapper):

    def __init__(self, client, ignore_css_selectors=None):
        self.client = client
        self.ignore_css_selectors = ignore_css_selectors or []

    def get(self, path, fields=None):
        return self.client.get(path, query_string=fields or None)

    def post(self, path, fields=None):
        return self.client.post(path, data=fields or None)

    def get_content(self, response):
        return response.data

    def get_content_type(self, response):
        return response.content_type


class WebTestClientWrapper(BaseClientWrapper):

    def __init__(self, webtest_app, ignore_css_selectors=None):
        self.webtest_app = webtest_app
        self.ignore_css_selectors = ignore_css_selectors or []

    def get(self, path, fields=None):
        return self.webtest_app.get(path, params=fields, expect_errors=True)

    def post(self, path, fields=None):
        return self.webtest_app.post(path, params=fields, expect_errors=True)

    def get_content(self, response):
        return response.body

    def get_content_type(self, response):
        return response.content_type


class DjangoClientWrapper(BaseClientWrapper):

    def __init__(self, client, ignore_css_selectors):
        self.client = client
        self.ignore_css_selectors = ignore_css_selectors or []

    def get(self, path, fields=None):
        return self.client.get(path, data=fields, follow=True)

    def post(self, path, fields=None):
        return self.client.post(path, data=fields, follow=True)

    def get_content(self, response):
        return response.content

    def get_content_type(self, response):
        return response.get('Content-Type')


def detect_and_wrap_client(client, ignore_css_selectors):
    client_class_pairs = [
        (cls.__module__, cls.__name__) for cls in
        inspect.getmro(client.__class__)
    ]
    for client_class_pair in client_class_pairs:
        if client_class_pair == ('flask.testing', 'FlaskClient'):
            return FlaskClientWrapper(client=client, ignore_css_selectors=ignore_css_selectors)
        if client_class_pair == ('webtest.app', 'TestApp'):
            return WebTestClientWrapper(webtest_app=client, ignore_css_selectors=ignore_css_selectors)
        if client_class_pair == ('flask_webtest', 'TestApp'):
            return WebTestClientWrapper(webtest_app=client, ignore_css_selectors=ignore_css_selectors)
        if client_class_pair == ('django.test.client', 'Client'):
            return DjangoClientWrapper(client=client, ignore_css_selectors=ignore_css_selectors)
        if client_class_pair == ('python_testing_crawler.clients', 'DummyClient'):
            return DummyClientWrapper()
    else:
        raise ValueError(f"Unknown client: {client}")
