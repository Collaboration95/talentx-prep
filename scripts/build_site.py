#!/usr/bin/env python3
"""Assemble the static site from checked-in research and resume metadata."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import zipfile
import copy

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def build():
    event, profile, resumes = read('data/event.json'), read('data/profile.json'), read('resumes/index.json')
    researched = {}
    for filename in ['ai-health.json', 'finance-enterprise.json', 'industry.json']:
        for company in read('research/' + filename):
            if company['id'] in researched:
                raise ValueError('Duplicate company: ' + company['id'])
            researched[company['id']] = company
    companies = [researched[id] for id in event['booths']]
    if len(companies) != 18 or len(resumes) != 18:
        raise ValueError('Expected 18 researched companies and 18 tailored resumes')
    for resume in resumes:
        for field in ['pdf', 'markdown', 'provenance']:
            if not (ROOT / resume[field]).is_file():
                raise ValueError('Missing ' + resume[field])
        if hashlib.sha256((ROOT / resume['pdf']).read_bytes()).hexdigest() != resume['sha256']:
            raise ValueError('Resume hash mismatch: ' + resume['company_id'])
    # Reproducible archive: PDF, editable text and provenance for each employer.
    with zipfile.ZipFile(ROOT / 'resumes/talentx-resume-pack.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for resume in resumes:
            for field in ['pdf', 'markdown', 'provenance']:
                path = resume[field]
                info = zipfile.ZipInfo(path, date_time=(2026, 10, 22, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (ROOT / path).read_bytes())
        info = zipfile.ZipInfo('resumes/index.json', date_time=(2026, 10, 22, 0, 0, 0))
        archive.writestr(info, (ROOT / 'resumes/index.json').read_bytes())
        for master in sorted((ROOT / 'resumes/sources').glob('*.md')):
            info = zipfile.ZipInfo(str(master.relative_to(ROOT)), date_time=(2026, 10, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, master.read_bytes())
    # A real directory entry supports /guru and /guru/ on static GitHub Pages.
    guru = ROOT / 'guru'
    guru.mkdir(exist_ok=True)
    entry = (ROOT / 'index.html').read_text().replace('<html lang="en">', '<html lang="en" data-audience="guru">')
    entry = entry.replace('<head>', '<head>\n  <base href="../">')
    entry = entry.replace('src="data.js"', 'src="guru/data.js"')
    entry = entry.replace('href="manifest.webmanifest"', 'href="guru/manifest.webmanifest"')
    entry = entry.replace('</nav>', '<a href="#targets" data-nav="targets">My targets</a></nav>')
    (guru / 'index.html').write_text(entry)
    manifest = read('manifest.webmanifest')
    manifest.update(name='TalentXperience 2026 · Guru', short_name='Guru TalentX', start_url='./', scope='../')
    for icon in manifest['icons']:
        icon['src'] = '../' + icon['src']
    (guru / 'manifest.webmanifest').write_text(json.dumps(manifest) + '\n')
    shared_event = copy.deepcopy(event)
    shared_event.pop('plan')
    (ROOT / 'data/shared-event.json').write_text(json.dumps(shared_event, indent=2, ensure_ascii=False) + '\n')
    shared_companies = copy.deepcopy(companies)
    overrides = read('research/shared-overrides.json')
    for company in shared_companies:
        for field in ['fit_reason', 'conversation_opener', 'priority', 'resume_track']:
            company.pop(field, None)
        company.update(overrides[company['id']])
        company['questions'] = company['questions'][:2] + ['What enrolment, academic-credit, start-date, duration and work-pass requirements apply to this placement?']
        for role in company['roles']:
            role.pop('fit', None)
            role['eligibility'] = role['eligibility'].replace('Candidate GPA eligibility unconfirmed.', 'Applicants should check the stated GPA threshold.')
        for source in company['sources']:
            source['note'] = source['note'].replace('Not selected as a close candidate match.', 'Requires Android-specific experience.')
    files = ['.', 'index.html', 'style.css', 'app.js', 'data.js', 'assets/icon.svg', 'manifest.webmanifest', 'event.ics', 'assets/fonts/fonts.css']
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'assets/fonts').glob('*.ttf'))]
    files += ['data/shared-event.json']
    personal_files = files + ['guru/', 'guru/index.html', 'guru/data.js', 'guru/manifest.webmanifest']
    personal_files += [r[field] for r in resumes for field in ['pdf', 'markdown', 'provenance']]
    personal_files += ['resumes/index.json', 'resumes/talentx-resume-pack.zip', 'data/profile.json', 'data/event.json', 'data/guru-strategy.json', 'README.md']
    personal_files += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'resumes/sources').glob('*.md'))]
    content = json.dumps({'event': event, 'profile': profile, 'companies': companies, 'resumes': resumes}, sort_keys=True)
    strategy = read('data/guru-strategy.json')
    content += json.dumps(strategy, sort_keys=True)
    content += json.dumps(shared_companies, sort_keys=True)
    version_material = content + ''.join(path + hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in personal_files if path not in {'.', 'guru/', 'data.js', 'guru/data.js'})
    version = hashlib.sha256(version_material.encode()).hexdigest()[:12]
    cache_name = 'talentx-' + version
    data = {'audience': 'shared', 'event': shared_event, 'companies': shared_companies,
            'built_at': datetime.now(ZoneInfo('Asia/Singapore')).isoformat(),
            'repository_url': 'https://github.com/Collaboration95/talentx-prep',
            'site_url': 'https://collaboration95.github.io/talentx-prep/',
            'offline_cache': cache_name, 'offline_files': files}
    (ROOT / 'data.js').write_text('window.TALENTX = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    personal = {**data, 'audience': 'guru', 'event': event, 'profile': profile, 'resumes': resumes,
                'companies': companies, 'strategy': strategy, 'offline_files': personal_files}
    (guru / 'data.js').write_text('window.TALENTX = ' + json.dumps(personal, ensure_ascii=False, separators=(',', ':')) + ';\n')
    core = ['.', 'index.html', 'style.css', 'app.js', 'data.js', 'assets/icon.svg', 'manifest.webmanifest', 'assets/fonts/fonts.css']
    core += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'assets/fonts').glob('*.ttf'))]
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in personal_files if path not in core and path != 'guru/'}
    sw = """/* Generated by scripts/build_site.py. Scope is this project only. */
