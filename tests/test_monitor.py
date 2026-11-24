import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'oref-monitor' / 'app'))
from oref_monitor import make_fingerprint, build_alert_keys, is_valid_alert, make_status

class MonitorTests(unittest.TestCase):
    def test_fingerprint_independent_of_dictionary_order(self):
        self.assertEqual(make_fingerprint({'id': 'demo', 'cat': 'test'}), make_fingerprint({'cat': 'test', 'id': 'demo'}))

    def test_locality_key_order(self):
        base = {'id': 'demo', 'cat': 'test', 'title': 'synthetic'}
        self.assertEqual(build_alert_keys(dict(base, data=['B', 'A'])), build_alert_keys(dict(base, data=['A', 'B'])))

    def test_invalid_alert(self):
        self.assertFalse(is_valid_alert(None))
        self.assertFalse(is_valid_alert({'title': 'synthetic', 'data': 'not a list'}))

    def test_failed_fetch_status(self):
        status = make_status(ok=False, error_message='synthetic error')
        self.assertFalse(status['ok'])
        self.assertFalse(status['has_active_alert'])
        self.assertEqual(status['error'], 'synthetic error')

if __name__ == '__main__':
    unittest.main()
