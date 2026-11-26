"""Validate `storyboard.json` against schema, duration bounds, subtitles, and consent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from pipeline.utils import SCHEMA_PATH, STORYBOARD_PATH, load_json


def validate_storyboard(
    storyboard_path: Path = STORYBOARD_PATH,
    schema_path: Path = SCHEMA_PATH,
    *,
    allow_unverified_consent: bool = False,
) -> list[str]:
    """Return a list of validation error messages; empty list means valid."""
    errors: list[str] = []
    storyboard = load_json(storyboard_path)
    schema = load_json(schema_path)

    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(storyboard), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"Schema error at `{loc}`: {err.message}")

    shots = storyboard.get("shots", [])
    target = storyboard.get("target_duration_sec")
    total_duration = sum(float(s.get("duration_sec", 0.0)) for s in shots)

    if not (60.0 <= total_duration <= 90.0):
        errors.append(
            f"Total shot duration ({total_duration:.2f}s) must be between 60 and 90 seconds."
        )
    if isinstance(target, (int, float)) and abs(total_duration - float(target)) > 0.5:
        errors.append(
            f"Sum of shot durations ({total_duration:.2f}s) differs from target_duration_sec ({target}s) by >0.5s."
        )

    seen_ids: set[str] = set()
    for shot in shots:
        shot_id = shot.get("id", "<unknown>")
        if shot_id in seen_ids:
            errors.append(f"Duplicate shot id: {shot_id}")
        seen_ids.add(shot_id)

        if not allow_unverified_consent and not shot.get("consent_verified", False):
            errors.append(
                f"Consent gate failed for {shot_id}: `consent_verified` must be true "
                "(record consent in ETHICS.md first)."
            )

        subtitle = shot.get("subtitle_en", "")
        lines = subtitle.splitlines() if subtitle else []
        if len(lines) > 2:
            errors.append(f"{shot_id}: `subtitle_en` exceeds 2 lines ({len(lines)} lines).")
        for idx, line in enumerate(lines, start=1):
            if len(line) > 45:
                errors.append(
                    f"{shot_id}: `subtitle_en` line {idx} is {len(line)} chars (recommended <= 40–45)."
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate storyboard.json contract.")
    parser.add_argument("--storyboard", type=Path, default=STORYBOARD_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument(
        "--skip-consent-gate",
        action="store_true",
        help="Allow schema/duration check during pre-consent drafting only.",
    )
    args = parser.parse_args(argv)

    errors = validate_storyboard(
        args.storyboard,
        args.schema,
        allow_unverified_consent=args.skip_consent_gate,
    )
    if errors:
        print("Storyboard validation FAILED:", file=sys.stderr)
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        return 1

    print(f"Storyboard validation PASSED: {args.storyboard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
