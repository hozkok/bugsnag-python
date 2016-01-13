import inspect
import unittest

from nose.tools import eq_

from bugsnag.configuration import Configuration
from bugsnag.notification import Notification
import fixtures


class TestNotification(unittest.TestCase):

    def test_sanitize(self):
        """
            It should sanitize request data
        """
        config = Configuration()
        notification = Notification(Exception("oops"), config, {},
                                    request={"params": {"password": "secret"}})

        notification.add_tab("request", {"arguments": {"password": "secret"}})

        payload = notification._payload()
        request = payload['events'][0]['metaData']['request']
        eq_(request['arguments']['password'], '[FILTERED]')
        eq_(request['params']['password'], '[FILTERED]')

    def test_code(self):
        """
            It should include code
        """
        config = Configuration()
        line = inspect.currentframe().f_lineno + 1
        notification = Notification(Exception("oops"), config, {})

        payload = notification._payload()

        code = payload['events'][0]['exceptions'][0]['stacktrace'][0]['code']
        lvl = "        "
        eq_(code[line - 3], lvl + "\"\"\"")
        eq_(code[line - 2], lvl + "config = Configuration()")
        eq_(code[line - 1], lvl + "line = inspect.currentframe().f_lineno + 1")
        eq_(code[line], lvl +
            "notification = Notification(Exception(\"oops\"), config, {})")
        eq_(code[line + 1], "")
        eq_(code[line + 2], lvl + "payload = notification._payload()")
        eq_(code[line + 3], "")

    def test_code_at_start_of_file(self):

        config = Configuration()
        notification = Notification(fixtures.start_of_file[1], config, {},
                                    traceback=fixtures.start_of_file[2])

        payload = notification._payload()

        code = payload['events'][0]['exceptions'][0]['stacktrace'][0]['code']
        eq_({1: '# flake8: noqa',
             2: 'try:',
             3: '    import sys; raise Exception("start")',
             4: 'except Exception: start_of_file = sys.exc_info()',
             5: '# 4',
             6: '# 5',
             7: '# 6'}, code)

    def test_code_at_end_of_file(self):

        config = Configuration()
        notification = Notification(fixtures.end_of_file[1], config, {},
                                    traceback=fixtures.end_of_file[2])

        payload = notification._payload()

        code = payload['events'][0]['exceptions'][0]['stacktrace'][0]['code']
        eq_({6:  '# 5',
             7:  '# 6',
             8:  '# 7',
             9:  '# 8',
             10: 'try:',
             11: '    import sys; raise Exception("end")',
             12: 'except Exception: end_of_file = sys.exc_info()'}, code)

    def test_code_turned_off(self):
        config = Configuration()
        config.send_code = False
        notification = Notification(Exception("oops"), config, {},
                                    traceback=fixtures.end_of_file[2])

        payload = notification._payload()

        code = payload['events'][0]['exceptions'][0]['stacktrace'][0]['code']
        self.assertEqual(code, None)
