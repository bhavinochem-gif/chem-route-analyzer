import io
from datetime import datetime
from PIL import Image as PILImage

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, 
    TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

from src.chem_renderer import render_reaction_scheme, generate_mechanism_flowchart_image

THEMES = {
    "Pharma Blue (Default)": {
        "primary": colors.HexColor("#1E3A8A"),
        "secondary": colors.HexColor("#2563EB"),
        "accent_bg": colors.HexColor("#EFF6FF"),
        "accent_border": colors.HexColor("#BFDBFE"),
        "text_dark": colors.HexColor("#0F172A"),
        "text_muted": colors.HexColor("#64748B"),
        "table_bg": colors.HexColor("#F8FAFC"),
        "table_border": colors.HexColor("#CBD5E1"),
        "rule_color": colors.HexColor("#CBD5E1")
    },
    "Emerald Biotech": {
        "primary": colors.HexColor("#065F46"),
        "secondary": colors.HexColor("#059669"),
        "accent_bg": colors.HexColor("#ECFDF5"),
        "accent_border": colors.HexColor("#A7F3D0"),
        "text_dark": colors.HexColor("#064E3B"),
        "text_muted": colors.HexColor("#4B5563"),
        "table_bg": colors.HexColor("#F9FAFB"),
        "table_border": colors.HexColor("#D1D5DB"),
        "rule_color": colors.HexColor("#D1D5DB")
    },
    "Crimson Process R&D": {
        "primary": colors.HexColor("#881337"),
        "secondary": colors.HexColor("#BE123C"),
        "accent_bg": colors.HexColor("#FFF1F2"),
        "accent_border": colors.HexColor("#FECDD3"),
        "text_dark": colors.HexColor("#4C0519"),
        "text_muted": colors.HexColor("#71717A"),
        "table_bg": colors.HexColor("#FAFAFA"),
        "table_border": colors.HexColor("#E4E4E7"),
        "rule_color": colors.HexColor("#E4E4E7")
    }
}

class BrandedNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, theme=None, org_name="Process Chemistry R&D", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.theme = theme or THEMES["Pharma Blue (Default)"]
        self.org_name = org_name

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(self.theme["text_muted"])
        
        self.drawString(54, letter[1] - 36, self.org_name.upper())
        self.setFont("Helvetica", 8)
        self.drawRightString(letter[0] - 54, letter[1] - 36, "Synthesis Route & Reaction Mechanism Pathway")
        
        self.setStrokeColor(self.theme["rule_color"])
        self.setLineWidth(0.5)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
        
        self.line(54, 45, letter[0] - 54, 45)
        self.drawString(54, 32, "CONFIDENTIAL — PROCESS CHEMISTRY & MECHANISM ELUCIDATION")
        self.drawRightString(letter[0] - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_report_styles(theme):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocTitle", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=theme["primary"]))
    styles.add(ParagraphStyle(name="SectionHeader", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=theme["primary"], spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle(name="StepTitle", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=theme["secondary"], spaceBefore=6, spaceAfter=3))
    styles.add(ParagraphStyle(name="BodyTextDark", fontName="Helvetica", fontSize=8, leading=11, textColor=theme["text_dark"]))
    styles.add(ParagraphStyle(name="MetaLabel", fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=theme["text_muted"]))
    styles.add(ParagraphStyle(name="MetaValue", fontName="Helvetica", fontSize=8, leading=10, textColor=theme["text_dark"]))
    return styles

def build_pdf_report(
    route_data: dict, 
    file_name: str = "Synthesis Route",
    logo_bytes: bytes = None,
    org_name: str = "Process Chemistry R&D",
    theme_name: str = "Pharma Blue (Default)"
) -> io.BytesIO:
    theme = THEMES.get(theme_name, THEMES["Pharma Blue (Default)"])
    pdf_buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = build_report_styles(theme)
    story = []
    content_width = letter[0] - 108

    # Title Block
    title_paragraphs = [
        Paragraph(f"<b>{org_name}</b>", styles["MetaLabel"]),
        Paragraph("Synthesis Route & Mechanism Pathway Dossier", styles["DocTitle"]),
        Spacer(1, 3),
        Paragraph(f"<b>Source:</b> {file_name} &nbsp;|&nbsp; <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')} &nbsp;|&nbsp; <b>Steps:</b> {len(route_data.get('steps', []))}", styles["MetaValue"])
    ]

    if logo_bytes:
        logo_img_buf = io.BytesIO(logo_bytes)
        pil_img = PILImage.open(logo_img_buf)
        w, h = pil_img.size
        aspect = h / float(w)
        logo_w = 90
        logo_h = min(logo_w * aspect, 45)
        logo_img_buf.seek(0)
        logo_flowable = RLImage(logo_img_buf, width=logo_w, height=logo_h)

        header_table = Table([[title_paragraphs, logo_flowable]], colWidths=[content_width - 100, 100])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
    else:
        story.extend(title_paragraphs)

    story.append(Spacer(1, 5))
    story.append(HRFlowable(width="100%", thickness=1, color=theme["primary"], spaceAfter=8))

    # Overall Strategy Box
    overview_text = route_data.get("overall_route_summary", "No summary available.")
    overview_box = Table(
        [[Paragraph("<b>Synthetic Route Strategy Overview</b>", styles["SectionHeader"])],
         [Paragraph(overview_text, styles["BodyTextDark"])]],
        colWidths=[content_width]
    )
    overview_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), theme["accent_bg"]),
        ("BOX", (0, 0), (-1, -1), 1, theme["accent_border"]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(overview_box)
    story.append(Spacer(1, 8))

    # Step Iteration
    for step in route_data.get("steps", []):
        step_elements = []
        step_num = step.get("step_number", 1)
        rxn_name = step.get("reaction_name", "Unclassified Transformation")
        rxn_class = step.get("reaction_class_type", "General Transformation")
        
        step_elements.append(Paragraph(f"Step {step_num}: {rxn_name} ({rxn_class})", styles["StepTitle"]))
        
        # (a) Conditions Block
        conditions = step.get("reagents_solvents_conditions", "N/A")
        cond_table = Table(
            [[Paragraph("<b>(a) Route & Conditions:</b>", styles["MetaLabel"]), Paragraph(conditions, styles["BodyTextDark"])]],
            colWidths=[130, content_width - 130]
        )
        cond_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["table_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.5, theme["table_border"]),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        step_elements.append(cond_table)
        step_elements.append(Spacer(1, 4))

        # (a) Overall Scheme
        rxn_smarts = step.get("reaction_smarts", "")
        if rxn_smarts and ">" in rxn_smarts:
            rxn_buf = render_reaction_scheme(rxn_smarts)
            if rxn_buf:
                step_elements.append(RLImage(rxn_buf, width=content_width, height=95))
                step_elements.append(Spacer(1, 6))

        # (b) Continuous Reaction Mechanism Pathway Canvas
        pathway = step.get("elementary_mechanism_pathway", [])
        if pathway:
            mech_canvas_buf = generate_mechanism_flowchart_image(pathway, title=f"(b) Reaction Mechanism — Step {step_num} Elementary Pathway")
            if mech_canvas_buf:
                # Dynamic height based on row count
                n_items = len(pathway)
                calc_h = 135 if n_items <= 3 else 210
                step_elements.append(RLImage(mech_canvas_buf, width=content_width, height=calc_h))
                step_elements.append(Spacer(1, 6))

        # Process Parameters & Impurity Risks Table
        proc = step.get("process_parameters", {})
        proc_data = [
            [Paragraph("<b>Critical Process Parameters:</b>", styles["MetaLabel"]), Paragraph(proc.get("critical_process_parameters", "N/A"), styles["BodyTextDark"])],
            [Paragraph("<b>Workup & Isolation:</b>", styles["MetaLabel"]), Paragraph(proc.get("workup_and_isolation", "N/A"), styles["BodyTextDark"])],
            [Paragraph("<b>Impurity Profile Risks:</b>", styles["MetaLabel"]), Paragraph(proc.get("impurity_profile_risks", "N/A"), styles["BodyTextDark"])]
        ]
        proc_table = Table(proc_data, colWidths=[130, content_width - 130])
        proc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["table_bg"]),
            ("GRID", (0, 0), (-1, -1), 0.5, theme["table_border"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        step_elements.append(proc_table)
        step_elements.append(Spacer(1, 6))
        step_elements.append(HRFlowable(width="100%", thickness=0.5, color=theme["rule_color"], spaceAfter=8))

        story.append(KeepTogether(step_elements))

    def canvas_factory(*args, **kwargs):
        return BrandedNumberedCanvas(*args, theme=theme, org_name=org_name, **kwargs)

    doc.build(story, canvasmaker=canvas_factory)
    pdf_buffer.seek(0)
    return pdf_buffer
