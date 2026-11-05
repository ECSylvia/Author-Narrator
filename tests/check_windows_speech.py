"""Isolated real Windows speech and HTTP routing check; never uses local_data."""
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
import local_web

class IsolatedSpeechTest(unittest.TestCase):
    def test_generation_and_download(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(local_web, 'DATA', Path(directory)):
            server = local_web.LocalServer(('127.0.0.1', 0), local_web.Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                base = 'http://127.0.0.1:' + str(server.server_port)
                headers = {'Host': '127.0.0.1:5173', 'Origin': 'http://127.0.0.1:5173', 'Content-Type': 'application/json'}
                request = urllib.request.Request(base + '/api/generate', data=json.dumps({'text': 'Author Narrator integration test.'}).encode(), headers=headers)
                with urllib.request.urlopen(request, timeout=310) as response:
                    audio = json.load(response)['url']
                with urllib.request.urlopen(urllib.request.Request(base + audio, headers=headers)) as response:
                    self.assertEqual(response.headers.get_content_type(), 'audio/wav')
                    self.assertEqual(response.read(4), b'RIFF')
                self.assertFalse((Path(directory) / 'project.json').exists())
            finally:
                server.shutdown()
                server.server_close()
                worker.join()

if __name__ == '__main__':
    unittest.main()
