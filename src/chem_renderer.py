import io
import re
import math
from PIL import Image, ImageDraw, ImageFont

# Graceful RDKit imports to prevent unhandled container startup crashes
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit.Chem import Draw
    from rdkit.Chem.Draw import rdMolDraw2D
    HAS_RDKIT_DRAW = True
    RDKIT_DRAW_ERROR = None
except Exception as e:
    HAS_RDKIT_DRAW = False
    RDKIT_DRAW_ERROR = str(e)
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except Exception:
        Chem = None
        AllChem = None

ARROW_COLOR = "#DC2626"  # Crimson Red for electron-pushing arrows


def parse_smiles_robust(smiles: str):
    """Robust multi-stage parser for single molecules, adducts, and complexes."""
    if not Chem or not smiles or not isinstance(smiles, str):
        return None
    
    clean_smiles = smiles.strip().replace(" ", "")
    clean_smiles = re.sub(r'[‡†]', '', clean_smiles)
    clean_smiles = re.sub(r'--+', '-', clean_smiles)

    mol = Chem.MolFromSmiles(clean_smiles)
    if mol:
        try:
            AllChem.Compute2DCoords(mol)
            return mol
        except Exception:
            return mol

    try:
        mol = Chem.MolFromSmiles(clean_smiles, sanitize=False)
        if mol:
            mol.UpdatePropertyCache(strict=False)
            Chem.SanitizeMol(
                mol,
                Chem.SANITIZE_FINDRADICALS | Chem.SANITIZE_KEKULIZE |
                Chem.SANITIZE_SETAROMATICITY | Chem.SANITIZE_SETCONJUGATION |
                Chem.SANITIZE_SETHYBRIDIZATION | Chem.SANITIZE_SYMMRINGS,
                catchErrors=True
            )
            AllChem.Compute2DCoords(mol)
            return mol
    except Exception:
        pass

    if "." in clean_smiles:
        valid_frags = [frag for frag in clean_smiles.split(".") if Chem.MolFromSmiles(frag, sanitize=False)]
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


def draw_bezier_curve(
    draw: ImageDraw.ImageDraw, 
    p0: tuple[float, float], 
    p1: tuple[float, float], 
    p2: tuple[float, float], 
    color: str = ARROW_COLOR, 
    width: int = 2, 
    num_points: int = 30
):
    """Renders a smooth quadratic Bézier curve with terminal arrowhead."""
    points = []
    for i in range(num_points + 1):
        t = i / float(num_points)
        x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        points.append((x, y))

    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=color, width=width)

    tangent_x = p2[0] - p1[0]
    tangent_y = p2[1] - p1[1]
    angle = math.atan2(tangent_y, tangent_x)

    arrow_len = 9
    arrow_angle = math.pi / 6

    x_tip, y_tip = p2
    x_left = x_tip - arrow_len * math.cos(angle - arrow_angle)
    y_left = y_tip - arrow_len * math.sin(angle - arrow_angle)
    x_right = x_tip - arrow_len * math.cos(angle + arrow_angle)
    y_right = y_tip - arrow_len * math.sin(angle + arrow_angle)

    draw.polygon([(x_tip, y_tip), (x_left, y_left), (x_right, y_right)], fill=color)


def get_feature_pixel_coords(drawer, mol, feature_type: str, indices: list[int]):
    """Calculates exact canvas pixel coordinates for an atom or bond midpoint."""
    try:
        conf = mol.GetConformer()
        num_atoms = mol.GetNumAtoms()
        valid_indices = [idx for idx in indices if 0 <= idx < num_atoms]
        if not valid_indices:
            return None

        if feature_type == "atom":
            p3d = conf.GetAtomPosition(valid_indices[0])
            p2d = drawer.GetDrawCoords(p3d)
            return (p2d.x, p2d.y)

        elif feature_type in ["bond", "between_atoms"]:
            if len(valid_indices) >= 2:
                p3d_1 = conf.GetAtomPosition(valid_indices[0])
                p3d_2 = conf.GetAtomPosition(valid_indices[1])
                p2d_1 = drawer.GetDrawCoords(p3d_1)
                p2d_2 = drawer.GetDrawCoords(p3d_2)
                return ((p2d_1.x + p2d_2.x) / 2.0, (p2d_1.y + p2d_2.y) / 2.0)
            else:
                p3d = conf.GetAtomPosition(valid_indices[0])
                p2d = drawer.GetDrawCoords(p3d)
                return (p2d.x, p2d.y)
    except Exception:
        pass
    return None


