from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def http_get_json(url: str, timeout_s: int = 10) -> dict:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate REAL sample outputs for README")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    ap.add_argument("--gs-id", type=int, default=1, help="Ground station id to query")
    ap.add_argument("--hours", type=int, default=24, help="Window length (<= 168 hours)")
    ap.add_argument("--metric", default="duration", choices=["duration", "max_elev"])
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--out", default="SAMPLE_OUTPUTS.md", help="Output markdown file (repo root)")
    ap.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds")
    args = ap.parse_args()

    if args.hours <= 0:
        print("[error] --hours must be > 0")
        sys.exit(2)
    if args.hours > 168:
        print("[error] --hours must be <= 168 (7 days)")
        sys.exit(2)

    start = utcnow()
    end = start + timedelta(hours=args.hours)

    start_iso = start.isoformat()
    end_iso = end.isoformat()

    base = args.base_url.rstrip("/")

    passes_url = f"{base}/passes?" + urlencode(
        {"gs_id": args.gs_id, "start": start_iso, "end": end_iso, "limit": 50}
    )
    best_url = f"{base}/schedule/best?" + urlencode(
        {"gs_id": args.gs_id, "start": start_iso, "end": end_iso, "metric": args.metric}
    )
    top_url = f"{base}/schedule/top?" + urlencode(
        {"gs_id": args.gs_id, "start": start_iso, "end": end_iso, "metric": args.metric, "k": args.k}
    )

    print("[info] Calling endpoints:")
    print("  ", passes_url)
    print("  ", best_url)
    print("  ", top_url)

    try:
        passes_json = http_get_json(passes_url, timeout_s=args.timeout)
        best_json = http_get_json(best_url, timeout_s=args.timeout)
        top_json = http_get_json(top_url, timeout_s=args.timeout)
    except Exception as e:
        print("\n[error] Could not fetch from API.")
        print("Make sure the server is running:")
        print("  py -3.12 -m uvicorn app.main:app --reload\n")
        print("If passes are empty, generate them first:")
        print("  py -3.12 -m app.scripts.fetch_tles")
        print("  py -3.12 -m app.scripts.generate_passes_7d_batched --days 2 --gs-limit 50 --sat-limit 30 --chunk-hours 24 --step 60 --delete-existing\n")
        print("Error:", repr(e))
        sys.exit(1)

    repo_root = Path(__file__).resolve().parents[2]  # .../app/scripts -> repo root
    out_path = (repo_root / args.out).resolve()

    md = []
    md.append("# Sample Outputs (Real)\n")
    md.append(
        f"Generated at: `{utcnow().isoformat()}`\n\n"
        f"Window: `{start_iso}` → `{end_iso}` (gs_id={args.gs_id})\n\n"
        f"> Note: Results depend on your DB contents (TLEs + generated passes).\n"
    )

    def section(title: str, url: str, payload: dict) -> None:
        md.append(f"\n## {title}\n")
        md.append(f"Request:\n\n`{url}`\n")
        md.append("\nResponse:\n\n```json\n")
        md.append(json.dumps(payload, indent=2))
        md.append("\n```\n")

    section("/passes", passes_url, passes_json)
    section("/schedule/best", best_url, best_json)
    section("/schedule/top", top_url, top_json)

    out_path.write_text("".join(md), encoding="utf-8")
    print(f"\n[done] Wrote: {out_path}")


if __name__ == "__main__":
    main()
