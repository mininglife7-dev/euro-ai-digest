#!/usr/bin/env python3
"""EURO AI weekly re-scan digest (MIT). Standard library only.
Fetches the public catalogue and deadlines from unadhi.com, re-checks each vendor source URL,
diffs against state/, writes digests/YYYY-MM-DD.md (+ a ready-to-send e-mail body) and updates state/.
Holds NO subscriber data: sending is done outside this repo."""
import json, os, sys, datetime, urllib.request, urllib.error
BASE = os.environ.get("EUROAI_BASE", "https://unadhi.com/platform/")
ROOT = os.path.dirname(os.path.abspath(__file__))
def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (EURO AI weekly re-scan)"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read()
def status(url):
    try: return get(url)[0]
    except urllib.error.HTTPError as e: return e.code
    except Exception: return 0
def load(p, d):
    try: return json.load(open(os.path.join(ROOT, p)))
    except Exception: return d
def main(check_links=True):
    today = datetime.date.today().isoformat()
    cat = json.loads(get(BASE + "catalogue.json")[1]); dl = json.loads(get(BASE + "deadlines.json")[1])
    old_cat, old_dl = load("state/catalogue.json", {"vendors": []}), load("state/deadlines.json", {"deadlines": []})
    ov = {v["id"]: v for v in old_cat["vendors"]}; nv = {v["id"]: v for v in cat["vendors"]}
    added = [nv[k] for k in nv if k not in ov]; removed = [ov[k] for k in ov if k not in nv]
    changed = [nv[k] for k in nv if k in ov and (nv[k]["ai"] != ov[k]["ai"] or nv[k]["src"] != ov[k]["src"])]
    od = {d["date"] + d["title"] for d in old_dl["deadlines"]}; nd = {d["date"] + d["title"] for d in dl["deadlines"]}
    dl_new = [d for d in dl["deadlines"] if d["date"] + d["title"] not in od]
    dl_gone = [d for d in old_dl["deadlines"] if d["date"] + d["title"] not in nd]
    upcoming = [d for d in dl["deadlines"] if 0 <= (datetime.date.fromisoformat(d["date"]) - datetime.date.today()).days <= 400]
    broken = [(v["name"], v["src"], s) for v in cat["vendors"] for s in [status(v["src"]) if check_links else 200] if s not in (200, 403, 429)]
    first = not old_cat["vendors"]
    L = [f"# EURO AI weekly re-scan: {today}", "", f"Catalogue: {len(cat['vendors'])} vendors (checked {cat.get('checked','?')}). Deadlines tracked: {len(dl['deadlines'])}.", ""]
    if first: L += ["First run: baseline stored, no diff yet.", ""]
    else:
        L += ["## Catalogue changes", *(["- none"] if not (added or removed or changed) else []),
              *[f"- NEW: {v['name']}: {v['ai']} ({v['src']})" for v in added], *[f"- REMOVED: {v['name']}" for v in removed],
              *[f"- UPDATED: {v['name']}: {v['ai']} ({v['src']})" for v in changed], "",
              "## Deadline changes", *(["- none"] if not (dl_new or dl_gone) else []),
              *[f"- NEW/CHANGED: {d['date']}: {d['title']} ({d.get('source','')})" for d in dl_new], *[f"- WITHDRAWN: {d['date']}: {d['title']}" for d in dl_gone], ""]
    L += ["## Coming up (next ~13 months)", *([f"- {d['date']}: {d['title']}" for d in upcoming] or ["- none"]), ""]
    L += ["## Vendor source links needing a look (internal)", *([f"- {n}: HTTP {s} {u}" for n, u, s in broken] or ["- none"]), ""]
    mail = "\n".join(L[:L.index("## Vendor source links needing a look (internal)")]) + \
        "\nRe-scan your own tool list: https://unadhi.com/platform/app/\n\nSuggestions only, not legal advice. Primary sources: EUR-Lex Reg. (EU) 2024/1689 and 2026/1744.\nYou get this because you opted in. To stop, reply with UNSUBSCRIBE.\n"
    os.makedirs(os.path.join(ROOT, "digests"), exist_ok=True)
    open(os.path.join(ROOT, "digests", today + ".md"), "w").write("\n".join(L) + "\n")
    open(os.path.join(ROOT, "digests", today + ".email.txt"), "w").write("Subject: EURO AI weekly re-scan " + today + "\n\n" + mail)
    open(os.path.join(ROOT, "digests", "LATEST.md"), "w").write("\n".join(L) + "\n")
    json.dump(cat, open(os.path.join(ROOT, "state/catalogue.json"), "w"), indent=1)
    json.dump(dl, open(os.path.join(ROOT, "state/deadlines.json"), "w"), indent=1)
    print("\n".join(L))
if __name__ == "__main__": main("--no-links" not in sys.argv)
