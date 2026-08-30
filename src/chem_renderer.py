import io
import re
import math
from PIL import Image, ImageDraw, ImageFont
from rdkit import Chem
from rdkit.Chem import AllChem, Draw
from rdkit.Chem.Draw import rdMolDraw2D

def parse_smiles_robust(smiles: str) -> Chem.Mol | None:
    """Robust multi-stage parser for single molecules, adducts, and complexes."""
    if not smiles or not isinstance(smiles, str):
        return None
    
    clean_smiles = smiles.strip().replace(" ", "")
    clean_smiles = re.sub(r'[‡†]', '', clean_smiles)
    clean_smiles = re.sub(r'--+', '-', clean_smiles)

    # 1. Standard RDKit parse
    mol = Chem.MolFromSmiles(clean_smiles)
    if mol:
        try:
            AllChem.Compute2DCoords(mol)
            return mol
        except Exception:
            return mol

    # 2. Permissive non-sanitized parse (for formal charges/chelates)
    try:
        mol = Chem.MolFromSmiles(clean_smiles, sanitize=False)
        if mol:
            mol.UpdatePropertyCache(strict=False)
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

    # 3. Disconnected fragment recovery
    if "." in clean_smiles:
        valid_frags = []
        for frag in clean_smiles.split("."):
            fmol = Chem.MolFromSmiles(frag, sanitize=False)
            if fmol:
                valid_frags.append(frag)
        if valid_frags:
            try:
                mol = Chem.MolFromSmiles(".".join(valid_frags), sanitize=False)
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


