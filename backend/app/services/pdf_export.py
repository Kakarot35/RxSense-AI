"""
Generates a downloadable Prescription Summary Report as PDF.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from io import BytesIO
from datetime import datetime

SEVERITY_COLORS = {
    "Major":    colors.HexColor("#dc2626"),
    "Moderate": colors.HexColor("#d97706"),
    "Minor":    colors.HexColor("#65a30d"),
}

def generate_pdf(result: dict) -> bytes:
    """
    Accepts the same dict structure returned by process_prescription task.
    Returns raw PDF bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Header
    story.append(Paragraph("Prescription Summary Report", ParagraphStyle(
        "Title", fontSize=20, fontName="Helvetica-Bold", spaceAfter=4, alignment=TA_CENTER
    )))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}",
        ParagraphStyle("Sub", fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.5*cm))

    # Interaction alerts
    if result.get("interactions"):
        story.append(Paragraph("Interaction Alerts", ParagraphStyle(
            "H2", fontSize=14, fontName="Helvetica-Bold", spaceAfter=8
        )))
        for alert in result["interactions"]:
            sev_color = SEVERITY_COLORS.get(alert["severity"], colors.grey)
            data = [[
                Paragraph(f'<font color="{sev_color.hexval()}">{alert["severity"]}</font>',
                          styles["Normal"]),
                Paragraph(f'{" + ".join(alert["drugs"])}: {alert["description"]}',
                          styles["Normal"]),
            ]]
            t = Table(data, colWidths=[2.5*cm, 13*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#fef2f2")),
                ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#fef2f2")]),
                ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#fecaca")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 8),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3*cm))
        story.append(Spacer(1, 0.5*cm))

    # Drug explanations
    story.append(Paragraph("Medication Explanations", ParagraphStyle(
        "H2", fontSize=14, fontName="Helvetica-Bold", spaceAfter=8
    )))
    for drug in result.get("drugs", []):
        story.append(Paragraph(drug["drug"].title(), ParagraphStyle(
            "DrugName", fontSize=12, fontName="Helvetica-Bold", spaceAfter=2
        )))
        meta = []
        if drug.get("dosage"):
            meta.append(f"Dosage: {drug['dosage']}")
        if drug.get("frequency"):
            meta.append(f"Frequency: {drug['frequency']}")
        if meta:
            story.append(Paragraph("  ·  ".join(meta), ParagraphStyle(
                "Meta", fontSize=9, textColor=colors.grey, spaceAfter=4
            )))
        story.append(Paragraph(drug["explanation"], styles["Normal"]))
        if drug.get("sources"):
            story.append(Paragraph(
                f"Sources: {', '.join(drug['sources'])}",
                ParagraphStyle("Src", fontSize=8, textColor=colors.grey, spaceAfter=4)
            ))
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=0.3, color=colors.lightgrey))
        story.append(Spacer(1, 0.4*cm))

    # Disclaimer
    story.append(Paragraph(
        "DISCLAIMER: This report is for patient education only and does not replace advice "
        "from your doctor or pharmacist. Always follow your prescriber's specific instructions.",
        ParagraphStyle("Disc", fontSize=8, textColor=colors.grey, borderPad=6,
                       backColor=colors.HexColor("#f9fafb"), leading=12)
    ))

    doc.build(story)
    return buffer.getvalue()
