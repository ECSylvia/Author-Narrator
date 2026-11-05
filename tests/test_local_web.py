import io
import json
import unittest
from unittest.mock import patch

import local_web


class Request:
    valid_host = local_web.Handler.valid_host

    def __init__(self, path, body, origin=None):
        payload = json.dumps(body).encode()
        self.path = path
        self.headers = {'Content-Length': str(len(payload)), 'Host': '127.0.0.1:8765'}
        if origin:
            self.headers['Origin'] = origin
        self.rfile = io.BytesIO(payload)
        self.result = None

    def send(self, value, status=200, mime='application/json'):
        self.result = (status, value)


class LocalWebTests(unittest.TestCase):
    def test_import_ignores_empty_preamble(self):
        request = Request('/api/import', {'name': 'book.md', 'text': '\n# One\nHello\n# Two\nWorld'})
        local_web.Handler.do_POST(request)
        status, data = request.result
        self.assertEqual(status, 200)
        self.assertEqual([c['title'] for c in data['chapters']], ['One', 'Two'])

    def test_cross_origin_generation_rejected(self):
        request = Request('/api/generate', {'text': 'Hello'}, 'https://example.com')
        with patch.object(local_web, 'speech') as speech:
            local_web.Handler.do_POST(request)
        self.assertEqual(request.result[0], 403)
        speech.assert_not_called()

    def test_hub_origin_allowed(self):
        request = Request('/api/import', {'name': 'book.md', 'text': '# One\nHello'}, 'http://127.0.0.1:5173')
        request.headers['Host'] = '127.0.0.1:5173'
        local_web.Handler.do_POST(request)
        self.assertEqual(request.result[0], 200)

    def test_unknown_host_rejected(self):
        request = Request('/api/import', {'text': 'Hello'})
        request.headers['Host'] = 'attacker.example'
        local_web.Handler.do_POST(request)
        self.assertEqual(request.result[0], 403)

    def test_empty_narration_rejected(self):
        request = Request('/api/generate', {'text': '  '})
        with patch.object(local_web, 'speech') as speech:
            local_web.Handler.do_POST(request)
        self.assertEqual(request.result[0], 400)
        speech.assert_not_called()


if __name__ == '__main__':
    unittest.main()
