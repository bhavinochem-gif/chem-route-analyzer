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

from src.chem_renderer import render_reaction_scheme, render_molecule_smiles

THEMES = {
    "Pharma Blue (Default)": {
        "primary": colors.HexColor("#1E3A8A"),
        "secondary": colors.HexColor("#2563EB"),
        "accent_bg": colors.HexColor("#EFF6FF"),
        "accent_border": colors.HexColor("#BFDBFE"),
        "mech_bg": colors.HexColor("#FAF5FF"),
        "mech_border": colors.HexColor("#E9D5FF"),
        "ipc_header_bg": colors.HexColor("#1E3A8A"),
        "ipc_header_text": colors.HexColor("#FFFFFF"),
        "text_dark": colors.HexColor("#0F172A"),
        "text_muted": colors.HexColor("#64748B"),
        "table_bg": colors.HexColor("#F8FAFC"),
        "table_alt_bg": colors.HexColor("#F1F5F9"),
        "table_border": colors.HexColor("#CBD5E1"),
        "rule_color": colors.HexColor("#CBD5E1")
    },
    "Emerald Biotech": {
        "primary": colors.HexColor("#065F46"),
        "secondary": colors.HexColor("#059669"),
        "accent_bg": colors.HexColor("#ECFDF5"),
        "accent_border": colors.HexColor("#A7F3D0"),
        "mech_bg": colors.HexColor("#F0FDF4"),
        "mech_border": colors.HexColor("#BBF7D0"),
        "ipc_header_bg": colors.HexColor("#065F46"),
        "ipc_header_text": colors.HexColor("#FFFFFF"),
        "text_dark": colors.HexColor("#064E3B"),
        "text_muted": colors.HexColor("#4B5563"),
        "table_bg": colors.HexColor("#F9FAFB"),
        "table_alt_bg": colors.HexColor("#F3F4F6"),
        "table_border": colors.HexColor("#D1D5DB"),
        "rule_color": colors.HexColor("#D1D5DB")
    },
    "Crimson Process R&D": {
        "primary": colors.HexColor("#881337"),
        "secondary": colors.HexColor("#BE123C"),
        "accent_bg": colors.HexColor("#FFF1F2"),
        "accent_border": colors.HexColor("#FECDD3"),
        "mech_bg": colors.HexColor("#FFFBEB"),
        "mech_border": colors.HexColor("#FDE68A"),
        "ipc_header_bg": colors.HexColor("#881337"),
        "ipc_header_text": colors.HexColor("#FFFFFF"),
        "text_dark": colors.HexColor("#4C0519"),
        "text_muted": colors.HexColor("#71717A"),
        "table_bg": colors.HexColor("#FAFAFA"),
        "table_alt_bg": colors.HexColor("#F4F4F5"),
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
        self.drawRightString(letter[0] - 54, letter[1] - 36, "Analytical Specifications & Synthesis Dossier")
        
        self.setStrokeColor(self.theme["rule_color"])
        self.setLineWidth(0.5)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
        
        self.line(54, 45, letter[0] - 54, 45)
        self.drawString(54, 32, "CONFIDENTIAL — PROCESS R&D & ANALYTICAL DEVELOPMENT")
        self.drawRightString(letter[0] - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_report_styles(theme):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocTitle", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=theme["primary"]))
    styles.add(ParagraphStyle(name="SectionHeader", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=theme["primary"], spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle(name="SubSectionHeader", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=theme["secondary"], spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle(name="StepTitle", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=theme["secondary"], spaceBefore=6, spaceAfter=4))
    styles.add(ParagraphStyle(name="BodyTextDark", fontName="Helvetica", fontSize=8, leading=10.5, textColor=theme["text_dark"]))
    styles.add(ParagraphStyle(name="IPCTableHeader", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=theme["ipc_header_text"]))
    styles.add(ParagraphStyle(name="MetaLabel", fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=theme["text_muted"]))
    styles.add(ParagraphStyle(name="MetaValue", fontName="Helvetica", fontSize=8, leading=10, textColor=theme["text_dark"]))
    return styles

def create_ipc_and_analytical_flowables(step_data: dict, styles, theme, content_width: float) -> list:
    flowables = []
    analytical_info = step_data.get("analytical_and_ipc", {})
    if not analytical_info:
        return flowables

    flowables.append(Spacer(1, 4))
    flowables.append(Paragraph("<b>In-Process Control (IPC) & Analytical Release Specifications</b>", styles["SubSectionHeader"]))
    
    ipc_list = analytical_info.get("ipc_checkpoints", [])
    if ipc_list:
        table_rows = [
            [
                Paragraph("<b>Sampling Stage / Checkpoint</b>", styles["IPCTableHeader"]),
                Paragraph("<b>Analytical Technique</b>", styles["IPCTableHeader"]),
                Paragraph("<b>Acceptance Criteria / Limit</b>", styles["IPCTableHeader"])
            ]
        ]
        for item in ipc_list:
            table_rows.append([
                Paragraph(item.get("stage", "IPC Point"), styles["BodyTextDark"]),
                Paragraph(item.get("technique", "HPLC/GC"), styles["BodyTextDark"]),
                Paragraph(item.get("acceptance_criteria", "N/A"), styles["BodyTextDark"])
            ])

        col_w1 = content_width * 0.32
        col_w2 = content_width * 0.28
        col_w3 = content_width * 0.40

        ipc_table = Table(table_rows, colWidths=[col_w1, col_w2, col_w3])
        ts = [
            ("BACKGROUND", (0, 0), (-1, 0), theme["ipc_header_bg"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, theme["table_border"]),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]
        for row_idx in range(1, len(table_rows)):
            bg_col = theme["table_alt_bg"] if row_idx % 2 == 0 else theme["table_bg"]
            ts.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg_col))

        ipc_table.setStyle(TableStyle(ts))
        flowables.append(ipc_table)
        flowables.append(Spacer(1, 5))

    char = analytical_info.get("characterization", {})
    if char:
        char_data = [
            [Paragraph("<b>HPLC / Assay Method:</b>", styles["MetaLabel"]), Paragraph(char.get("hplc_assay_desc", "N/A"), styles["BodyTextDark"])],
            [Paragraph("<b>Diagnostic <sup>1</sup>H NMR Signals:</b>", styles["MetaLabel"]), Paragraph(char.get("nmr_diagnostic_peaks", "N/A"), styles["BodyTextDark"])],
            [Paragraph("<b>Mass Spec (m/z) Target:</b>", styles["MetaLabel"]), Paragraph(char.get("mass_spec_target", "N/A"), styles["BodyTextDark"])]
        ]
        char_table = Table(char_data, colWidths=[130, content_width - 130])
        char_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["accent_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.5, theme["accent_border"]),
            ("GRID", (0, 0), (-1, -1), 0.5, theme["accent_border"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 3.5),
        ]))
        flowables.append(char_table)

    return flowables

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

    title_paragraphs = [
        Paragraph(f"<b>{org_name}</b>", styles["MetaLabel"]),
        Paragraph("Synthesis Route & Analytical Release Dossier", styles["DocTitle"]),
        Spacer(1, 3),
        Paragraph(f"<b>File:</b> {file_name} &nbsp;|&nbsp; <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')} &nbsp;|&nbsp; <b>Steps:</b> {len(route_data.get('steps', []))}", styles["MetaValue"])
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

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=theme["primary"], spaceAfter=8))

    overview_text = route_data.get("overall_route_summary", "No route summary available.")
    overview_box = Table(
        [[Paragraph("<b>Synthetic Route Strategy Overview</b>", styles["SectionHeader"])],
         [Paragraph(overview_text, styles["BodyTextDark"])]],
        colWidths=[content_width]
    )
    overview_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), theme["accent_bg"]),
        ("BOX", (0, 0), (-1, -1), 1, theme["accent_border"]),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(overview_box)
    story.append(Spacer(1, 10))

    for step in route_data.get("steps", []):
        step_elements = []
        step_num = step.get("step_number", 1)
        rxn_name = step.get("reaction_name", "Unclassified Transformation")
        
        step_elements.append(Paragraph(f"Step {step_num}: {rxn_name}", styles["StepTitle"]))
        
        conditions = step.get("reagents_solvents_conditions", "N/A")
        cond_table = Table(
            [[Paragraph("<b>Conditions & Reagents:</b>", styles["MetaLabel"]), Paragraph(conditions, styles["BodyTextDark"])]],
            colWidths=[120, content_width - 120]
        )
        cond_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["table_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.5, theme["table_border"]),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        step_elements.append(cond_table)
        step_elements.append(Spacer(1, 5))

        rxn_smarts = step.get("reaction_smarts", "")
        img_flowable = None

        if rxn_smarts and ">" in rxn_smarts:
            rxn_buf = render_reaction_scheme(rxn_smarts)
            if rxn_buf:
                img_flowable = RLImage(rxn_buf, width=content_width, height=120)

        if not img_flowable:
            sm_buf = render_molecule_smiles(step.get("starting_material_smiles", ""))
            prod_buf = render_molecule_smiles(step.get("product_smiles", ""))
            if sm_buf and prod_buf:
                mol_cells = [[
                    RLImage(sm_buf, width=220, height=110),
                    Paragraph("<b>➔</b>", ParagraphStyle('Arrow', fontName='Helvetica-Bold', fontSize=16, alignment=1, textColor=theme["secondary"])),
                    RLImage(prod_buf, width=220, height=110)
                ]]
                img_table = Table(mol_cells, colWidths=[230, 44, 230])
                img_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                img_flowable = img_table

        if img_flowable:
            step_elements.append(img_flowable)
            step_elements.append(Spacer(1, 5))

        mech = step.get("mechanism", {})
        mech_lines = [f"<b>Mechanism Class:</b> {mech.get('mechanism_type', 'N/A')}"]
        for idx, flow in enumerate(mech.get("arrow_pushing_description", []), 1):
            mech_lines.append(f"<b>{idx}.</b> {flow}")

        intermediates = mech.get("key_intermediates", [])
        if intermediates:
            inter_str = ", ".join([f"<i>{item.get('name')}:</i> {item.get('smiles_or_desc')}" for item in intermediates])
            mech_lines.append(f"<b>Key Intermediates:</b> {inter_str}")

        mech_paragraphs = [Paragraph(line, styles["BodyTextDark"]) for line in mech_lines]
        mech_box = Table([[Paragraph("<b>Electron-Pushing Mechanism</b>", styles["SectionHeader"])], [mech_paragraphs]], colWidths=[content_width])
        mech_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["mech_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.5, theme["mech_border"]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        step_elements.append(mech_box)
        step_elements.append(Spacer(1, 5))

        proc = step.get("process_parameters", {})
        proc_data = [
            [Paragraph("<b>Critical Process Parameters (CPPs):</b>", styles["MetaLabel"]), Paragraph(proc.get("critical_process_parameters", "N/A"), styles["BodyTextDark"])],
            [Paragraph("<b>Workup & Isolation Procedure:</b>", styles["MetaLabel"]), Paragraph(proc.get("workup_and_isolation", "N/A"), styles["BodyTextDark"])],
            [Paragraph("<b>Impurity Profile Risks:</b>", styles["MetaLabel"]), Paragraph(proc.get("impurity_profile_risks", "N/A"), styles["BodyTextDark"])]
        ]
        proc_table = Table(proc_data, colWidths=[140, content_width - 140])
        proc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), theme["table_bg"]),
            ("GRID", (0, 0), (-1, -1), 0.5, theme["table_border"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 3.5),
        ]))
        step_elements.append(proc_table)

        analytical_flowables = create_ipc_and_analytical_flowables(step, styles, theme, content_width)
        step_elements.extend(analytical_flowables)

        step_elements.append(Spacer(1, 6))
        step_elements.append(HRFlowable(width="100%", thickness=0.5, color=theme["rule_color"], spaceAfter=8))

        story.append(KeepTogether(step_elements))

    def canvas_factory(*args, **kwargs):
        return BrandedNumberedCanvas(*args, theme=theme, org_name=org_name, **kwargs)

    doc.build(story, canvasmaker=canvas_factory)
    pdf_buffer.seek(0)
    return pdf_buffer
