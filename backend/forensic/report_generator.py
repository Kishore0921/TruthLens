import json
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from backend.config import REPORTS_DIR


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TLTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=4 * mm,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='TLTagline',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#5c6bc0'),
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    ))
    styles.add(ParagraphStyle(
        name='TLHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#283593'),
        spaceBefore=10 * mm,
        spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        name='TLSubHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#3949ab'),
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name='TLBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name='TLSmall',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='TLWarning',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#b71c1c'),
        leading=14,
        spaceBefore=4 * mm,
        spaceAfter=4 * mm,
    ))
    return styles


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(15 * mm, 10 * mm, f"TruthLens Report — Page {doc.page}")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, "CONFIDENTIAL — Requires Human Review")
    canvas.restoreState()


def _confidence_color(band: str) -> str:
    return {
        'high': '#c62828',
        'medium': '#ef6c00',
        'low': '#2e7d32',
    }.get(band, '#616161')


def generate_pdf_report(report_data: dict) -> Path:
    """Generate a professional PDF forensic report. Returns the file path."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    inv = report_data.get("investigation", {})
    inv_id = inv.get("id", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"truthlens_report_{inv_id[:8]}_{timestamp}.pdf"
    filepath = REPORTS_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = _build_styles()
    story = []

    # ── Title Page ──
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("TruthLens", styles['TLTitle']))
    story.append(Paragraph("Detect. Analyze. Correlate. Explain.", styles['TLTagline']))
    story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor('#5c6bc0'),
                            spaceAfter=8 * mm, spaceBefore=4 * mm, hAlign='CENTER'))

    story.append(Paragraph("Forensic Analysis Report", styles['TLHeading']))

    meta_data = [
        ["Investigation ID:", inv_id],
        ["Title:", inv.get("title", "Untitled")],
        ["Status:", inv.get("status", "unknown")],
        ["Generated:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")],
    ]
    meta_table = Table(meta_data, colWidths=[45 * mm, 110 * mm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    if inv.get("description"):
        story.append(Paragraph(f"<b>Description:</b> {inv['description']}", styles['TLBody']))

    # ── Executive Forensic Assessment ──
    assessment = report_data.get("assessment", {})
    if assessment:
        badge = assessment.get("badge_label", "Under Review")
        headline = assessment.get("headline", "")
        narrative = assessment.get("summary_narrative", "")

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"<b>Forensic Assessment:</b> <font color='#1a237e'><b>{badge}</b></font>", styles['TLSubHeading']))
        if headline:
            story.append(Paragraph(f"<b>{headline}</b>", styles['TLBody']))
        if narrative:
            story.append(Paragraph(narrative, styles['TLBody']))

        key_obs = assessment.get("key_observations", [])
        if key_obs:
            story.append(Paragraph("<b>Key Empirical Observations:</b>", styles['TLBody']))
            for obs in key_obs[:5]:
                story.append(Paragraph(f"• {obs}", styles['TLBody']))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "<i>This report presents observations, heuristic indicators, and model-based scores. "
        "It does not make definitive claims of authenticity or fabrication. "
        "All findings require independent human review by qualified analysts.</i>",
        styles['TLWarning']
    ))

    story.append(PageBreak())

    # ── Evidence Inventory ──
    evidence_items = report_data.get("evidence_items", [])
    story.append(Paragraph("Evidence Inventory", styles['TLHeading']))

    if evidence_items:
        ev_header = ["#", "Filename", "Type", "Size", "SHA-256"]
        ev_rows = [ev_header]
        for i, ev in enumerate(evidence_items, 1):
            sha = ev.get("sha256", "")
            sha_display = f"{sha[:16]}..." if len(sha) > 16 else sha
            size_bytes = ev.get("file_size", 0)
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            elif size_bytes > 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes} B"
            ev_rows.append([
                str(i),
                ev.get("original_filename", "unknown")[:30],
                ev.get("media_type", "unknown"),
                size_str,
                sha_display,
            ])
        ev_table = Table(ev_rows, colWidths=[10 * mm, 50 * mm, 20 * mm, 25 * mm, 55 * mm])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eaf6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
        ]))
        story.append(ev_table)
    else:
        story.append(Paragraph("No evidence items submitted.", styles['TLBody']))

    # ── Findings ──
    findings = report_data.get("findings", [])
    story.append(Paragraph("Analysis Findings", styles['TLHeading']))

    if findings:
        # Group by engine
        by_engine = {}
        for f in findings:
            engine = f.get("engine", "unknown")
            by_engine.setdefault(engine, []).append(f)

        for engine, engine_findings in by_engine.items():
            story.append(Paragraph(f"Engine: {engine}", styles['TLSubHeading']))

            for f in engine_findings:
                band = f.get("confidence_band", "medium")
                band_color = _confidence_color(band)
                score = f.get("model_score")
                score_str = f" (score: {score:.2f})" if score is not None else ""

                story.append(Paragraph(
                    f'<b>{f.get("indicator", "N/A")}</b> — '
                    f'<font color="{band_color}">Confidence: {band.upper()}</font>'
                    f'{score_str}',
                    styles['TLBody']
                ))
                story.append(Paragraph(f'{f.get("description", "")}', styles['TLBody']))

                limitations = f.get("limitations", [])
                if limitations:
                    lim_text = "; ".join(limitations)
                    story.append(Paragraph(
                        f'<font color="#757575"><i>Limitations: {lim_text}</i></font>',
                        styles['TLBody']
                    ))

                story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph("No findings were generated during analysis.", styles['TLBody']))

    # ── Cross-Modal Correlations ──
    correlations = report_data.get("correlations", [])
    story.append(Paragraph("Cross-Modal Correlations", styles['TLHeading']))

    if correlations:
        for c in correlations:
            strength = c.get("strength", 0)
            story.append(Paragraph(
                f'<b>{c.get("relationship_type", "N/A")}</b> — '
                f'Strength: {strength:.2f}',
                styles['TLBody']
            ))
            story.append(Paragraph(f'{c.get("explanation", "")}', styles['TLBody']))
            if c.get("rule_id"):
                story.append(Paragraph(
                    f'<font color="#757575"><i>Rule: {c["rule_id"]}</i></font>',
                    styles['TLBody']
                ))
            c_limitations = c.get("limitations", [])
            if c_limitations:
                story.append(Paragraph(
                    f'<font color="#757575"><i>Correlation Limitations: {"; ".join(c_limitations)}</i></font>',
                    styles['TLBody']
                ))
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph(
            "No cross-modal correlations were identified. This may indicate independent evidence "
            "or insufficient findings for correlation analysis.",
            styles['TLBody']
        ))

    # ── Summary ──
    summary = report_data.get("summary", {})
    story.append(Paragraph("Summary", styles['TLHeading']))

    summary_data = [
        ["Total Evidence Items:", str(summary.get("total_evidence", 0))],
        ["Total Findings:", str(summary.get("total_findings", 0))],
        ["Total Correlations:", str(summary.get("total_correlations", 0))],
    ]
    if summary.get("confidence_distribution"):
        for band, count in summary["confidence_distribution"].items():
            summary_data.append([f"  {band.capitalize()} Confidence:", str(count)])

    sum_table = Table(summary_data, colWidths=[55 * mm, 100 * mm])
    sum_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 * mm),
    ]))
    story.append(sum_table)

    # ── Limitations ──
    limitations = report_data.get("limitations", [])
    story.append(Paragraph("Limitations & Disclaimers", styles['TLHeading']))

    all_limitations = [
        "Automated analysis tools provide indicators, not conclusive proof.",
        "Model scores reflect statistical patterns and may produce false positives or false negatives.",
        "Absence of detected indicators does not confirm authenticity.",
        "Results should be interpreted by qualified forensic analysts in proper context.",
        "Environmental factors (compression, re-encoding, screenshots) can affect analysis accuracy.",
    ] + limitations

    for lim in all_limitations:
        story.append(Paragraph(f"• {lim}", styles['TLBody']))

    # ── Conclusion ──
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="80%", thickness=1, color=colors.HexColor('#5c6bc0'),
                            spaceAfter=4 * mm, hAlign='CENTER'))
    story.append(Paragraph(
        "<b>This report requires human review.</b> The findings presented are observations and "
        "heuristic indicators generated by automated analysis engines. They do not constitute "
        "definitive judgments of authenticity or manipulation. A qualified human analyst must "
        "review and interpret these results in context before any conclusions are drawn.",
        styles['TLWarning']
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        f"Generated by TruthLens v1.0.0 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        styles['TLSmall']
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return filepath
