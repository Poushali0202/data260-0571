from __future__ import annotations

import re
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def pdf_escape(value: str) -> str:
    value = value.encode("ascii", "replace").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def markdown_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = re.sub(r"^#{1,6}\s*", "", raw)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = line.replace("—", "-").replace("→", "->")
        if not line.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(line, width=96, break_long_words=False) or [""])
    return lines


def make_pdf(lines: list[str]) -> bytes:
    per_page = 51
    pages = [lines[index : index + per_page] for index in range(0, len(lines), per_page)] or [[]]
    objects: list[bytes] = []
    page_ids = [4 + index * 2 for index in range(len(pages))]
    for index, page_lines in enumerate(pages):
        content = ["BT", "/F1 10 Tf", "50 750 Td", "13 TL"]
        for line in page_lines:
            content.append(f"({pdf_escape(line)}) Tj T*")
        content.append("ET")
        stream = "\n".join(content).encode("ascii")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_ids[index] + 1} 0 R >>"
            ).encode("ascii")
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    base_objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    all_objects = base_objects + objects
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(all_objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(all_objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(all_objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def main() -> None:
    source = ROOT / "reports" / "hw01" / "report.md"
    destination = ROOT / "reports" / "hw01" / "report.pdf"
    destination.write_bytes(make_pdf(markdown_lines(source.read_text(encoding="utf-8"))))
    print(f"wrote {destination}")


if __name__ == "__main__":
    main()