def render_molecule_with_mechanistic_arrows(
    smiles: str, 
    arrows: list[dict] = None, 
    ref_mol = None, 
    width: int = 240, 
    height: int = 170
) -> Image.Image:
    """Renders 2D molecule with atom-anchored Bézier curved arrows or fallback card."""
    mol = parse_smiles_robust(smiles)

    if HAS_RDKIT_DRAW and mol:
        try:
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
            opts.padding = 0.12

            drawer.DrawMolecule(mol)
            drawer.FinishDrawing()

            base_img = Image.open(io.BytesIO(drawer.GetDrawingText())).convert("RGBA")
            draw = ImageDraw.Draw(base_img)

            if arrows:
                for arr in arrows:
                    s_type = arr.get("source_type", "atom")
                    s_indices = arr.get("source_indices", [])
                    t_type = arr.get("target_type", "atom")
                    t_indices = arr.get("target_indices", [])
                    direction = arr.get("curvature_direction", "clockwise")

                    p0 = get_feature_pixel_coords(drawer, mol, s_type, s_indices)
                    p2 = get_feature_pixel_coords(drawer, mol, t_type, t_indices)

                    if p0 and p2:
                        dx = p2[0] - p0[0]
                        dy = p2[1] - p0[1]
                        dist = math.hypot(dx, dy)
                        if dist < 8:
                            continue

                        backoff = min(12.0, dist * 0.25)
                        p2_adj = (p2[0] - (dx / dist) * backoff, p2[1] - (dy / dist) * backoff)

                        mid_x = (p0[0] + p2_adj[0]) / 2.0
                        mid_y = (p0[1] + p2_adj[1]) / 2.0

                        nx = -dy / dist
                        ny = dx / dist

                        curvature_sign = 1 if direction == "clockwise" else -1
                        h = max(22.0, dist * 0.38) * curvature_sign

                        p1 = (mid_x + nx * h, mid_y + ny * h)
                        draw_bezier_curve(draw, p0, p1, p2_adj, color=ARROW_COLOR, width=2)

            return base_img
        except Exception:
            pass

    # High-contrast fallback card if RDKit drawing is unavailable
    img = Image.new("RGBA", (width, height), (248, 250, 252, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(4, 4), (width - 5, height - 5)], radius=6, outline="#CBD5E1", width=1)
    font = ImageFont.load_default()
    
    display_text = smiles.strip() if smiles else "Structure"
    if len(display_text) > 24:
        display_text = display_text[:22] + "..."
    draw.text((10, height // 2 - 12), "[Intermediate Structure]", fill="#1E40AF", font=font)
    draw.text((10, height // 2 + 4), display_text, fill="#334155", font=font)
    return img


def draw_annotated_arrow(
    draw: ImageDraw.ImageDraw, 
    x_start: int, 
    y: int, 
    length: int = 100, 
    arrow_type: str = "forward",
    label_top: str = "", 
    label_bottom: str = ""
):
    """Draws inter-molecular reaction step arrows between cards."""
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

    if label_top and label_top.strip().lower() != "none":
        draw.text((x_start + 2, y - 20), label_top.strip(), fill="#0F172A", font=font)
    if label_bottom and label_bottom.strip().lower() != "none":
        draw.text((x_start + 2, y + 8), label_bottom.strip(), fill="#475569", font=font)


def render_reaction_scheme(rxn_smarts: str) -> io.BytesIO | None:
    """Renders high-level 2D reaction transformation."""
    if not HAS_RDKIT_DRAW or not rxn_smarts:
        return None
    try:
        rxn = AllChem.ReactionFromSmarts(rxn_smarts, useSmiles=True)
        drawer = rdMolDraw2D.MolDraw2DCairo(850, 220)
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


def generate_mechanism_flowchart_image(pathway_steps: list, title: str = "(b) Reaction Mechanism") -> io.BytesIO | None:
    """Renders continuous mechanism cascade flowchart with intermediate drawings and reaction arrows."""
    if not pathway_steps:
        return None

    mol_w, mol_h = 240, 170
    arrow_w = 110
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

    draw.rectangle([(8, 8), (total_w - 8, total_h - 8)], outline="#CBD5E1", width=2)
    draw.text((padding, 16), title, fill="#0F172A", font=font)

    first_smiles = pathway_steps[0].get("intermediate_smiles") or pathway_steps[0].get("reactant_smiles", "")
    ref_mol = parse_smiles_robust(first_smiles)

    curr_y = header_h + padding

    for i in range(row1_count):
        curr_x = padding + i * (mol_w + arrow_w)
        step_data = pathway_steps[i]
        
        smiles = step_data.get("intermediate_smiles") or step_data.get("reactant_smiles", "")
        arrows = step_data.get("electron_arrows", [])
        
        mol_img = render_molecule_with_mechanistic_arrows(smiles, arrows=arrows, ref_mol=ref_mol, width=mol_w, height=mol_h)
        canvas_img.paste(mol_img, (int(curr_x), int(curr_y)), mol_img)

        if i < row1_count - 1:
            arr_x = curr_x + mol_w + 4
            arr_y = curr_y + (mol_h // 2)
            arrow_type = step_data.get("arrow_type", "forward")
            lbl_top = step_data.get("reagents_in", "")
            lbl_bot = step_data.get("reagents_out", "")
            draw_annotated_arrow(draw, int(arr_x), int(arr_y), length=arrow_w - 8, arrow_type=arrow_type, label_top=lbl_top, label_bottom=lbl_bot)

    if use_two_rows:
        down_x = padding + (row1_count - 1) * (mol_w + arrow_w) + (mol_w // 2)
        down_y_start = curr_y + mol_h + 4
        last_r1_step = pathway_steps[row1_count - 1]
        
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
            arrows = step_data.get("electron_arrows", [])
            mol_img = render_molecule_with_mechanistic_arrows(smiles, arrows=arrows, ref_mol=ref_mol, width=mol_w, height=mol_h)
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
