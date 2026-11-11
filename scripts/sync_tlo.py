#!/usr/bin/env python3
"""Screen official 90R captions, preserve tracked bills, and refresh their text.

No API key or paid service. Uses Python's standard library and curl.
Never replaces a valid snapshot after an incomplete report fetch.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dist/data/bills.json"
SESSION = "90R"
BASE = "https://capitol.texas.gov"
RULES = {
    "Religious exercise": r"religio\w*|free exercise|faith[- ]based|conscience|sectarian|chaplain\w*|prayer|ten commandments",
    "Schools & education": r"education savings|private school\w*|religious instruction|school prayer|ten commandments|chaplain\w*",
    "Equal treatment": r"discriminat\w*|religious test\w*|equal protection",
    "Worship & land use": r"place\w* of worship|church\w*|mosque\w*|synagogue\w*|cemeter\w*|burial|municipal utility district\w*",
    "Conscience & licensing": r"conscience|sincerely held|religious belief\w*|religious exemption\w*",
    "Faith communities": r"muslim\w*|islam\w*|sharia\w*|jewish|juda\w*|christian\w*|sikh\w*|hindu\w*|buddhis\w*|antisemiti\w*|anti-semiti\w*|foreign law\w*",
}

def clean(value):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", value)).split())

def fetch(url):
    if not url.startswith(BASE + "/"):
        raise ValueError("Only official TLO URLs may be fetched")
    result = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", "35", "--retry", "1", url], capture_output=True, check=True)
    raw = result.stdout
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")

def parse_report(body, session=SESSION):
    if f"{session[:2]}th Legislature Regular Session" not in clean(body):
        raise ValueError("Wrong or missing session in report; old snapshot preserved")
    expected = re.search(r"Number of Bills:\s*([\d,]+)", body)
    if not expected:
        raise ValueError("Report has no bill count")
    bills = []
    for row in re.split(r'<div\s+class="row"\s*>', body)[1:]:
        vals = [clean(x) for x in re.findall(r'<div[^>]*>(.*?)</div>', row, re.S)]
        match = re.fullmatch(r"(HB|SB|HJR|SJR|HCR|SCR|HR|SR)\s+(\d+)", vals[0]) if vals else None
        if not match:
            continue
        def field(name):
            for i, val in enumerate(vals[:-1]):
                if val.replace(" ", "").rstrip(":").lower() == name.lower():
                    return vals[i + 1]
            return ""
        bill_id = "".join(match.groups())
        caption, author, action = field("Caption"), field("Author"), field("LastAction")
        if not caption or not author or not re.match(r"\d{2}/\d{2}/\d{4}", action):
            raise ValueError(f"Incomplete report record: {bill_id}")
        date = dt.datetime.strptime(action[:10], "%m/%d/%Y").date().isoformat()
        bills.append({"id":bill_id,"number":f"{match[1]} {int(match[2])}","type":match[1],"chamber":"House" if match[1].startswith("H") else "Senate", "caption":caption,"author":author,"lastAction":action[11:],"actionDate":date,"historyUrl":f"{BASE}/BillLookup/History.aspx?LegSess={session}&Bill={bill_id}","textPageUrl":f"{BASE}/BillLookup/Text.aspx?LegSess={session}&Bill={bill_id}"})
    if len(bills) != int(expected[1].replace(",", "")) or len({b['id'] for b in bills}) != len(bills):
        raise ValueError(f"Report count mismatch: {len(bills)} vs {expected[1]}")
    return bills

def classify(caption):
    return [topic for topic, rule in RULES.items() if re.search(r"\b(?:" + rule + r")\b", caption, re.I)]

def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def guard_review(bill):
    if (bill.get("reviewState") == "Text reviewed" and bill.get("textUrl") and bill.get("textHash")
            and (bill.get("textUrl") != bill.get("reviewedTextUrl") or bill.get("textHash") != bill.get("reviewedTextHash"))):
        bill.update(reviewState="Text changed · review needed",summary=None,relevance=None)

def text_update(bill):
    """Read the text tab to find the newest version, rather than guessing a suffix."""
    try:
        page = fetch(bill["textPageUrl"])
        pattern = r'href=["\']([^"\']*/tlodocs/90R/billtext/html/[^"\']+)["\']'
        urls = [html.unescape(u) for u in re.findall(pattern, page, re.I)]
        if not urls:
            raise ValueError("No official HTML text version located")
        # TLO lists versions in legislative order. The final HTML link is newest.
        url = urls[-1]
        if url.startswith("/"): url = BASE + url
        url = url.replace("http://", "https://", 1)
        text = clean(fetch(url))
        if len(text) < 100 or not re.search(r"90(?:R|\(R\)|th)", text, re.I):
            raise ValueError("Unexpected text response")
        return {"textUrl":url,"textHash":hashlib.sha256(text.encode()).hexdigest(),"textCheckedAt":NOW,"textFetchError":None}
    except Exception as exc:
        return {"textFetchError":type(exc).__name__,"textAttemptedAt":NOW}

def run(args):
    previous = load_json(DATA, {"bills":[],"changes":[]})
    prior = {b["id"]:b for b in previous["bills"]}
    editorial = load_json(ROOT / "editorial.json", {})
    reports = []
    all_bills = []
    for chamber in ["house", "senate"]:
        url = f"{BASE}/reports/Report.aspx?LegSess={SESSION}&ID={chamber}filed"
        raw = (Path(args.reports) / f"{chamber}.html").read_text() if args.reports else fetch(url)
        records = parse_report(raw)
        reports.append({"label":f"Filed {chamber.title()} legislation","url":url,"records":len(records),"checkedAt":NOW})
        all_bills.extend(records)
    if not all_bills:
        raise ValueError("No bill records returned")
    # A sharp regression may be a partial upstream response; never erase the snapshot.
    if len(all_bills) < previous.get("screenedCount", 0) * .9:
        raise ValueError("Report coverage fell by more than 10%; review before publishing")
    tracked = []
    changes = previous.get("changes", [])
    for bill in all_bills:
        key = bill["id"]
        topics = classify(bill["caption"])
        edit = editorial.get(key, {})
        if edit.get("exclude"):
            continue
        if not (topics or key in prior or edit.get("include")):
            continue
        old = prior.get(key, {})
        merged = {**old, **bill,"topics":edit.get("topics", topics or old.get("topics",[])),"sourceCheckedAt":NOW,"firstSeen":old.get("firstSeen",NOW),"reviewState":"Caption screened","summary":None,"relevance":None, **{k:v for k,v in edit.items() if k not in ("include","exclude")}}
        if not old:
            changes.append({"id":key,"at":NOW,"kind":"Added to tracker","detail":bill["caption"]})
        elif bill["lastAction"] != old.get("lastAction") or bill["actionDate"] != old.get("actionDate"):
            changes.append({"id":key,"at":NOW,"kind":"Action changed","detail":bill["lastAction"]})
        tracked.append(merged)
    if args.text:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            updates = list(pool.map(text_update, tracked))
        for bill, update in zip(tracked, updates):
            old_hash = bill.get("textHash")
            bill.update(update)
            if old_hash and update.get("textHash") and old_hash != update["textHash"]:
                bill["reviewState"] = "Text changed · review needed"
                bill["summary"] = None
                bill["relevance"] = None
                bill["reviewedTextHash"] = None
                changes.append({"id":bill["id"],"at":NOW,"kind":"Bill text changed","detail":"Review the current official version before relying on a prior summary."})
            # A stored editorial note applies only to its reviewed version.
    for bill in tracked:
        guard_review(bill)
    tracked.sort(key=lambda b:(b["actionDate"],b["id"]),reverse=True)
    snapshot={"session":SESSION,"updatedAt":NOW,"screenedCount":len(all_bills),"coverage":"All filed House and Senate bill and resolution captions in the two official reports. Keyword screening, not a full-text census. Broad matches require review.","updateMode":"manual","reports":reports,"bills":tracked,"changes":changes[-500:]}
    DATA.parent.mkdir(parents=True,exist_ok=True)
    temp=DATA.with_suffix(".tmp")
    temp.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n")
    temp.replace(DATA)
    print(f"Screened {len(all_bills)} official captions; tracked {len(tracked)} measures; snapshot saved.")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--reports",help="Directory of saved official reports for reproducible ingestion")
    parser.add_argument("--text",action="store_true",help="Also retrieve latest text for tracked measures")
    args=parser.parse_args()
    NOW=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try: run(args)
    except Exception as exc:
        print(f"UPDATE FAILED. Existing snapshot preserved. {exc}",file=sys.stderr)
        sys.exit(1)
