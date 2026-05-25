#!/usr/bin/env python3
"""Extract non-blank figure/table crops from a PDF.

This script intentionally avoids caption-only cropping. It only writes an
image when the crop contains real visual content near the caption, and skips
mostly white renders that usually happen when a caption is separated from the
figure body across pages.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


CAPTION_RE = re.compile(r"^(Figure|Fig\.?|Table)\s*(\d+)", re.IGNORECASE)


def get_visual_bboxes(page: fitz.Page) -> list[tuple[float, float, float, float]]:
    """Return bounding boxes for real visual blocks: embedded images + drawings."""
    bboxes: list[tuple[float, float, float, float]] = []

    try:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            for rect in page.get_image_rects(xref):
                if rect.height > 8 and rect.width > 8:
                    bboxes.append((rect.x0, rect.y0, rect.x1, rect.y1))
    except Exception:
        pass

    try:
        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if rect and rect.height > 8 and rect.width > 8:
                bboxes.append((rect.x0, rect.y0, rect.x1, rect.y1))
    except Exception:
        pass

    return bboxes


def is_mostly_white(pix: fitz.Pixmap, threshold: float = 0.95) -> bool:
    """Return True when sampled pixels are overwhelmingly white."""
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


def extract_figures(pdf_path: Path, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    extracted: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_top, page_bot = page.rect.y0, page.rect.y1
        page_h = page.rect.height
        blocks = page.get_text("dict").get("blocks", [])
        visual_bboxes = get_visual_bboxes(page)

        captions = []
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                match = CAPTION_RE.match(line_text)
                if match:
                    captions.append(
                        {
                            "type": "table" if match.group(1).lower().startswith("table") else "figure",
                            "num": match.group(2),
                            "bbox": block["bbox"],
                        }
                    )
                    break

        if not captions:
            if len(visual_bboxes) > 30:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                if not is_mostly_white(pix):
                    file_name = f"page{page_num + 1}.png"
                    pix.save(out_dir / file_name)
                    extracted.append(file_name)
            continue

        for cap in captions:
            cap_top, cap_bot = cap["bbox"][1], cap["bbox"][3]
            prefix = "fig" if cap["type"] == "figure" else "table"
            file_name = f"{prefix}{cap['num']}_page{page_num + 1}.png"

            visual_above = [
                box for box in visual_bboxes
                if box[3] <= cap_top + 5 and box[1] >= page_top + 40
            ]
            visual_below = [
                box for box in visual_bboxes
                if box[1] >= cap_bot - 5 and box[3] <= page_bot - 20
            ]

            if visual_above:
                fig_top = min(box[1] for box in visual_above) - 5
                fig_bot = cap_bot + 5
            elif visual_below and cap_bot < page_top + 0.5 * page_h:
                fig_top = cap_top - 5
                fig_bot = max(box[3] for box in visual_below) + 5
            else:
                continue

            fig_top = max(fig_top, page_top + 30)
            fig_bot = min(fig_bot, page_bot - 20)
            if fig_bot - fig_top < 40:
                continue

            clip = fitz.Rect(page.rect.x0 + 5, fig_top, page.rect.x1 - 5, fig_bot)
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=clip)
            if pix.height < 50 or pix.width < 100:
                continue
            if is_mostly_white(pix):
                continue

            pix.save(out_dir / file_name)
            extracted.append(file_name)

    doc.close()
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract non-blank figures and tables from a PDF.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("images_dir", type=Path)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of one file per line.")
    args = parser.parse_args()

    images = extract_figures(args.pdf_path, args.images_dir)
    if args.json:
        print(json.dumps(images, ensure_ascii=False, indent=2))
    else:
        print("\n".join(images))


if __name__ == "__main__":
    main()
