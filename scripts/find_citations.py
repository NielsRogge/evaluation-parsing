import requests
import json
import os
import time

API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
if not API_KEY:
    with open("keys.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()
    API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

PAPER_ID = "ARXIV:2501.00321"
BASE_URL = f"https://api.semanticscholar.org/graph/v1/paper/{PAPER_ID}/citations"

headers = {"x-api-key": API_KEY}
fields = "title,authors,year,venue,externalIds,url,citationCount,publicationDate"

all_citations = []
offset = 0
limit = 1000

while True:
    params = {"fields": fields, "offset": offset, "limit": limit}
    print(f"Fetching citations offset={offset} ...")
    resp = requests.get(BASE_URL, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    batch = data.get("data", [])
    if not batch:
        break

    all_citations.extend(batch)
    print(f"  Got {len(batch)} citations (total so far: {len(all_citations)})")

    if "next" not in data:
        break
    offset = data["next"]
    time.sleep(0.5)

print(f"\nTotal citing papers: {len(all_citations)}\n")
print(f"{'#':<4} {'Year':<6} {'Title':<90} {'Venue':<30} {'Citations'}")
print("-" * 140)

sorted_citations = sorted(
    all_citations,
    key=lambda c: (c["citingPaper"].get("year") or 0, c["citingPaper"].get("citationCount") or 0),
    reverse=True,
)

for i, citation in enumerate(sorted_citations, 1):
    paper = citation["citingPaper"]
    title = (paper.get("title") or "N/A")[:88]
    year = paper.get("year") or "N/A"
    venue = (paper.get("venue") or "")[:28]
    cite_count = paper.get("citationCount", 0)
    authors = ", ".join(a["name"] for a in (paper.get("authors") or [])[:3])
    if len(paper.get("authors") or []) > 3:
        authors += " et al."
    arxiv_id = (paper.get("externalIds") or {}).get("ArXiv", "")
    s2_url = paper.get("url", "")

    print(f"{i:<4} {year:<6} {title:<90} {venue:<30} {cite_count}")
    print(f"     Authors: {authors}")
    if arxiv_id:
        print(f"     arXiv: https://arxiv.org/abs/{arxiv_id}")
    elif s2_url:
        print(f"     S2: {s2_url}")
    print()

with open("citations_ocrbench_v2.json", "w") as f:
    json.dump({"total": len(all_citations), "citations": sorted_citations}, f, indent=2)

print(f"Full results saved to citations_ocrbench_v2.json")
