import io
import re
import math
from PIL import Image, ImageDraw, ImageFont
from rdkit import Chem
from rdkit.Chem import AllChem, Draw

def parse_smiles_robust(smiles: str) -> Chem.Mol | None:
    """
    Multi-stage tolerant SMILES parser that handles organometallics, 
    coordination salts (dot-separated adducts), and non-standard valences.
    """
    if not smiles or not isinstance(smiles, str):
        return None
    
    # 1. Clean whitespace and non-standard pseudo-SMILES characters
    clean_smiles = smiles.strip().replace(" ", "")
    # Remove transition state daggers or dash notations
    clean_smiles = re.sub(r'[‡†]', '', clean_smiles)
    clean_smiles = re.sub(r'--+', '-', clean_smiles)

    # 2. Standard strict parse
    mol = Chem.MolFromSmiles(clean_smiles)
    if mol:
        try:
            AllChem.Compute2DCoords(mol)
            return mol
        except Exception:
            return mol

    # 3. Non-sanitized fallback (for coordination complexes & unusual valences)
    try:
        mol = Chem.MolFromSmiles(clean_smiles, sanitize=False)
        if mol:
            mol.UpdatePropertyCache(strict=False)
            # Apply safe sanitization flags while skipping rigid property/valence errors
            Chem.SanitizeMol(
                mol,
                Chem.SANITIZE_FINDRADICALS |
                Chem.SANITIZE_KEKULIZE |
                Chem.SANITIZE_SETAROMATICITY |
                Chem.SANITIZE_SETCONJUGATION |
                Chem.SANITIZE_SETHYBRIDIZATION |
                Chem.SANITIZE_SYMMRINGS,
                catchErrors=True
            )
            AllChem.Compute2DCoords(mol)
            return mol
    except Exception:
        pass

    # 4. Dot-separated major fragment recovery (if solvent/counterion part is malformed)
    if "." in clean_smiles:
        fragments = clean_smiles.split(".")
        valid_frags = []
        for frag in fragments:
            fmol = Chem.MolFromSmiles(frag, sanitize=False)
            if fmol:
                valid_frags.append(frag)
        if valid_frags:
            try:
                recovered_smiles = ".".join(valid_frags)
                mol = Chem.MolFromSmiles(recovered_smiles, sanitize=False)
                if mol:
                    mol.UpdatePropertyCache(strict=False)
                    AllChem.Compute2DCoords(mol)
                    return mol
            except Exception:
                pass

    return None


def render_reaction_scheme(rxn_smarts: str) -> io.BytesIO | None:
    """Renders high-level 2D reaction transformation (Reactants > Reagents > Products)."""
    try:
        rxn = AllChem.ReactionFromSmarts(rxn_smarts, useSmiles=True)
        drawer = Draw.MolDraw2DCairo(850, 220)
        opts = drawer.drawOptions()
        opts.bondLineWidth = 2
        opts.fixedFontSize = 13
        drawer.DrawReaction(rxn)
        drawer.FinishDrawing()
        
        output = io.BytesIO(drawer.GetDrawingText())
        output.seek(0)
        return output
    except Exception:
        return None


