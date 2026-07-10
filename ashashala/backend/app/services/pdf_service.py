"""On-demand PDF rendering for a Report row — not cached, regenerated per
request from the stored narrative/snapshot fields (cheap; avoids storing
binary blobs in Postgres)."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

from app.models.report import Report


def render_report_pdf(report: Report, *, student_name: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Progress Report — {student_name}", styles["Title"]),
        Paragraph(f"Period: {report.period_start.isoformat()} to {report.period_end.isoformat()}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(report.narrative, styles["BodyText"]),
        Spacer(1, 12),
    ]

    if report.mastery_snapshot_json:
        story.append(Paragraph("Mastery by topic", styles["Heading2"]))
        rows = [["Topic", "Score"]] + [
            [m.get("topic", ""), str(m.get("score", ""))] for m in report.mastery_snapshot_json
        ]
        story.append(Table(rows))
        story.append(Spacer(1, 12))

    if report.quiz_score_trend_json:
        story.append(Paragraph("Recent quiz scores", styles["Heading2"]))
        rows = [["Date", "Score"]] + [
            [q.get("attempted_at", ""), str(q.get("score", ""))] for q in report.quiz_score_trend_json
        ]
        story.append(Table(rows))
        story.append(Spacer(1, 12))

    if report.teacher_notes:
        story.append(Paragraph("Teacher notes", styles["Heading2"]))
        story.append(Paragraph(report.teacher_notes, styles["BodyText"]))

    doc.build(story)
    return buffer.getvalue()
