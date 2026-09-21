from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else "hw01"
    report_dir = ROOT / "reports" / folder
    markdown = (report_dir / "report.md").read_text(encoding="utf-8")
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("H", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6)
    subheading = ParagraphStyle("H3", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=13, spaceAfter=4)
    cell = ParagraphStyle("T", parent=body, fontSize=8, leading=10, spaceAfter=0)
    code = ParagraphStyle("C", parent=styles["Code"], fontSize=7.5, leading=9)

    story = []
    in_code = False
    code_lines: list[str] = []
    table_lines: list[str] = []
    for raw in markdown.splitlines() + [""]:
        if table_lines and not raw.startswith("|"):
            rows = [[Paragraph(inline(text), cell) for text in row] for row in table_rows(table_lines)]
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2ece8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(table)
            story.append(Spacer(1, 8))
            table_lines = []
        if raw.strip().startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), code, maxLineLength=100))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(raw)
            continue
        if raw.startswith("|"):
            table_lines.append(raw)
            continue
        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", raw.strip())
        if image:
            path = report_dir / image.group(2)
            if path.exists():
                img = Image(str(path))
                img._restrictSize(6.5 * inch, 7 * inch)
                story.append(img)
                story.append(Spacer(1, 8))
            continue
        if raw.startswith("# "):
            story.append(Paragraph(inline(raw[2:]), styles["Title"]))
            continue
        if raw.startswith("## "):
            story.append(Paragraph(inline(raw[3:]), heading))
            continue
        if raw.startswith("### "):
            story.append(Paragraph(inline(raw[4:]), subheading))
            continue
        if not raw.strip():
            story.append(Spacer(1, 6))
            continue
        story.append(Paragraph(inline(raw), body))

    dest = report_dir / "report.pdf"
    doc = SimpleDocTemplate(str(dest), pagesize=letter, title=f"DATA-260 {folder.upper()}")
    doc.build(story)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