def render_molecule_to_pil(smiles: str, ref_mol: Chem.Mol = None, width: int = 220, height: int = 160) -> Image.Image:
    """Renders an intermediate molecule aligned with reference scaffold orientation."""
    mol = parse_smiles_robust(smiles)
    
    if mol:
        try:
            # Align 2D coordinates to parent reference scaffold if available
            if ref_mol:
                try:
                    AllChem.GenerateDepictionMatching2DStructure(mol, ref_mol)
                except Exception:
                    AllChem.Compute2DCoords(mol)
            else:
                AllChem.Compute2DCoords(mol)

            drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
            opts = drawer.drawOptions()
            opts.bondLineWidth = 2
            opts.clearBackground = True
            opts.padding = 0.08
            opts.additionalAtomLabelPadding = 0.05
            
            drawer.DrawMolecule(mol)
            drawer.FinishDrawing()
            return Image.open(io.BytesIO(drawer.GetDrawingText())).convert("RGBA")
        except Exception:
            pass

    # Fallback card
    img = Image.new("RGBA", (width, height), (248, 250, 252, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(4, 4), (width - 5, height - 5)], radius=6, outline="#94A3B8", width=1)
    
    display_text = smiles.strip() if smiles else "Intermediate Complex"
    if len(display_text) > 26:
        display_text = display_text[:24] + "..."
        
    font = ImageFont.load_default()
    draw.text((10, height // 2 - 12), "[Intermediate Structure]", fill="#1E40AF", font=font)
    draw.text((10, height // 2 + 4), display_text, fill="#334155", font=font)
    return img


def draw_annotated_arrow(
    draw: ImageDraw.ImageDraw, 
    x_start: int, 
    y: int, 
    length: int = 105, 
    arrow_type: str = "forward",
    label_top: str = "", 
    label_bottom: str = ""
):
    """Draws forward or equilibrium arrows with full, unclipped reagent strings."""
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

    # Top Label (e.g. + hydrazine hydrate)
    if label_top and label_top.strip().lower() != "none":
        draw.text((x_start + 2, y - 20), label_top.strip(), fill="#0F172A", font=font)
    
    # Bottom Label (e.g. - Cl-)
    if label_bottom and label_bottom.strip().lower() != "none":
        draw.text((x_start + 2, y + 8), label_bottom.strip(), fill="#475569", font=font)


def generate_mechanism_flowchart_image(pathway_steps: list, title: str = "(b) Reaction Mechanism") -> io.BytesIO | None:
    """
    Renders continuous publication-standard mechanism cascades with intermediate
    drawings and annotated reaction arrows.
    """
    if not pathway_steps:
        return None

    mol_w, mol_h = 220, 160
    arrow_w = 115
    padding = 24
    header_h = 45

    n_steps = len(pathway_steps)
    use_two_rows = n_steps > 3
    row1_count = math.ceil(n_steps / 2) if use_two_rows else n_steps
    
    total_w = padding * 2 + (row1_count * mol_w) + ((row1_count - 1) * arrow_w) + 20
    total_h = header_h + (mol_h + padding * 2) if not use_two_rows else header_h + (mol_h * 2 + 110 + padding * 2)

    canvas_img = Image.new("RGB", (int(total_w), int(total_h)), (255, 255, 255))
    draw = ImageDraw.Draw(canvas_img)
    font = ImageFont.load_default()

    # Border & Title Header
    draw.rectangle([(8, 8), (total_w - 8, total_h - 8)], outline="#CBD5E1", width=2)
    draw.text((padding, 16), title, fill="#0F172A", font=font)

    # Reference structure for scaffold alignment
    first_smiles = pathway_steps[0].get("intermediate_smiles") or pathway_steps[0].get("reactant_smiles", "")
    ref_mol = parse_smiles_robust(first_smiles)

    curr_y = header_h + padding

    # --- Row 1 Flow ---
    for i in range(row1_count):
        curr_x = padding + i * (mol_w + arrow_w)
        step_data = pathway_steps[i]
        
        smiles = step_data.get("intermediate_smiles") or step_data.get("reactant_smiles", "")
        mol_img = render_molecule_to_pil(smiles, ref_mol=ref_mol, width=mol_w, height=mol_h)
        canvas_img.paste(mol_img, (int(curr_x), int(curr_y)), mol_img)

        if i < row1_count - 1:
            arr_x = curr_x + mol_w + 4
            arr_y = curr_y + (mol_h // 2)
            arrow_type = step_data.get("arrow_type", "forward")
            lbl_top = step_data.get("reagents_in", "")
            lbl_bot = step_data.get("reagents_out", "")
            draw_annotated_arrow(draw, int(arr_x), int(arr_y), length=arrow_w - 8, arrow_type=arrow_type, label_top=lbl_top, label_bottom=lbl_bot)

    # --- Row 2 Flow (Serpentine) ---
    if use_two_rows:
        down_x = padding + (row1_count - 1) * (mol_w + arrow_w) + (mol_w // 2)
        down_y_start = curr_y + mol_h + 4
        last_r1_step = pathway_steps[row1_count - 1]
        
        # Draw vertical arrow
        y_end = down_y_start + 65
        draw.line([(down_x, down_y_start), (down_x, y_end)], fill="#0F172A", width=2)
        draw.polygon([(down_x, y_end), (down_x - 5, y_end - 10), (down_x, y_end - 7), (down_x + 5, y_end - 10)], fill="#0F172A")
        
        if last_r1_step.get("reagents_in"):
            draw.text((down_x - 70, down_y_start + 24), last_r1_step.get("reagents_in"), fill="#0F172A", font=font)
        if last_r1_step.get("reagents_out"):
            draw.text((down_x + 12, down_y_start + 24), last_r1_step.get("reagents_out"), fill="#475569", font=font)

        row2_y = curr_y + mol_h + 80
        row2_steps = pathway_steps[row1_count:]
        
        for j, step_data in enumerate(row2_steps):
            col_idx = (row1_count - 1) - j
            r2_x = padding + col_idx * (mol_w + arrow_w)
            
            smiles = step_data.get("intermediate_smiles", "")
            mol_img = render_molecule_to_pil(smiles, ref_mol=ref_mol, width=mol_w, height=mol_h)
            canvas_img.paste(mol_img, (int(r2_x), int(row2_y)), mol_img)

            if j < len(row2_steps) - 1:
                arr_x_start = r2_x - 10
                arr_x_end = arr_x_start - (arrow_w - 12)
                arr_y = row2_y + (mol_h // 2)
                draw.line([(arr_x_start, arr_y), (arr_x_end, arr_y)], fill="#0F172A", width=2)
                draw.polygon([(arr_x_end, arr_y), (arr_x_end + 10, arr_y - 5), (arr_x_end + 7, arr_y), (arr_x_end + 10, arr_y + 5)], fill="#0F172A")
                
                lbl_top = step_data.get("reagents_in", "")
                lbl_bot = step_data.get("reagents_out", "")
                if lbl_top and lbl_top.strip().lower() != "none":
                    draw.text((arr_x_end + 4, arr_y - 20), lbl_top.strip(), fill="#0F172A", font=font)
                if lbl_bot and lbl_bot.strip().lower() != "none":
                    draw.text((arr_x_end + 4, arr_y + 8), lbl_bot.strip(), fill="#475569", font=font)

    output = io.BytesIO()
    canvas_img.save(output, format="PNG", dpi=(300, 300))
    output.seek(0)
    return output
