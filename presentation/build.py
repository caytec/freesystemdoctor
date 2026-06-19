#!/usr/bin/env python3
"""Render the FreeAndroidDoctor product deck (PL + EN) to PDF via WeasyPrint."""
from pathlib import Path
from weasyprint import HTML

HERE = Path(__file__).parent
DIST = HERE / "dist"
DIST.mkdir(exist_ok=True)

for lang in ("pl", "en"):
    src = HERE / f"deck-{lang}.html"
    out = DIST / f"FreeAndroidDoctor-deck-{lang.upper()}.pdf"
    print(f"Rendering {src.name} -> {out.name}")
    HTML(filename=str(src), base_url=str(HERE)).write_pdf(str(out))
    size_kb = out.stat().st_size // 1024
    print(f"  done ({size_kb} KB)")

print("\nOutput:")
for pdf in sorted(DIST.glob("*.pdf")):
    print(f"  {pdf}")
