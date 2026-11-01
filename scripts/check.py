#!/usr/bin/env python3
"""Stdlib package checks; never installs or runs the authoring model."""
import argparse
import hashlib
import html
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Deck(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.keys, self.slides, self.network_assets = [], [], [], []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if "data-edit" in attrs:
            self.keys.append(attrs["data-edit"])
        if tag == "section" and "slide" in attrs.get("class", "").split():
            self.slides.append(attrs.get("id"))
        if tag in ("script", "img", "iframe", "audio", "video", "source", "link"):
            value = attrs.get("src") or attrs.get("href") or ""
            if value.startswith(("https:", "http:", "//")):
                self.network_assets.append(value)

def run(build=False):
    checks = []
    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})
    c = json.loads((ROOT / "capability.json").read_text())
    skill = ROOT / c["portable_method"]["path"]
    check("one canonical skill", list((ROOT / "skills").rglob("SKILL.md")) == [skill / "SKILL.md"])
    check("manifest identity and portable folder agree", c["id"] == skill.name == c["portable_method"]["name"] and c["name"] == "amplifier-capability-" + c["id"])
    check("manifest declares callable skill", c["kind"] == "skill" and c["engine"] == "LLM" and c["contract_version"] == "amplifier-capability/v1")
    check("portable rights notice travels with method", (skill / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes())
    for p in skill.rglob("*.md"):
        for dest in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", p.read_text()):
            if not dest.startswith(("http:", "https:", "#")):
                check("local reference exists: " + str(p.relative_to(skill)) + ":" + dest, (p.parent / dest.split("#")[0]).is_file())
    for name in ["skills/idea-talks/assets/template.html", "evals/dev/repair-club-talk.html"]:
        p = ROOT / name
        d = Deck()
        d.feed(p.read_text())
        check(name + ": unique slide IDs", len(d.ids) == len(set(d.ids)) and len(d.slides) == 9)
        check(name + ": unique editable keys", len(d.keys) == len(set(d.keys)) and len(d.keys) > 0)
        check(name + ": no remote runtime assets", not d.network_assets)
    check("no local-source absolute paths in portable payload", not any("/Users/" in p.read_text() for p in skill.rglob("*") if p.is_file() and p.suffix in (".md", ".html", ".json")))
    check("no env or private working files in portable payload", not any(p.name.startswith(".env") or ".research" in p.parts for p in skill.rglob("*")))
    report = {"checks": checks, "passed": all(x["passed"] for x in checks), "scope": "Static package/contract conformance; browser and model behavior are separate."}
    if build and report["passed"]:
        site = ROOT / "site"
        site.mkdir(exist_ok=True)
        shutil.copyfile(skill / "assets/template.html", site / "template.html")
        shutil.copyfile(ROOT / "docs/workflow.svg", site / "workflow.svg")
        (site / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Idea Talks guide</title><style>body{max-width:1000px;margin:50px auto;padding:0 24px;font:18px/1.6 Arial;color:#233d4b;background:#edf4f7}img{width:100%;height:auto}a{color:#216e67}</style><h1>Idea Talks</h1><p>' + html.escape(c["promise"]) + '</p><img src="workflow.svg" alt="Evidence to claim ledger, story spine, HTML draft and human review"><p><a href="template.html">Open the authoring template</a></p><p>MIT-licensed method and newly authored offline HTML editor. The template is a starting composition, not a completed talk. No publishing, provider configuration or dependency installation is included.</p></html>')
        report["build"] = {"template_sha256": hashlib.sha256((site / "template.html").read_bytes()).hexdigest()}
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--build", action="store_true")
    raise SystemExit(run(p.parse_args().build))
