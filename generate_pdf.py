"""Generate assessment PDF from SUBMISSION.md content."""
import re
import unicodedata
from fpdf import FPDF
from pathlib import Path

ROOT = Path(__file__).parent
MD = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8")


def sanitize(text: str) -> str:
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2192": "->", "\u2260": "!=",
        "\u2265": ">=", "\u00d7": "x", "\u2022": "-", "\u2018": "'", "\u2019": "'",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "Deriv DA Assessment Submission", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def write_line(self, text: str, style: str = "", size: int = 10):
        text = sanitize(text.strip())
        if not text:
            self.ln(3)
            return
        if len(text) > 110:
            text = text[:107] + "..."
        self.set_x(self.l_margin)
        self.set_font("Helvetica", style, size)
        self.multi_cell(self.epw, 5, text)

    def write_section(self, text: str):
        in_code = False
        for line in text.split("\n"):
            raw = line.rstrip()
            if raw.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                if raw.startswith("+") or raw.startswith("|") or "----" in raw:
                    continue
                self.write_line(raw, "", 8)
                continue
            if not raw:
                self.ln(2)
                continue
            if raw.startswith("# "):
                self.ln(3)
                self.write_line(raw[2:], "B", 14)
            elif raw.startswith("## "):
                self.ln(2)
                self.write_line(raw[3:], "B", 12)
            elif raw.startswith("### "):
                self.ln(1)
                self.write_line(raw[4:], "B", 11)
            else:
                clean = re.sub(r"\*\*|`", "", raw)
                self.write_line(clean.lstrip("> "), "I" if raw.startswith(">") else "", 9 if raw.startswith("-") else 10)


pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.write_section(MD)
out = ROOT / "Deriv_DA_Assessment_Submission.pdf"
pdf.output(str(out))
print(f"Written: {out}")
