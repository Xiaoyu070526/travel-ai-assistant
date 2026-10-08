"""Render PDFs with Poppler, assemble page contact sheets and check content bounds."""

from pathlib import Path
import shutil
import subprocess

import fitz
from PIL import Image, ImageDraw


def main():
    root = Path("tmp/pdfs")
    root.mkdir(parents=True, exist_ok=True)
    samples = [Path("output/pdf/travel-plan-preview-zh.pdf")]
    samples.extend(root / f"travel-plan-preview-{lang}.pdf" for lang in ("en", "ja", "fr", "ko"))
    poppler = shutil.which("pdftoppm")
    if not poppler:
        raise RuntimeError("pdftoppm is required for PDF visual QA")
    for sample in samples:
        prefix = root / sample.stem
        subprocess.run([poppler, "-r", "80", "-png", str(sample), str(prefix)], check=True)
        pages = sorted(page for page in root.glob(sample.stem + "-*.png")
                       if page.stem.rsplit("-", 1)[-1].isdigit())
        contact = Image.new("RGB", (600 * 2, 880 * ((len(pages) + 1) // 2)), "#dce4e8")
        draw = ImageDraw.Draw(contact)
        for i, page in enumerate(pages):
            with Image.open(page) as image:
                image.thumbnail((560, 810))
                x, y = (i % 2) * 600 + 20, (i // 2) * 880 + 40
                contact.paste(image, (x, y))
                draw.text((x, y - 25), page.name, fill="black")
        contact.save(root / (sample.stem + "-contact.png"))
        with fitz.open(sample) as doc:
            for number, page in enumerate(doc, 1):
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        for span in line["spans"]:
                            x0, y0, x1, y1 = span["bbox"]
                            assert 0 <= x0 <= x1 <= page.rect.width, (sample, number, span)
                            assert 0 <= y0 <= y1 <= page.rect.height, (sample, number, span)
            print(sample.name, len(doc), "pages; text within page bounds")


if __name__ == "__main__":
    main()
