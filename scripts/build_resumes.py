#!/usr/bin/env python3
"""Build, inspect, then release the TalentXperience company resume downloads.

Run `--stage build`, visually inspect every PNG in the printed QA directory,
and record the inspected candidate hashes in qa-approval.json before `--stage
release`. Workspace helpers own draft provenance, release validation and resume
selection. This script only renders those drafts and packages exact releases.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import fitz


ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "talentx-prep"
OUTPUT = PREP / "resumes"
QA = PREP / ".local" / "resume-qa"
DATE = "2026-10-22"
MASTER_SCOPE = "master"
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
FONT_FILES = {"regular": "Arial.ttf", "bold": "Arial Bold.ttf"}
FONTS = {name: fitz.Font(fontfile=str(FONT_DIR / filename)) for name, filename in FONT_FILES.items()}
INK = (0.12, 0.16, 0.21)
ACCENT = (0.12, 0.25, 0.36)
MUTED = (0.34, 0.38, 0.43)

# The order and two-bullet limit are the complete factual tailoring operation.
COMPANIES = [
    ("1fss", "1FSS", ["researchagent", "talktoit", "hr-2026"], "Payment investigation, data ingestion and compact analytical queries."),
    ("ailytics", "Ailytics", ["fitback", "talktoit", "findmycar"], "Computer vision, data pipelines and live sensor dashboards."),
    ("ajentik-ai", "Ajentik AI", ["researchagent", "common-grounds-makeathon", "talktoit"], "Tool-using research agents, validated generation and conversational analytics."),
    ("cygnus-med", "Cygnus Med", ["fitback", "talktoit", "findmycar"], "Image-based measurements, health-data processing and connected-device software."),
    ("dhl-express", "DHL Express", ["hr-2026", "findmycar", "talktoit"], "Geospatial queries, live vehicle status and reliable data ingestion."),
    ("fano-labs", "Fano Labs", ["researchagent", "talktoit", "common-grounds-makeathon"], "Grounded research agents, natural-language analytics and real-time interactions."),
    ("julius-baer", "Julius Baer", ["researchagent", "hr-2026", "talktoit"], "Payment investigation, analytical queries and structured data pipelines."),
    ("keysight-technologies", "Keysight Technologies", ["findmycar", "hr-2026", "ss-dcl"], "Connected-device software, efficient queries and cached image matching."),
    ("mediacorp", "Mediacorp", ["common-grounds-makeathon", "researchagent", "talktoit"], "Audience-driven interactive experiences, research agents and analytics interfaces."),
    ("national-dental-centre-singapore", "National Dental Centre Singapore", ["talktoit", "researchagent", "fitback"], "Health analytics, grounded research workflows and image-based measurements."),
    ("octomate", "Octomate", ["ss-dcl", "talktoit", "common-grounds-makeathon"], "Productivity workflows, full-stack analytics and agent-driven interactions."),
    ("rezonate", "Rezonate", ["researchagent", "talktoit", "common-grounds-makeathon"], "Grounded retrieval and tool-using agents, health analytics and validated code generation for AI healthcare workflows."),
    ("sap-fioneer", "SAP Fioneer", ["researchagent", "talktoit", "hr-2026"], "Payment-investigation agents, structured ingestion and analytical decision layers."),
    ("smrt", "SMRT", ["findmycar", "hr-2026", "talktoit"], "Live vehicle dashboards, geospatial queries and operational data pipelines."),
    ("singlife", "Singlife", ["researchagent", "talktoit", "hr-2026"], "Grounded payment investigation, health analytics and compact decision layers."),
    ("trainocate", "Trainocate", ["talktoit", "common-grounds-makeathon", "findmycar"], "Full-stack analytics, agent applications and AWS-connected IoT software."),
    ("trampolene", "Trampolene", ["talktoit", "fitback", "common-grounds-makeathon"], "Health-data interfaces, image-based measurements and interactive applications."),
    ("yokogawa-engineering", "Yokogawa Engineering", ["hr-2026", "findmycar", "talktoit"], "Efficient decision queries, sensor integration and reliable data processing."),
]


def now():
    return datetime.now(ZoneInfo("Asia/Singapore")).isoformat()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def helper(script, *args):
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--workspace", str(ROOT), *args],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def resolve(scope, purpose):
    return helper("resolve_resume.py", "--scope", scope, "--purpose", purpose)


def plain(text):
    # Link labels stay faithful; deliberately create no PDF link annotations.
    return re.sub(r"\[([^\]]+)\]\([^\n]*?\)", r"\1", text)


def tokens(text):
    # Use the workspace implementation rather than duplicate its release rule.
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from workspace import text_tokens
    return text_tokens(text)


def wrap(text, width, size, font):
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if FONTS[font].text_length(candidate, fontsize=size) <= width:
            current = candidate
        else:
            if not current or FONTS[font].text_length(word, fontsize=size) > width:
                raise ValueError(f"Cannot wrap token: {word}")
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render(markdown, target, company):
    document = fitz.open()
    page = None
    y = 0
    margin = 44
    width, height = fitz.paper_size("a4")
    content_width = width - margin * 2
    bounds = []
    section = ""

    def new_page():
        nonlocal page, y
        page = document.new_page(width=width, height=height)
        for font, filename in FONT_FILES.items():
            page.insert_font(fontname=font, fontfile=str(FONT_DIR / filename))
        y = margin

    def block(text, size=10.5, leading=14.1, font="regular", color=INK, indent=0, after=3, bullet=False):
        nonlocal y
        text = plain(text)
        lines = wrap(text, content_width - indent, size, font)
        # fitz point coordinates are baselines; preserve a full font ascender.
        baseline = y + FONTS[font].ascender * size
        for index, line in enumerate(lines):
            page.insert_text((margin + indent, baseline + index * leading), line,
                             fontsize=size, fontname=font, color=color)
        if bullet:
            page.draw_circle((margin + 3, baseline - size * 0.32), 1.15, color=ACCENT, fill=ACCENT)
        y += len(lines) * leading + after
        if y > height - margin:
            raise ValueError(f"{company}: page {len(document)} overflows at {text[:60]} ({y:.1f})")
        bounds.append({"page": len(document), "bottom": round(y, 2), "text": text[:80]})

    new_page()
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "## Projects":
            new_page()
        if line.startswith("# "):
            block(line[2:], size=23, leading=29, font="bold", color=ACCENT, after=4)
        elif line.startswith("## "):
            section = line[3:]
            y += 9 if section != "Projects" else 0
            block(section, size=12, leading=17, font="bold", color=ACCENT, after=5)
            page.draw_line((margin, y - 3), (width - margin, y - 3), color=(0.77, 0.81, 0.84), width=0.55)
        elif line.startswith("### "):
            y += 4
            block(line[4:], size=10.8, leading=13.4, font="bold", after=2)
        elif line.startswith("- "):
            block(line[2:], indent=12, bullet=True, after=3)
        elif not section:
            block(line, size=9.3, leading=12.3, color=MUTED, after=3)
        elif re.match(r"^(January|February|March|April|May|June|July|August|September|October|November|December) \d{4} - ", line):
            block(line, size=9.8, leading=12.8, color=MUTED, after=3)
        else:
            block(line, after=4)

    document.set_metadata({"title": f"Guruprasath Gopal - {company}", "author": "Guruprasath Gopal",
                           "subject": "TalentXperience company-tailored resume", "creator": "applyd deterministic draft renderer"})
    document.subset_fonts()
    target.parent.mkdir(parents=True, exist_ok=True)
    document.save(target, garbage=4, deflate=True, no_new_id=True)
    document.close()
    extracted = subprocess.run(["pdftotext", "-layout", str(target), "-"], check=True, capture_output=True, text=True).stdout
    if tokens(markdown) != tokens(extracted):
        raise ValueError(f"{company}: rendered PDF text does not match helper draft")
    with fitz.open(target) as pdf:
        if len(pdf) != 2 or any(list(p.links()) for p in pdf):
            raise ValueError(f"{company}: expected two pages with no credential link annotations")
        for page in pdf:
            for word in page.get_text("words"):
                if word[0] < margin - 1 or word[2] > width - margin + 1 or word[1] < margin - 1 or word[3] > height - margin + 1:
                    raise ValueError(f"{company}: text outside page content box: {word}")
    return {"page_count": 2, "sha256": sha256(target), "body_font_pt": 10.5,
            "content_bottoms": [max(b["bottom"] for b in bounds if b["page"] == p) for p in (1, 2)],
            "text_matches_draft": True, "credential_hyperlinks": False}


def previews(state):
    images = QA / "pages"
    images.mkdir(parents=True, exist_ok=True)
    for item in state["companies"]:
        with fitz.open(item["candidate"]) as pdf:
            for number, page in enumerate(pdf, 1):
                page.get_pixmap(dpi=144).save(images / f"{item['company_id']}-p{number}.png")
    for index in range(0, len(state["companies"]), 2):
        sheet = fitz.open()
        page = sheet.new_page(width=1200, height=1740)
        for row, item in enumerate(state["companies"][index:index + 2]):
            with fitz.open(item["candidate"]) as pdf:
                for col in range(2):
                    left, top = col * 600, row * 870
                    page.insert_text((left + 12, top + 17), f"{item['company_id']} | page {col + 1}", fontsize=12)
                    page.show_pdf_page(fitz.Rect(left + 6, top + 25, left + 594, top + 857), pdf, col)
        page.get_pixmap().save(QA / f"contact-sheet-{index // 2 + 1:02}.png")
        sheet.close()


def build():
    QA.mkdir(parents=True, exist_ok=True)
    names = read(PREP / "research" / "brief.json")["companies"]
    if names != [c[1] for c in COMPANIES]:
        raise ValueError("Company names/order differ from the task brief")
    presets_path = ROOT / "resumes" / "presets.json"
    presets = read(presets_path)
    snapshot = QA / "original-registry.json"
    if not snapshot.exists():
        write(snapshot, read(ROOT / "resumes" / "registry.json"))
        write(QA / "original-presets.json", presets)
    for slug, _, projects, _ in COMPANIES:
        name = f"talentx-{slug}"
        setting = {"projects": projects, "bullets_per_project": 2}
        if name in presets and presets[name] != setting:
            raise ValueError(f"Existing preset differs: {name}")
        presets[name] = setting
    write(presets_path, presets)
    state = {"built_at": now(), "companies": []}
    for slug, name, projects, note in COMPANIES:
        scope = f"talentx-{slug}"
        # Resolve immediately before every deterministic draft, never from a name.
        master = resolve(MASTER_SCOPE, "reference")
        draft = helper("workspace.py", "draft", "--preset", scope)
        manifest = read(Path(draft["manifest"]))
        if manifest["source_master_id"] != master["id"] or manifest["source_master_sha256"] != master["sha256"]:
            raise ValueError("Master changed during drafting")
        candidate = QA / "candidates" / f"{slug}.pdf"
        layout = render(Path(draft["draft"]).read_text(), candidate, name)
        state["companies"].append({"company_id": slug, "company_name": name, "scope": scope,
            "projects": projects, "tailoring_note": note, "release_id": f"{scope}-{DATE}-v1",
            "master": master, **draft, "candidate": str(candidate), **layout})
    write(QA / "build-state.json", state)
    previews(state)
    print(json.dumps({"built": len(state["companies"]), "page_count": sum(c["page_count"] for c in state["companies"]),
                      "qa_directory": str(QA), "content_bottoms": {c["company_id"]: c["content_bottoms"] for c in state["companies"]}}, indent=2))


def package():
    state = read(QA / "build-state.json")
    approval = read(QA / "qa-approval.json")
    if not approval.get("all_pages_visually_inspected"):
        raise ValueError("Visual inspection of every final page is required before release")
    index = []
    for item in state["companies"]:
        slug = item["company_id"]
        candidate = Path(item["candidate"])
        if sha256(candidate) != item["sha256"] or approval["inspected_pdf_hashes"].get(slug) != item["sha256"]:
            raise ValueError(f"Candidate changed after visual inspection: {slug}")
        registry = read(ROOT / "resumes" / "registry.json")
        matches = [r for r in registry["releases"] if r["id"] == item["release_id"]]
        if not matches:
            helper("workspace.py", "release", "--file", str(candidate), "--id", item["release_id"],
                   "--scope", item["scope"], "--purpose", "application", "--manifest", item["manifest"],
                   "--note", f"TalentXperience: {item['company_name']}. {item['tailoring_note']} Two-page PDF inspected; faithful helper draft; credential links disabled.")
        registry = read(ROOT / "resumes" / "registry.json")
        release = next(r for r in registry["releases"] if r["id"] == item["release_id"])
        OUTPUT.mkdir(parents=True, exist_ok=True)
        pdf = OUTPUT / f"{slug}.pdf"
        # Resolve immediately before copying the exact current release bytes.
        selected = resolve(item["scope"], "application")
        if selected["id"] != item["release_id"] or selected["sha256"] != item["sha256"]:
            raise ValueError(f"Unexpected current company release: {slug}")
        shutil.copyfile(selected["path"], pdf)
        markdown = OUTPUT / f"{slug}.md"
        shutil.copyfile(item["draft"], markdown)
        master_path = OUTPUT / "sources" / f"{item['master']['id']}.md"
        master_path.parent.mkdir(parents=True, exist_ok=True)
        if master_path.exists() and sha256(master_path) != item["master"]["sha256"]:
            raise ValueError("Packaged source master differs from immutable original")
        if not master_path.exists():
            shutil.copyfile(item["master"]["path"], master_path)
        if sha256(master_path) != item["master"]["sha256"] or sha256(markdown) != release["draft_provenance"]["sha256"] or sha256(pdf) != selected["sha256"]:
            raise ValueError("Packaged artifact hash mismatch")
        manifest = {**release["draft_provenance"], "path": markdown.name}
        packaged_release = {**release, "path": pdf.name, "draft_provenance": manifest}
        provenance = OUTPUT / f"{slug}.provenance.json"
        write(provenance, {"schema_version": 1, "company_id": slug, "company_name": item["company_name"],
            "path_base": ".", "packaged_at": now(), "source_master_id": item["master"]["id"],
            "source_master_sha256": item["master"]["sha256"],
            "source_master": {"id": item["master"]["id"], "path": str(master_path.relative_to(OUTPUT)), "sha256": item["master"]["sha256"]},
            "pdf": {"path": pdf.name, "sha256": selected["sha256"], "page_count": item["page_count"]},
            "markdown": {"path": markdown.name, "sha256": sha256(markdown)},
            "draft_manifest": manifest, "release": packaged_release,
            "release_id": selected["id"], "review_due_at": release["review_due_at"],
            "selected_projects": release["selected_projects"], "tailoring_note": item["tailoring_note"],
            "verification": {"text_matches_helper_draft": True, "all_pages_visually_inspected": True,
                             "credential_hyperlinks": False, "resolved_before_copy": True}})
        index.append({"company_id": slug, "company_name": item["company_name"],
            "pdf": str(pdf.relative_to(PREP)), "markdown": str(markdown.relative_to(PREP)),
            "provenance": str(provenance.relative_to(PREP)), "scope": item["scope"],
            "release_id": selected["id"], "source_master_id": item["master"]["id"],
            "sha256": selected["sha256"], "review_due_at": release["review_due_at"],
            "projects": item["projects"], "tailoring_note": item["tailoring_note"]})
    original = read(QA / "original-registry.json")["releases"]
    current = read(ROOT / "resumes" / "registry.json")["releases"]
    if any(entry not in current for entry in original):
        raise ValueError("A pre-existing registry entry was modified")
    for name, setting in read(QA / "original-presets.json").items():
        if read(ROOT / "resumes" / "presets.json").get(name) != setting:
            raise ValueError("A pre-existing preset was modified")
    write(OUTPUT / "index.json", index)
    print(json.dumps({"released": len(index), "page_count": 2 * len(index), "index": str(OUTPUT / "index.json"),
                      "preserved_existing_registry_entries": len(original), "releases": index}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("build", "release"), required=True)
    args = parser.parse_args()
    if args.stage == "build":
        build()
    else:
        package()
