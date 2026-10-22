#!/usr/bin/env python3
"""Check published data, links, resume bytes and source-PDF exclusions."""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check():
    shared = json.loads((ROOT / 'data.js').read_text().removeprefix('window.TALENTX = ').strip().removesuffix(';'))
    data = json.loads((ROOT / 'guru/data.js').read_text().removeprefix('window.TALENTX = ').strip().removesuffix(';'))
    assert shared['audience'] == 'shared' and data['audience'] == 'guru'
    assert 'profile' not in shared and 'resumes' not in shared and 'plan' not in shared['event']
    assert not re.search(r'guruprasath|guru[’\'s ]|BugRaid|TalkToIt|ResearchAgent|5000', json.dumps(shared), re.I)
    assert all(not path.startswith(('resumes/', 'guru/')) and path != 'data/profile.json' for path in shared['offline_files'])
    assert '<base href="../">' in (ROOT / 'guru/index.html').read_text()
    assert 'src="guru/data.js"' in (ROOT / 'guru/index.html').read_text()
    companies, resumes, event = data['companies'], data['resumes'], data['event']
    assert len(companies) == len(resumes) == 18
    assert {c['id'] for c in companies} == {r['company_id'] for r in resumes} == set(event['booths'])
    assert sum(bool(b['floor']) for b in event['booths'].values()) == 16
    assert len(event['talks']) == 8
    for c in companies:
        assert c['checked_at'].endswith('+08:00'), c['id']
        assert c['sources'] and c['questions'] and c['summary']
        for url in [c['website'], c['careers_url']] + [s['url'] for s in c['sources']] + [r['url'] for r in c['roles']]:
            assert urlsplit(url).scheme == 'https', (c['id'], url)
        for r in c['roles']:
            assert r['status'] in {'verified-open', 'closed', 'portal-only', 'unverified'}
            assert r['source_note'] and r['eligibility']
    for c in shared['companies']:
        assert 'fit_reason' not in c and 'conversation_opener' not in c
        assert all('fit' not in r for r in c['roles'])
    for r in resumes:
        path = ROOT / r['pdf']
        assert path.read_bytes().startswith(b'%PDF-')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == r['sha256'], path
        provenance = json.loads((ROOT / r['provenance']).read_text())
        assert r['source_master_id'] == 'master-2026-10-18-v2'
        assert not re.search(r'/Users/|/workspace/', json.dumps(provenance))
        assert (ROOT / r['markdown']).is_file()
    for path in data['offline_files']:
        assert (ROOT / path).exists(), path
        assert not path.startswith(('.local', '/'))
    with zipfile.ZipFile(ROOT / 'resumes/talentx-resume-pack.zip') as z:
        assert len([n for n in z.namelist() if n.endswith('.pdf')]) == 18
    source_hashes = {s['sha256'] for s in json.loads((ROOT / 'data/source-inputs.json').read_text())}
    for path in ROOT.rglob('*.pdf'):
        if '.local' in path.parts:
            continue
        assert hashlib.sha256(path.read_bytes()).hexdigest() not in source_hashes, 'Original PDF in publication: ' + str(path)
        assert path.parent == ROOT / 'resumes', path
        assert path.stem in event['booths'], path
    git_dir = ROOT / '.git'
    if git_dir.exists():
        tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files'], text=True, capture_output=True, check=True).stdout.splitlines()
        assert not any(p.startswith('.local/') or 'Company Guide' in p or 'Student_Briefing' in p for p in tracked)
        assert all(not p.endswith('.pdf') or p.startswith('resumes/') for p in tracked)
    print(f'PASS: shared/personal data separated; {len(companies)} companies, 16 booths, 8 sessions; 18 resume hashes; offline assets; publication boundary')


if __name__ == '__main__':
    check()
