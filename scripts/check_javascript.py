"""Syntax-check local JavaScript and executable inline scripts; does not load external libraries."""
from pathlib import Path
from html.parser import HTMLParser
import subprocess
import tempfile

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__(); self.active = False; self.parts = []; self.scripts = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            attrs = dict(attrs); self.active = not attrs.get('src') and attrs.get('type', '') in ('', 'text/javascript', 'application/javascript'); self.parts = []
    def handle_data(self, data):
        if self.active: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            self.scripts.append(''.join(self.parts)); self.active = False

for path in sorted(Path('frontend').rglob('*.js')):
    subprocess.run(['node', '--check', str(path)], check=True)
for path in sorted(Path('frontend').rglob('*.html')):
    parser = Scripts(); parser.feed(path.read_text(encoding='utf-8'))
    for script in parser.scripts:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'inline.js'; target.write_text(script, encoding='utf-8')
            print(f'Checking {path}', flush=True)
            subprocess.run(['node', '--check', str(target)], check=True)
