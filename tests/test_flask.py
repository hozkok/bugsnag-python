import sys

from nose.plugins.skip import SkipTest
if (3, 0) <= sys.version_info < (3, 3):  # noqa
    raise SkipTest("Flask is incompatible with python3 3.0 - 3.2")

import unittest

from nose.tools import eq_, ok_
from mock import patch
from flask import Flask

from bugsnag.flask import handle_exceptions
import bugsnag.notification


bugsnag.configuration.api_key = '066f5ad3590596f9aa8d601ea89af845'


class SentinalError(RuntimeError):
    pass


class TestFlask(unittest.TestCase):

    @patch('bugsnag.notification.deliver')
    def test_bugsnag_middleware_working(self, deliver):
        app = Flask("bugsnag")

        @app.route("/hello")
        def hello():
            return "OK"

        handle_exceptions(app)

        resp = app.test_client().get('/hello')
        eq_(resp.data, b'OK')

        eq_(deliver.call_count, 0)

    @patch('bugsnag.notification.deliver')
    def test_bugsnag_crash(self, deliver):
        app = Flask("bugsnag")

        @app.route("/hello")
        def hello():
            raise SentinalError("oops")

        handle_exceptions(app)
        app.test_client().get('/hello')

        eq_(deliver.call_count, 1)
        payload = deliver.call_args[0][0]
        eq_(payload['events'][0]['exceptions'][0]['errorClass'],
            'test_flask.SentinalError')
        eq_(payload['events'][0]['metaData']['request']['url'],
            'http://localhost/hello')

    @patch('bugsnag.notification.deliver')
    def test_bugsnag_notify(self, deliver):
        app = Flask("bugsnag")

        @app.route("/hello")
        def hello():
            bugsnag.notify(SentinalError("oops"))
            return "OK"

        handle_exceptions(app)
        app.test_client().get('/hello')

        eq_(deliver.call_count, 1)
        payload = deliver.call_args[0][0]
        eq_(payload['events'][0]['metaData']['request']['url'],
            'http://localhost/hello')

    @patch('bugsnag.notification.deliver')
    def test_bugsnag_custom_data(self, deliver):
        meta_data = [{"hello": {"world": "once"}},
                     {"again": {"hello": "world"}}]

        app = Flask("bugsnag")

        @app.route("/hello")
        def hello():
            bugsnag.configure_request(meta_data=meta_data.pop())
            raise SentinalError("oops")

        handle_exceptions(app)
        app.test_client().get('/hello')
        app.test_client().get('/hello')

        eq_(deliver.call_count, 2)

        payload = deliver.call_args_list[0][0][0]
        eq_(payload['events'][0]['metaData'].get('hello'), None)
        eq_(payload['events'][0]['metaData']['again']['hello'], 'world')

        payload = deliver.call_args_list[1][0][0]
        eq_(payload['events'][0]['metaData']['hello']['world'], 'once')
        eq_(payload['events'][0]['metaData'].get('again'), None)

    @patch('bugsnag.notification.deliver')
    def test_bugsnag_includes_posted_json_data(self, deliver):
        app = Flask("bugsnag")

        @app.route("/ajax", methods=["POST"])
        def hello():
            raise SentinalError("oops")

        handle_exceptions(app)
        app.test_client().post(
            '/ajax', data='{"key": "value"}', content_type='application/json')

        eq_(deliver.call_count, 1)
        payload = deliver.call_args[0][0]
        event = payload['events'][0]
        eq_(event['exceptions'][0]['errorClass'], 'test_flask.SentinalError')
        eq_(event['metaData']['request']['url'], 'http://localhost/ajax')
        eq_(event['metaData']['request']['data'], dict(key='value'))

    @patch('bugsnag.notification.deliver')
    def test_bugsnag_add_metadata_tab(self, deliver):
        app = Flask("bugsnag")

        @app.route("/form", methods=["PUT"])
        def hello():
            bugsnag.add_metadata_tab("account", {"id": 1, "premium": True})
            bugsnag.add_metadata_tab("account", {"premium": False})
            raise SentinalError("oops")

        handle_exceptions(app)
        app.test_client().put(
            '/form', data='_data', content_type='application/octet-stream')

        eq_(deliver.call_count, 1)
        payload = deliver.call_args[0][0]
        eq_(payload['events'][0]['metaData']['account']['premium'], False)

        eq_(payload['events'][0]['metaData']['account']['id'], 1)

    @patch('bugsnag.notification.deliver')
    def test_bugsnag_includes_unknown_content_type_posted_data(self, deliver):
        app = Flask("bugsnag")

        @app.route("/form", methods=["PUT"])
        def hello():
            raise SentinalError("oops")

        handle_exceptions(app)
        app.test_client().put(
            '/form', data='_data', content_type='application/octet-stream')

        eq_(deliver.call_count, 1)
        payload = deliver.call_args[0][0]
        event = payload['events'][0]
        eq_(event['exceptions'][0]['errorClass'],
            'test_flask.SentinalError')
        eq_(event['metaData']['request']['url'],
            'http://localhost/form')
        ok_('_data' in event['metaData']['request']['data']['body'])