def render_molecule_to_pil(smiles: str, width: int = 210, height: int = 150) -> Image.Image:
    """Renders a single intermediate SMILES into a high-contrast PIL image."""
    mol = parse_smiles_robust(smiles)
    
    if mol:
        try:
            drawer = Draw.MolDraw2DCairo(width, height)
            opts = drawer.drawOptions()
            opts.bondLineWidth = 2
            opts.clearBackground = True
            opts.padding = 0.08
            drawer.DrawMolecule(mol)
            drawer.FinishDrawing()
            return Image.open(io.BytesIO(drawer.GetDrawingText())).convert("RGBA")
        except Exception:
            pass

    # Fallback: Clean chemical name/species card if molecule cannot be parsed
    img = Image.new("RGBA", (width, height), (248, 250, 252, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(4, 4), (width - 5, height - 5)], radius=6, outline="#94A3B8", width=1)
    
    display_text = smiles.strip() if smiles else "Intermediate Complex"
    if len(display_text) > 24:
        display_text = display_text[:22] + "..."
        
    font = ImageFont.load_default()
    draw.text((12, height // 2 - 12), f"[Complex / TS]", fill="#1E40AF", font=font)
    draw.text((12, height // 2 + 4), display_text, fill="#334155", font=font)
    return img


def draw_horizontal_arrow(
    draw: ImageDraw.ImageDraw, 
    x_start: int, 
    y: int, 
    length: int = 90, 
    arrow_type: str = "forward",
    label_top: str = "", 
    label_bottom: str = ""
):
    """Draws forward or equilibrium arrows with top/bottom reagent text."""
    x_end = x_start + length
    line_color = "#0F172A"
    font = ImageFont.load_default()

    if arrow_type == "equilibrium":
        draw.line([(x_start, y - 3), (x_end, y - 3)], fill=line_color, width=2)
        draw.polygon([(x_end, y - 3), (x_end - 8, y - 7), (x_end - 6, y - 3)], fill=line_color)
        draw.line([(x_start, y + 3), (x_end, y + 3)], fill=line_color, width=2)
        draw.polygon([(x_start, y + 3), (x_start + 8, y + 7), (x_start + 6, y + 3)], fill=line_color)
    else:
        draw.line([(x_start, y), (x_end, y)], fill=line_color, width=2)
        draw.polygon([(x_end, y), (x_end - 10, y - 5), (x_end - 7, y), (x_end - 10, y + 5)], fill=line_color)

    if label_top:
        draw.text((x_start + 4, y - 18), label_top, fill="#0F172A", font=font)
    if label_bottom:
        draw.text((x_start + 4, y + 6), label_bottom, fill="#475569", font=font)


def draw_vertical_arrow(
    draw: ImageDraw.ImageDraw, 
    x: int, 
    y_start: int, 
    length: int = 70, 
    label_left: str = "", 
    label_right: str = ""
):
    """Draws downward transition arrow with reagent labels."""
    y_end = y_start + length
    line_color = "#0F172A"
    font = ImageFont.load_default()

    draw.line([(x, y_start), (x, y_end)], fill=line_color, width=2)
    draw.polygon([(x, y_end), (x - 5, y_end - 10), (x, y_end - 7), (x + 5, y_end - 10)], fill=line_color)

    if label_left:
        draw.text((x - 65, y_start + (length // 2) - 8), label_left, fill="#0F172A", font=font)
    if label_right:
        draw.text((x + 12, y_start + (length // 2) - 8), label_right, fill="#475569", font=font)


def generate_mechanism_flowchart_image(pathway_steps: list, title: str = "(b) Reaction Mechanism") -> io.BytesIO | None:
    """
    Renders continuous publication-standard mechanism cascades with intermediate
    drawings and annotated reaction arrows.
    """
    if not pathway_steps:
        return None

    mol_w, mol_h = 205, 145
    arrow_w = 90
    padding = 24
    header_h = 45

    n_steps = len(pathway_steps)
    use_two_rows = n_steps > 3
    row1_count = math.ceil(n_steps / 2) if use_two_rows else n_steps
    
    total_w = padding * 2 + (row1_count * mol_w) + ((row1_count - 1) * arrow_w) + 20
    total_h = header_h + (mol_h + padding * 2) if not use_two_rows else header_h + (mol_h * 2 + 100 + padding * 2)

    canvas_img = Image.new("RGB", (int(total_w), int(total_h)), (255, 255, 255))
    draw = ImageDraw.Draw(canvas_img)
    font = ImageFont.load_default()

    # Border and Header Title
    draw.rectangle([(8, 8), (total_w - 8, total_h - 8)], outline="#CBD5E1", width=2)
    draw.text((padding, 16), title, fill="#0F172A", font=font)

    curr_y = header_h + padding

    # --- Row 1 Flow ---
    for i in range(row1_count):
        curr_x = padding + i * (mol_w + arrow_w)
        step_data = pathway_steps[i]
        
        smiles = step_data.get("intermediate_smiles") or step_data.get("reactant_smiles", "")
        mol_img = render_molecule_to_pil(smiles, width=mol_w, height=mol_h)
        canvas_img.paste(mol_img, (int(curr_x), int(curr_y)), mol_img)

        if i < row1_count - 1:
            arr_x = curr_x + mol_w + 5
            arr_y = curr_y + (mol_h // 2)
            arrow_type = step_data.get("arrow_type", "forward")
            lbl_top = step_data.get("reagents_in", "")
            lbl_bot = step_data.get("reagents_out", "")
            draw_horizontal_arrow(draw, int(arr_x), int(arr_y), length=arrow_w - 10, arrow_type=arrow_type, label_top=lbl_top, label_bottom=lbl_bot)

    # --- Row 2 Flow (Serpentine) ---
    if use_two_rows:
        down_x = padding + (row1_count - 1) * (mol_w + arrow_w) + (mol_w // 2)
        down_y_start = curr_y + mol_h + 5
        last_r1_step = pathway_steps[row1_count - 1]
        draw_vertical_arrow(
            draw, 
            int(down_x), 
            int(down_y_start), 
            length=60, 
            label_left=last_r1_step.get("reagents_in", ""), 
            label_right=last_r1_step.get("reagents_out", "")
        )

        row2_y = curr_y + mol_h + 75
        row2_steps = pathway_steps[row1_count:]
        
        for j, step_data in enumerate(row2_steps):
            col_idx = (row1_count - 1) - j
            r2_x = padding + col_idx * (mol_w + arrow_w)
            
            smiles = step_data.get("intermediate_smiles", "")
            mol_img = render_molecule_to_pil(smiles, width=mol_w, height=mol_h)
            canvas_img.paste(mol_img, (int(r2_x), int(row2_y)), mol_img)

            if j < len(row2_steps) - 1:
                arr_x_start = r2_x - 10
                arr_x_end = arr_x_start - (arrow_w - 15)
                arr_y = row2_y + (mol_h // 2)
                draw.line([(arr_x_start, arr_y), (arr_x_end, arr_y)], fill="#0F172A", width=2)
                draw.polygon([(arr_x_end, arr_y), (arr_x_end + 10, arr_y - 5), (arr_x_end + 7, arr_y), (arr_x_end + 10, arr_y + 5)], fill="#0F172A")
                
                lbl_top = step_data.get("reagents_in", "")
                lbl_bot = step_data.get("reagents_out", "")
                if lbl_top:
                    draw.text((arr_x_end + 4, arr_y - 18), lbl_top, fill="#0F172A", font=font)
                if lbl_bot:
                    draw.text((arr_x_end + 4, arr_y + 6), lbl_bot, fill="#475569", font=font)

    output = io.BytesIO()
    canvas_img.save(output, format="PNG", dpi=(300, 300))
    output.seek(0)
    return output
