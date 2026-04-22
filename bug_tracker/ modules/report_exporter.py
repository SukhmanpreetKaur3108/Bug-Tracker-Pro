"""
modules/report_exporter.py  —  Report Export Module
=====================================================
Exports bug data as:
  • CSV  — download via Streamlit st.download_button
  • PDF  — simple tabular report using reportlab
"""

import csv
import io
from datetime import datetime

# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

_CSV_FIELDS = [
    "id", "title", "severity", "priority", "priority_score",
    "status", "reported_by", "assigned_to",
    "created_at", "updated_at", "description",
]

def export_csv(bugs: list, users: list) -> bytes:
    """
    Export a list of bugs to CSV bytes.

    :param bugs:  List of bug dicts.
    :param users: List of user dicts (used to resolve IDs to names).
    :return:      UTF-8 encoded CSV bytes ready for st.download_button.
    """
    user_map = {u["id"]: u["username"] for u in users}
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()

    for bug in bugs:
        row = {k: bug.get(k, "") for k in _CSV_FIELDS}
        row["reported_by"] = user_map.get(bug.get("reported_by"), str(bug.get("reported_by", "")))
        row["assigned_to"] = user_map.get(bug.get("assigned_to"), "Unassigned")
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

def export_pdf(bugs: list, users: list) -> bytes:
    """
    Export a list of bugs to a simple PDF report.

    :param bugs:  List of bug dicts.
    :param users: List of user dicts.
    :return:      PDF bytes ready for st.download_button.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
    except ImportError:
        return b""   # reportlab not installed

    user_map = {u["id"]: u["username"] for u in users}
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=inch, bottomMargin=inch)

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Bug Tracker — Export Report", styles["Title"]))
    elements.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  |  Total bugs: {len(bugs)}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 0.2*inch))

    # Table header + rows
    header = ["#", "Title", "Severity", "Status", "Score", "Reporter", "Assignee", "Date"]
    data = [header]
    for bug in bugs:
        data.append([
            str(bug.get("id", "")),
            bug.get("title", "")[:40],
            bug.get("severity", ""),
            bug.get("status", ""),
            str(bug.get("priority_score", "")),
            user_map.get(bug.get("reported_by"), "?"),
            user_map.get(bug.get("assigned_to"), "—"),
            str(bug.get("created_at", ""))[:10],
        ])

    tbl = Table(data, colWidths=[0.3*inch, 2.2*inch, 0.8*inch, 0.9*inch,
                                  0.5*inch, 0.9*inch, 0.9*inch, 0.8*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#2C3E50")),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8F9FA"), colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(tbl)

    doc.build(elements)
    return buffer.getvalue()
