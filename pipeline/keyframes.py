"""Reference sheet and per-shot keyframe generator (FLUX.2 klein / FLUX.1 schnell)."""

from __future__ import annotations

import argparse

from pipeline.utils import STORYBOARD_PATH, load_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate reference sheet and per-shot keyframes.")
    parser.add_argument("--shot", help="Optional single shot ID (e.g. shot_01) to regenerate.")
    args = parser.parse_args(argv)

    storyboard = load_json(STORYBOARD_PATH)
    shots = storyboard.get("shots", [])
    selected = [s for s in shots if not args.shot or s["id"] == args.shot]
    print(
        f"pipeline.keyframes scaffold ready ({len(selected)} shot(s) targeted) — "
        "awaiting Step 4 reference & keyframe generation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
