#!/usr/bin/env python3
"""Package a skill directory into dist/<skill-name>.zip."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


EXCLUDED_NAMES = {".DS_Store", "__MACOSX"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_NAMES for part in path.parts):
        return False
    if "__pycache__" in path.parts:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def package_skill(skill_name: str) -> Path:
    if not skill_name or "/" in skill_name or "\\" in skill_name:
        raise ValueError("skill name must be a directory name, not a path")

    root = Path(__file__).resolve().parent
    skill_dir = root / skill_name
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"skill directory not found: {skill_dir}")
    if not (skill_dir / "SKILL.md").is_file():
        raise FileNotFoundError(f"SKILL.md not found in skill directory: {skill_dir}")

    output_dir = root / "dist"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{skill_name}.zip"

    files = sorted(path for path in skill_dir.rglob("*") if should_include(path))
    if not files:
        raise ValueError(f"no files to package in skill directory: {skill_dir}")

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root))

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package a skill directory under this skills folder into dist/<skill-name>.zip."
    )
    parser.add_argument("skill_name", help="skill directory name, for example: financial-report-extraction")
    args = parser.parse_args()

    try:
        output_path = package_skill(args.skill_name)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
