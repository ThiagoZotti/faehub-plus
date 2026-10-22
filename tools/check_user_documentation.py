"""Validate the documentation artifact without loading Flask or school data."""
import hashlib
import json
from pathlib import Path
import re

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs' / 'manual'


def check():
    data = json.loads((SOURCE/'conteudo.json').read_text(encoding='utf-8'))
    manifest = json.loads((SOURCE/'manifesto.json').read_text(encoding='utf-8'))
    evidence = json.loads((SOURCE/'navegacao.json').read_text(encoding='utf-8'))
    pdf = ROOT / manifest['pdf']
    assert pdf.is_file()
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == manifest['pdf_sha256']
    assert len(data['pages']) == len({page['id'] for page in data['pages']})
    cases = {page['uc'] for page in data['pages'] if page.get('uc')}
    assert cases == {f'UC{i:02d}' for i in range(1, 40)}
    observed = {item['key'] for item in evidence['telas']}
    assert len(observed) == manifest['captured_viewports'] == 55
    for page in data['pages']:
        if page.get('shot'):
            assert page['shot'] in observed
    for asset in manifest['assets']:
        path = SOURCE/'capturas'/asset['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset['sha256']
        with Image.open(path) as im:
            assert im.format == 'JPEG'
            assert im.width >= 1000 and im.height >= 600
            im.verify()
    diagrams = list((SOURCE/'diagramas').glob('*.svg'))
    assert len(diagrams) == manifest['diagrams'] == 6
    assert all('<svg' in path.read_text(encoding='utf-8') for path in diagrams)
    reader = PdfReader(pdf)
    texts = [page.extract_text() or '' for page in reader.pages]
    text = '\n'.join(texts)
    assert all(len(item.strip()) > 100 for item in texts), 'Unexpected blank or orphan page'
    assert '\ufffd' not in text, 'Replacement glyph in PDF text'
    for title in ('Documentação', 'Recuperar senha', 'autenticador', 'Classes do núcleo', 'Catálogo de casos de uso'):
        assert title.lower() in text.lower(), title
    assert all(case in text for case in cases)
    assert sum(float(page.mediabox.width) > float(page.mediabox.height) for page in reader.pages) == 6
    assert len(reader.outline) >= 50
    assert not re.search(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----|ya29\.[A-Za-z0-9_-]+', text)
    for link in re.findall(r'\]\(([^)]+)\)', (SOURCE/'manual.md').read_text(encoding='utf-8')):
        if not link.startswith(('https://', '#')):
            assert (SOURCE/link).is_file(), link
    print(json.dumps({'pages':len(reader.pages), 'captured_viewports':len(observed),
                      'screenshots_in_manual':manifest['screenshots_in_manual'],
                      'use_cases':len(cases),'uml_diagrams':len(diagrams),
                      'size_bytes':pdf.stat().st_size,'result':'PASS'},ensure_ascii=False))


if __name__ == '__main__':
    check()
