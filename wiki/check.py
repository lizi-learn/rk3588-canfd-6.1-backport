#!/usr/bin/env python3
"""Check published local destinations and catch common private-data mistakes."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

OUT = Path(__file__).resolve().parent / 'dist'
class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links = set(), []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            assert a['id'] not in self.ids, 'Duplicate ID: ' + a['id']
            self.ids.add(a['id'])
        for attr in ('href', 'src'):
            if a.get(attr):
                self.links.append(a[attr])

def main():
    pages = {p.relative_to(OUT).as_posix(): Page(p.read_text()) for p in OUT.glob('*.html')}
    assert len(pages) >= 12, 'Missing Wiki articles'
    errors, checked = [], 0
    def check(href, origin):
        nonlocal checked
        u = urlsplit(href)
        if u.scheme or u.netloc:
            return
        rel = unquote(u.path).lstrip('/') or (origin if u.fragment else 'index.html')
        if rel.endswith('/'):
            rel += 'index.html'
        if rel not in pages and not (OUT / rel).is_file():
            errors.append(f'{origin}: missing {href}')
        if u.fragment and rel in pages and unquote(u.fragment) not in pages[rel].ids:
            errors.append(f'{origin}: missing anchor {href}')
        checked += 1
    for path, page in pages.items():
        for href in page.links:
            check(href, path)
    index = json.loads((OUT / 'search-index.json').read_text())
    for record in index:
        check(record['url'], 'search-index.json')
    corpus = '\n'.join(p.read_text() for p in OUT.rglob('*') if p.is_file() and p.suffix != '.svg')
    patterns = {
        'private IPv4': r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b',
        'MAC address': r'\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b',
        'private key': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
        'token value': r'(?:oauth_token|refresh_token|dns_cloudflare_api_key)\s*[=:]\s*[\"\x27]?[\w-]{16,}',
        'old password': r'\btemppwd\b',
        'remote ID': r'(?i)(?:ToDesk\s*(?:ID|设备码)|NoMachine\s*(?:ID|设备码))\s*[:：]\s*\d{6,}'
    }
    for label, pattern in patterns.items():
        if re.search(pattern, corpus):
            errors.append('Potential private data: ' + label)
    assert not errors, '\n'.join(errors)
    assert all(any(term in r['text'] for r in index) for term in ('p2p0', '12,386,944', '1.5M', 'SingletonLock'))
    print(f'Wiki check passed: {len(pages)} HTML files, {len(index)} search sections, {checked} local destinations; privacy patterns clear')

if __name__ == '__main__':
    main()
