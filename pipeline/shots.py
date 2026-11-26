"""Moving-shot generator (Wan 2.2 TI2V-5B / HunyuanVideo 1.5) with SHA-256 caching and Ken Burns fallback."""

from __future__ import annotations

import argparse

from pipeline.utils import STORYBOARD_PATH, load_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate moving video shots with SHA-256 caching.")
    parser.add_argument("--shot", help="Optional single shot ID (e.g. shot_01) to regenerate.")
    args = parser.parse_args(argv)

    storyboard = load_json(STORYBOARD_PATH)
    shots = storyboard.get("shots", [])
    selected = [s for s in shots if not args.shot or s["id"] == args.shot]
    print(
        f"pipeline.shots scaffold ready ({len(selected)} shot(s) targeted) — "
        "awaiting Step 5 moving-shot generation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
