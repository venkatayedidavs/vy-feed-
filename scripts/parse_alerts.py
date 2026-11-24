#!/usr/bin/env python3
"""Turn LinkedIn job alert emails into entries in data/jobs.json.

Usage:
    python3 scripts/parse_alerts.py INBOX_DIR [--jobs data/jobs.json] [--dry-run]

INBOX_DIR holds one JSON file per email, each with the Gmail fields
{"id", "date", "subject", "plaintextBody"}. Raw emails are never committed:
they carry tracking tokens. Only the parsed job details are kept.

Steps: parse every job card, keep jobs whose title and location match the
search preferences, drop job ids already in jobs.json, append the rest.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Stockholm")

TITLE_INCLUDE = re.compile(
    r"product\s+(manager|owner|lead|director|management)|head\s+of\s+product|"
    r"director\s+of\s+product|vp\s+(of\s+)?product|chief\s+product|"
    r"produktchef|produktägare|produktansvarig|produktejer",
    re.I,
)
TITLE_EXCLUDE = re.compile(r"\b(intern|internship|junior|trainee|graduate|student|sales)\b", re.I)

# Places that count as "in the search area" (lower case, matched as words).
SKANE = """malmö malmo lund helsingborg landskrona trelleborg ystad kristianstad hässleholm
ängelholm höganäs eslöv staffanstorp lomma burlöv arlöv vellinge svedala höör kävlinge bjuv
åstorp klippan skåne scania""".split()
GOTHENBURG = """gothenburg göteborg mölndal frölunda partille kungälv lerum härryda mölnlycke
landvetter torslanda hisings""".split()
COPENHAGEN = """copenhagen københavn kobenhavn frederiksberg taastrup herlev ballerup humlebæk lyngby
søborg bagsværd måløv hillerød glostrup brøndby hvidovre rødovre gentofte hellerup valby
albertslund ishøj kastrup tårnby hørsholm birkerød allerød farum værløse roskilde køge
helsingør greve dragør virum holte gladsaxe skovlunde vallensbæk nordhavn ørestad""".split()
AREA_WORDS = SKANE + GOTHENBURG + COPENHAGEN
REMOTE_COUNTRIES = ["sweden", "sverige", "denmark", "danmark", "stockholm", "emea", "europe", "nordics"]

VIEW_JOB = re.compile(r"View job:\s*https://www\.linkedin\.com/comm/jobs/view/(\d+)")
ALERT_HEADER = re.compile(r"^Your job alert for (.+?) in (.+)$")
OTHER_HEADER = re.compile(r"^(?:<[^>]+>)?(.+?)(?:</[^>]+>)?\s+jobs in (.+)$")
WORKPLACE = re.compile(r"\s*\((Remote|Hybrid|On-site)\)\s*$", re.I)
SEPARATOR = re.compile(r"^-{10,}$")


def has_word(text, words):
    low = text.lower()
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", low) for w in words)


def location_ok(location, workplace):
    if has_word(location, AREA_WORDS):
        return True
    return workplace == "Remote" and has_word(location, REMOTE_COUNTRIES)


def parse_email(msg):
    """Yield job dicts from one alert email."""
    body = msg.get("plaintextBody") or ""
    sent = datetime.fromisoformat(msg["date"].replace("Z", "+00:00")).astimezone(TZ)
    search = None
    paragraphs, current = [], []
    for line in body.splitlines():
        line = line.strip()
        if not line or SEPARATOR.match(line):
            if current:
                paragraphs.append(current)
            current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(current)

    prev = None
    for para in paragraphs:
        for line in para:
            m = ALERT_HEADER.match(line) or OTHER_HEADER.match(line)
            if m:
                search = m.group(2).strip()
        view = next((VIEW_JOB.search(l) for l in para if VIEW_JOB.search(l)), None)
        if view and prev and len(prev) >= 3:
            title, company, location = prev[-3:]
            wp = WORKPLACE.search(location)
            workplace = wp.group(1).title() if wp else ""
            location = WORKPLACE.sub("", location).strip()
            notes = "Easy Apply" if any("Apply with resume" in l for l in para) else ""
            yield {
                "id": view.group(1),
                "title": title,
                "company": company,
                "location": location,
                "workplace": workplace,
                "url": f"https://www.linkedin.com/jobs/view/{view.group(1)}/",
                "date_found": sent.strftime("%Y-%m-%d"),
                "search_location": search or "",
                "notes": notes,
            }
        prev = para


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inbox")
    ap.add_argument("--jobs", default=str(Path(__file__).resolve().parent.parent / "data" / "jobs.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jobs_path = Path(args.jobs)
    feed = json.loads(jobs_path.read_text(encoding="utf-8"))
    seen = {j["id"] for j in feed["jobs"]}

    msgs = []
    for f in sorted(Path(args.inbox).glob("*.json")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                msgs.append(json.loads(line))
    msgs.sort(key=lambda m: m["date"])

    added, skipped = [], []
    for msg in msgs:
        for job in parse_email(msg):
            if job["id"] in seen:
                continue
            seen.add(job["id"])
            if not TITLE_INCLUDE.search(job["title"]) or TITLE_EXCLUDE.search(job["title"]):
                skipped.append((job, "title"))
            elif not location_ok(job["location"], job["workplace"]):
                skipped.append((job, "location"))
            else:
                added.append(job)

    for job in added:
        print(f"ADD   {job['date_found']}  {job['title']} | {job['company']} | {job['location']} {job['workplace']}")
    for job, why in skipped:
        print(f"SKIP  ({why})  {job['title']} | {job['company']} | {job['location']}")
    print(f"{len(msgs)} emails, {len(added)} new jobs, {len(skipped)} skipped")

    if added and not args.dry_run:
        feed["jobs"].extend(added)
        feed["updated"] = datetime.now(timezone.utc).astimezone(TZ).isoformat(timespec="minutes")
        jobs_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
