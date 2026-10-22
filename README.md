# TalentXperience 2026 companion

Live site: https://collaboration95.github.io/talentx-prep/

Personal target shortlist: https://collaboration95.github.io/talentx-prep/guru/#targets

The root URL is the shared classmate view. Personal CVs, fit notes, profile answers and the suggested route appear only at https://collaboration95.github.io/talentx-prep/guru/. Both views keep the same expo, research, schedule and general preparation tools. Their notes and offline download lists are separate; the shared entry does not load the personal data bundle. The personal route retains the original browser notes key.

A buildless mobile website for NUS-ISS TalentXperience on **23 October 2026**. The illustrated expo uses the supplied briefing’s actual rooms and floors; booth positions are illustrative.

## Included

- 18 company briefs with official websites, careers routes, cited research and timestamps.
- Vacancy status separated into verified vacancy, unverified lead, role card, and closed listing. A verified vacancy is not a guarantee of eligibility.
- Registration, all eight sharing sessions, 16 booths, a suggested route and physical-passport reminders.
- Local notes, bookmarks, passport/checklist progress, notes export/import, and optional offline saving.
- Shared preparation prompts and Guruprasath Gopal’s clearly labelled personal kit: 18 two-page tailored PDFs, editable Markdown, provenance, and a ZIP download.
- Bundled Kalam/Nunito fonts with OFL licences. No analytics, remote scripts or account requirement.

The two original supplied event PDFs and the reference screenshot are **not committed or published**. Their extracted text, reference renders and QA files remain in ignored `.local/`. Event facts are recorded in `data/event.json`; research sources are linked in each company brief. The latest supplied student briefing is used for the timetable because the public event page lists a different programme. Confirm signage at the event. The briefing’s final “12:00 AM” is displayed as midday within its stated morning event.

## Run locally

Open `index.html` directly for the guide, or use a local static server for service-worker support:

```sh
python3 -m http.server 8765 --directory .
```

Open http://localhost:8765. GitHub Pages serves the repository root; `.nojekyll` disables Jekyll processing. There is no framework build or dependency installation.

## Update site data

Edit the relevant company record in `research/`, then:

```sh
python3 scripts/build_site.py
python3 scripts/check_site.py
node --check app.js
node --check sw.js
node scripts/check_offline.cjs
```

The site build and checks use only Python’s standard library. They merge the checked-in research, validate the resume hashes, create the CV ZIP, and rebuild `data.js` and `sw.js`. Everything required to serve or rebuild the website is in this folder. Do not add `.local/` to Git.

`scripts/build_resumes.py` is the historical authoring helper for the registered applyd workspace, using its current master, project catalog and release registry. Rebuilding or replacing application resumes requires that workspace and its release workflow. The delivered PDF/Markdown/provenance snapshots are self-contained; serving the site does not require applyd. Preserve released files and create a new dated revision for future changes.

## Personal information and notes

The owner explicitly authorised sharing derived event information and personal resume materials. Personal CVs and saved answers are labelled as Guru’s rather than templates for classmates. Notes entered by visitors are stored only in their own browser. Export before changing devices or clearing site data; import replaces that browser’s saved progress. Never commit exported visitor notes.

Offline support saves the application shell automatically. Use **Prep kit → Save guide offline** in the shared view, or **Save guide + CVs offline** under `/guru/` to include personal downloads on that device. External career portals require internet. Offline data can be removed by the browser; downloaded files and exported notes provide independent backups.

Research checked on 22 October 2026, Asia/Singapore (UTC+08:00). Listings can close or change; follow the source before applying. No applications or employer messages are sent by this website.
