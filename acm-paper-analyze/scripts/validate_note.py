#!/usr/bin/env python3
"""Validate and optionally repair an Obsidian paper note."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import fitz


IMAGE_REF_RE = re.compile(r"!\[[^\]]+\]\((images/[^)]+\.png)\)")
CAPTION_RE = re.compile(r"> (Figure|Table)( \d+)?: ")
QUALITY_RE = re.compile(r'quality_score: "\d+\.\d/10"$')
STRING_KEYS = {"date", "paper_id", "title", "authors", "domain", "quality_score", "created", "updated"}


def is_mostly_white_image(path: Path, threshold: float = 0.95) -> bool:
    try:
        pix = fitz.Pixmap(path)
    except Exception:
        return False

    if pix.width * pix.height == 0:
        return True

    samples = pix.samples
    stride = pix.n
    white = 0
    sampled = 0
    step = max(stride * 4, stride)

    for i in range(0, len(samples) - stride, step):
        if stride < 3:
            is_white = samples[i] > 240
        else:
            r, g, b = samples[i], samples[i + 1], samples[i + 2]
            is_white = r > 240 and g > 240 and b > 240
        if is_white:
            white += 1
        sampled += 1

    return sampled > 0 and white / sampled > threshold


def remove_image_blocks(lines: list[str], bad_refs: set[str]) -> list[str]:
    cleaned: list[str] = []
    i = 0
    while i < len(lines):
        match = IMAGE_REF_RE.search(lines[i])
        if match and match.group(1) in bad_refs:
            i += 1
            if i < len(lines) and lines[i] == "":
                i += 1
            if i < len(lines) and lines[i].startswith("> ") and CAPTION_RE.match(lines[i]):
                i += 1
            continue
        cleaned.append(lines[i])
        i += 1
    return cleaned


def ensure_image_caption_spacing(lines: list[str]) -> tuple[list[str], int]:
    fixed: list[str] = []
    inserts = 0
    i = 0
    while i < len(lines):
        fixed.append(lines[i])
        if IMAGE_REF_RE.search(lines[i]):
            next_line = lines[i + 1] if i + 1 < len(lines) else None
            if next_line is not None and next_line.startswith("> ") and CAPTION_RE.match(next_line):
                fixed.append("")
                inserts += 1
        i += 1
    return fixed, inserts


def yaml_tag_issues(lines: list[str]) -> list[str]:
    issues: list[str] = []
    in_frontmatter = False
    for line_no, line in enumerate(lines, start=1):
        if line == "---":
            in_frontmatter = not in_frontmatter
            continue
        if not in_frontmatter:
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            if key in STRING_KEYS:
                value = value.strip()
                if not (value.startswith('"') and value.endswith('"')):
                    issues.append(f"line {line_no}: {key} must be wrapped in double quotes")
        if line.startswith("quality_score:") and not QUALITY_RE.match(line):
            issues.append(f"line {line_no}: quality_score must look like \"8.5/10\"")
        if line.strip().startswith("- "):
            tag = line.strip()[2:]
            if " " in tag:
                issues.append(f"line {line_no}: tag contains spaces: {tag}")
    return issues


def resolve_ref(note_path: Path, images_dir: Path, ref: str) -> Path:
    ref_path = Path(ref)
    if ref_path.parts and ref_path.parts[0] == "images":
        return images_dir / ref_path.name
    return note_path.parent / ref_path


def validate(note_path: Path, images_dir: Path, fix: bool) -> int:
    text = note_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues: list[str] = []

    if not text.startswith("---\n"):
        issues.append("missing YAML frontmatter")

    refs = IMAGE_REF_RE.findall(text)
    missing_refs = {ref for ref in refs if not resolve_ref(note_path, images_dir, ref).exists()}

    white_refs: set[str] = set()
    for ref in refs:
        image_path = resolve_ref(note_path, images_dir, ref)
        if image_path.exists() and is_mostly_white_image(image_path):
            white_refs.add(ref)

    for ref in sorted(missing_refs):
        issues.append(f"broken image reference: {ref}")
    for ref in sorted(white_refs):
        issues.append(f"mostly white image reference: {ref}")

    for idx, line in enumerate(lines):
        if IMAGE_REF_RE.search(line):
            if idx + 1 >= len(lines) or lines[idx + 1] != "":
                issues.append(f"line {idx + 1}: image must be followed by a blank line")
            if idx + 2 >= len(lines) or not CAPTION_RE.match(lines[idx + 2]):
                issues.append(f"line {idx + 1}: image must be followed by a Figure/Table caption")

    issues.extend(yaml_tag_issues(lines))

    if fix:
        bad_refs = missing_refs | white_refs
        if bad_refs:
            lines = remove_image_blocks(lines, bad_refs)
        lines, _ = ensure_image_caption_spacing(lines)
        note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        for ref in white_refs:
            image_path = resolve_ref(note_path, images_dir, ref)
            if image_path.exists():
                image_path.unlink()

    if fix and issues:
        return validate(note_path, images_dir, False)

    if issues:
        for issue in issues:
            print(issue)
        return 1

    print("OK")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an Obsidian paper note.")
    parser.add_argument("note_path", type=Path)
    parser.add_argument("--images-dir", type=Path, help="Defaults to NOTE_DIR/images.")
    parser.add_argument("--fix", action="store_true", help="Remove bad image blocks and repair image spacing.")
    args = parser.parse_args()

    images_dir = args.images_dir or args.note_path.parent / "images"
    raise SystemExit(validate(args.note_path, images_dir, args.fix))


if __name__ == "__main__":
    main()
