"""Local Author-Narrator workspace. Run: python local_web.py."""
import json
import os
import subprocess
import sys
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.core.manuscript_parser import ManuscriptParser

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('NARRATOR_DATA_DIR', ROOT / 'local_data'))
HOSTS = ('127.0.0.1:8765', 'localhost:8765', '127.0.0.1:5173', 'localhost:5173')
HOSTS += tuple(filter(None, os.environ.get('NARRATOR_HUB_HOSTS', '').split(',')))
SPEECH = r'''
Add-Type -AssemblyName System.Speech
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  if ($request.action -eq 'voices') {
    $voices = @($synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })
    ConvertTo-Json -InputObject $voices -Compress
  } else {
    if ($request.voice) { $synth.SelectVoice($request.voice) }
    $synth.SetOutputToWaveFile($request.path)
    $synth.Speak($request.text)
  }
} finally { $synth.Dispose() }
'''


def speech(request):
    if sys.platform.startswith('linux'):
        voices = ('en-us', 'en-gb')
        if request.get('action') == 'voices':
            return json.dumps(voices)
        voice = request.get('voice') or voices[0]
        if voice not in voices:
            raise ValueError('Select an installed narration voice')
        result = subprocess.run(
            ['espeak-ng', '-v', voice, '-w', request['path'], '--stdin'],
            input=request['text'], encoding='utf-8', capture_output=True, timeout=300,
        )
        if result.returncode:
            raise RuntimeError('Linux narration failed')
        return ''
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', SPEECH],
        input=json.dumps(request), capture_output=True, text=True, timeout=300,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise RuntimeError('Windows narration failed. Check that a Windows speech voice is installed.')
    return result.stdout.strip()


class Handler(BaseHTTPRequestHandler):
    def valid_host(self):
        return self.headers.get('Host') in HOSTS

    def send(self, value, status=200, mime='application/json'):
        body = json.dumps(value).encode() if mime == 'application/json' else value
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.valid_host():
            return self.send({'error': 'Invalid host'}, 403)
        path = urlparse(self.path).path
        if path == '/api/project':
            saved = DATA / 'project.json'
            return self.send(json.loads(saved.read_text('utf-8')) if saved.exists() else None)
        if path == '/api/voices':
            try:
                return self.send({'voices': json.loads(speech({'action': 'voices'}))})
            except Exception as exc:
                return self.send({'error': str(exc)}, 503)
        if path.startswith('/audio/'):
            name = path.removeprefix('/audio/')
            if len(name) != 36 or not name.endswith('.wav') or any(c not in '0123456789abcdef.wav' for c in name):
                return self.send({'error': 'Not found'}, 404)
            file = DATA / name
            if file.exists():
                return self.send(file.read_bytes(), mime='audio/wav')
            return self.send({'error': 'Not found'}, 404)
        assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path in assets:
            name, mime = assets[path]
            return self.send((ROOT / 'web' / name).read_bytes(), mime=mime)
        self.send({'error': 'Not found'}, 404)

    def do_POST(self):
        # Same-origin browser requests only; never expose this service beyond loopback.
        if not self.valid_host():
            return self.send({'error': 'Invalid host'}, 403)
        origin = self.headers.get('Origin')
        if origin and origin != f'http://{self.headers.get("Host")}':
            return self.send({'error': 'Cross-origin request rejected'}, 403)
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 5_000_000:
                return self.send({'error': 'Request must be under 5 MB'}, 413)
            request = json.loads(self.rfile.read(length))
            path = urlparse(self.path).path
            if path == '/api/import':
                content = request['text']
                parser = ManuscriptParser._parse_markdown if request.get('name', '').lower().endswith('.md') else ManuscriptParser._parse_text
                chapters = [dict(title=c.title, text=c.content, status='Draft') for c in parser(content) if c.content.strip()]
                return self.send({'chapters': chapters})
            if path == '/api/project':
                if not isinstance(request.get('chapters'), list):
                    raise ValueError('Project must contain chapters')
                DATA.mkdir(exist_ok=True)
                temporary = DATA / f'{uuid.uuid4().hex}.tmp'
                temporary.write_text(json.dumps(request, ensure_ascii=False), 'utf-8')
                temporary.replace(DATA / 'project.json')
                return self.send({'saved': True})
            if path == '/api/generate':
                text = request['text'].strip()
                if not text or len(text) > 50000:
                    raise ValueError('Enter between 1 and 50,000 characters for narration')
                DATA.mkdir(exist_ok=True)
                name = uuid.uuid4().hex + '.wav'
                speech({'text': text, 'voice': request.get('voice'), 'path': str(DATA / name)})
                return self.send({'url': '/audio/' + name})
            self.send({'error': 'Not found'}, 404)
        except (ValueError, KeyError, TypeError) as exc:
            self.send({'error': str(exc)}, 400)
        except Exception as exc:
            self.send({'error': str(exc)}, 500)


class LocalServer(ThreadingHTTPServer):
    # Windows otherwise permits duplicate listeners which can stall connections.
    allow_reuse_address = False


if __name__ == '__main__':
    server = LocalServer((os.environ.get('NARRATOR_BIND', '127.0.0.1'), 8765), Handler)
    print('Author-Narrator 2.0: http://127.0.0.1:8765', flush=True)
    if '--open' in sys.argv:
        threading.Timer(1, lambda: webbrowser.open('http://127.0.0.1:8765')).start()
    server.serve_forever()