const CACHE = __CACHE__;
const CORE = __CORE__;
const SAVED_HASHES = __HASHES__;
async function matchesHash(response, expected) {
  if (!response || !response.ok) return false;
  const digest = await crypto.subtle.digest('SHA-256', await response.clone().arrayBuffer());
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('') === expected;
}
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const current = await caches.open(CACHE);
    const oldNames = (await caches.keys()).filter(k => k.startsWith('talentx-') && k !== CACHE);
    for (const name of oldNames) {
      const old = await caches.open(name);
      for (const request of await old.keys()) {
        const relative = new URL(request.url).pathname.slice(new URL(self.registration.scope).pathname.length);
        const expected = SAVED_HASHES[relative];
        if (!expected || await current.match(request)) continue;
        const saved = await old.match(request);
        if (await matchesHash(saved, expected)) await current.put(request, saved);
        else {
          try { const fresh = await fetch(request); if (await matchesHash(fresh, expected)) await current.put(request, fresh); }
          catch (_) { /* A changed file must be saved again rather than serving a superseded resume. */ }
        }
      }
      await caches.delete(name);
    }
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== location.origin || !url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
  event.respondWith(fetch(event.request).then(response => {
    if (response.ok) { const clone = response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, clone)); }
    return response;
  }).catch(async () => {
    const activeCache = await caches.open(CACHE);
    const cached = await activeCache.match(event.request);
    if (cached) return cached;
    if (event.request.mode === 'navigate' && !/\\.[a-z0-9]+$/i.test(url.pathname)) {
      const relative = url.pathname.slice(new URL(self.registration.scope).pathname.length);
      const entry = relative === 'guru' || relative.startsWith('guru/') ? 'guru/index.html' : 'index.html';
      const shell = await activeCache.match(new URL(entry, self.registration.scope).href);
      if (shell) return shell;
    }
    return new Response('This file is not saved offline. Reconnect and use Prep kit → Save offline.', {status:503, headers:{'Content-Type':'text/plain; charset=utf-8'}});
  }));
});
""".replace('__CACHE__', json.dumps(cache_name)).replace('__CORE__', json.dumps(core)).replace('__HASHES__', json.dumps(hashes))
    (ROOT / 'sw.js').write_text(sw)
    print(f'Built {len(companies)} companies, {len(resumes)} resumes, {len(files)} offline files; {cache_name}')


if __name__ == '__main__':
    build()
