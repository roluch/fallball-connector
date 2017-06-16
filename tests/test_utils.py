from flask_testing import TestCase
from logging import LogRecord
from connector.app import app
from connector.utils import ConnectorLogFormatter, JsonLogFormatter
from datetime import datetime


class TestUtils(TestCase):
    def create_app(self):
        app.config.update({'TESTING': True})

        return app

    def test_json_log_formatter_format(self):
        formatter = JsonLogFormatter()
        record = LogRecord('fake_name', 'DEBUG', None, None, 'fake_message',
                           None, None)
        record.reseller_name = 'fake_reseller_name'
        # as return result of formatter.format is a string we will check the substring
        actual_record = formatter.format(record)
        assert 'fake_reseller_name' in actual_record
        assert datetime.now().isoformat(' ')[:-7] in actual_record
        record.msg = {
            'text': 'fake_text'
        }
        actual_record = formatter.format(record)
        assert 'fake_text' in actual_record

    def test_connector_log_formatter_format(self):
        formatter = ConnectorLogFormatter()
        record = LogRecord('fake_name', 'DEBUG', None, None, 'fake_message',
                           None, None)
        record.reseller_name = 'fake_reseller_name'
        # as return result of formatter.format is a string we will check the substring
        actual_record = formatter.format(record)
        assert 'fake_reseller_name' in actual_record
        assert datetime.now().isoformat(' ')[:-7] in actual_record
        record.msg = {
            'text': 'fake_text'
        }
        actual_record = formatter.format(record)
        assert 'fake_text' in actual_record

    def test_connector_log_formatter_dict_format(self):
        formatter = ConnectorLogFormatter()
        message = {'message': 'fake_message', 'type': 'message_type'}
        record = LogRecord('fake_name', 'DEBUG', None, None, message,
                           None, None)
        record.reseller_name = 'fake_reseller_name'
        # as return result of formatter.format is a string we will check the substring
        actual_record = formatter.format(record)
        assert 'fake_reseller_name' in actual_record
        assert 'MESSAGE_TYPE' in actual_record
        assert datetime.now().isoformat(' ')[:-7] in actual_record
        record.msg = {
            'text': 'fake_text'
        }
        actual_record = formatter.format(record)
        assert 'fake_text' in actual_record
