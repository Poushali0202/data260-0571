from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, Preformatted, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports" / "hw01"


def main() -> None:
    markdown = (REPORT_DIR / "report.md").read_text(encoding="utf-8")
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("H", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=13, spaceAfter=4)
    code = ParagraphStyle("C", parent=styles["Code"], fontSize=8, leading=10)

    story = []
    in_code = False
    code_lines: list[str] = []
    for raw in markdown.splitlines():
        if raw.strip().startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), code))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(raw)
            continue
        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", raw.strip())
        if image:
            path = REPORT_DIR / image.group(2)
            if path.exists():
                img = Image(str(path))
                img._restrictSize(6.5 * inch, 4.2 * inch)
                story.append(img)
                story.append(Spacer(1, 8))
            else:
                story.append(Paragraph(f"[missing image: {image.group(2)}]", body))
            continue
        if raw.startswith("# "):
            story.append(Paragraph(raw[2:], styles["Title"]))
            continue
        if raw.startswith("## "):
            story.append(Paragraph(raw[3:], heading))
            continue
        line = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        line = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
        if not line.strip():
            story.append(Spacer(1, 6))
            continue
        story.append(Paragraph(line, body))

    dest = REPORT_DIR / "report.pdf"
    doc = SimpleDocTemplate(str(dest), pagesize=letter, title="DATA-260 HW1")
    doc.build(story)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
