"""One-command end-to-end pipeline orchestrator (`make film` / `python -m pipeline.run`)."""

from __future__ import annotations

import sys

from pipeline import assemble, keyframes, music, narration, shots, validate


def main() -> int:
    stages = [
        ("validate", lambda: validate.main([])),
        ("narration", lambda: narration.main([])),
        ("keyframes", lambda: keyframes.main([])),
        ("music", lambda: music.main([])),
        ("shots", lambda: shots.main([])),
        ("assemble", lambda: assemble.main(["--mode", "final"])),
    ]
    for name, runner in stages:
        print(f"==> Running stage: {name}")
        code = runner()
        if code != 0:
            print(f"Pipeline stopped at stage `{name}` (exit code {code}).", file=sys.stderr)
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
