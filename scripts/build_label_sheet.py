"""Build docs/templates/judge-labelling-sheet.xlsx: the same labelling sheet Clyve uses, for
anyone who prefers Excel or Google Sheets to editing the CSV. Needs openpyxl (pip install -e ".[dev]").

    python scripts/build_label_sheet.py
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().parents[1] / "docs" / "templates" / "judge-labelling-sheet.xlsx"
COLS = ["id", "text", "signals", "human_verdict", "why", "lead", "date_sent", "today", "freshness_days"]
WIDTHS = {"A": 8, "B": 60, "C": 50, "D": 16, "E": 36, "F": 20, "G": 13, "H": 13, "I": 15}
GUIDE = [
    ("Progress", None),
    ("Labelled", '=COUNTIF(Labels!D2:D1000,"pass")+COUNTIF(Labels!D2:D1000,"fail")'),
    ("Target", 30),
    ("pass", '=COUNTIF(Labels!D2:D1000,"pass")'),
    ("fail", '=COUNTIF(Labels!D2:D1000,"fail")'),
    ("Ready to calibrate?", '=IF(AND(B2>=30,B4>=10,B5>=10),"Yes: save Labels as CSV and calibrate",'
                            '"Not yet: need 30 labels, at least 10 pass and 10 fail")'),
    (None, None),
    ("What this is for", None),
    ("Each row is one real message you sent. You decide pass or fail by hand; then the "
     "personalisation_factuality judge runs on the same rows and gtm-evals measures how often it agrees "
     "with you. At 30+ labels and 85%+ agreement, the workflow can move from PILOT ONLY to DEPLOYABLE.", None),
    (None, None),
    ("How to fill a row", None),
    ("text: the exact message as sent, not the draft.", None),
    ("signals: the facts on file about the recipient, one per line: S1: fact (source URL or screenshot, date).", None),
    ("human_verdict: pass only if every statement about the recipient matches a signal and nothing implies "
     "private data (conversion rate, revenue, CAC, AOV). Stretched, unsupported or stale is fail.", None),
    ("why: one line. For a fail, quote the statement that broke it.", None),
    ("today fills itself from date_sent; freshness_days is 45.", None),
    (None, None),
    ("Tips", None),
    ("Label before you look at the judge's answer.", None),
    ("Get at least 10 fails, or a judge that always says pass looks accurate. Rejected drafts count.", None),
    ("When in doubt, fail it.", None),
    (None, None),
    ("When it's done", None),
    ("Save the Labels sheet as CSV to evals/labels/personalisation_factuality.csv, then run: "
     "gtm-evals judge calibrate personalisation_factuality evals/labels/personalisation_factuality.csv "
     "--update workflows/your-workflow.yaml", None),
]


def main():
    wb = Workbook()
    ws = wb.active
    ws.title = "Labels"
    ws.append(COLS)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="F3F3F3")
    for i in range(1, 31):
        r = i + 1
        ws.append([f"L{i:02d}", None, None, None, None, None, None, f'=IF(G{r}="","",G{r})', 45])
        for col in "GH":
            ws[f"{col}{r}"].number_format = "yyyy-mm-dd"
        for col in "BCE":
            ws[f"{col}{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    dv = DataValidation(type="list", formula1='"pass,fail"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add("D2:D1000")
    for col, w in WIDTHS.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "B2"

    g = wb.create_sheet("How to label")
    for label, value in GUIDE:
        g.append([label, value])
    for r in (1, 8, 11, 18, 23):
        g[f"A{r}"].font = Font(bold=True, size=12)
    for r in range(2, 7):
        g[f"A{r}"].font = Font(bold=True)
    for r in range(9, len(GUIDE) + 1):
        g[f"A{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    g.column_dimensions["A"].width = 100
    g.column_dimensions["B"].width = 48
    g.sheet_view.showGridLines = False

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
