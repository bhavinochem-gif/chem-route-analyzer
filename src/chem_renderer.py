import io
import re
import math
from PIL import Image, ImageDraw, ImageFont
from rdkit import Chem
from rdkit.Chem import AllChem

# Safe import for rdMolDraw2D if available
try:
    from rdkit.Chem.Draw import rdMolDraw2D
    HAS_RDKIT_DRAW = True
except Exception:
    HAS_RDKIT_DRAW = False

ARROW_COLOR = "#DC2626"  # Crimson Red for curved electron arrows

# Standard CPK Element Color Palette
CPK_COLORS = {
    "N": "#2563EB",   # Blue
    "O": "#DC2626",   # Red
    "F": "#0D9488",   # Teal
    "Cl": "#16A34A",  # Green
    "Br": "#991B1B",  # Maroon
    "I": "#7C3AED",   # Purple
    "S": "#D97706",   # Amber
    "P": "#EA580C",   # Orange
    "B": "#B45309",   # Brown
    "Na": "#475569",  # Slate
    "K": "#475569",   # Slate
    "Pd": "#0284C7",  # Sky Blue
    "C": "#0F172A",   # Dark Charcoal
    "H": "#64748B"    # Gray
}


def parse_smiles_robust(smiles: str) -> Chem.Mol | None:
    """Tolerant multi-stage parser for complex pharmaceutical SMILES and salts."""
    if not smiles or not isinstance(smiles, str):
        return None
    
    clean = smiles.strip().replace(" ", "")
    clean = re.sub(r'[‡†]', '', clean)
    clean = re.sub(r'--+', '-', clean)

    mol = Chem.MolFromSmiles(clean)
    if mol:
        try:
            AllChem.Compute2DCoords(mol)
            return mol
        except Exception:
            return mol

    try:
        mol = Chem.MolFromSmiles(clean, sanitize=False)
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

    if "." in clean:
        valid_frags = [f for f in clean.split(".") if Chem.MolFromSmiles(f, sanitize=False)]
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
    """Renders a smooth quadratic Bézier curve and terminal arrowhead."""
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


def draw_molecule_pure_pil(
    mol: Chem.Mol, 
    width: int = 240, 
    height: int = 170, 
    arrows: list[dict] = None
) -> Image.Image:
    """
    Renders 2D structures directly in PIL using RDKit conformer coordinates.
    Guarantees structural rendering without Cairo or X11 dependencies.
    """
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    if not mol or mol.GetNumAtoms() == 0:
        return img

    if mol.GetNumConformers() == 0:
        AllChem.Compute2DCoords(mol)
    conf = mol.GetConformer()

    xs = [conf.GetAtomPosition(i).x for i in range(mol.GetNumAtoms())]
    ys = [conf.GetAtomPosition(i).y for i in range(mol.GetNumAtoms())]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    dx = max_x - min_x if max_x != min_x else 1.0
    dy = max_y - min_y if max_y != min_y else 1.0

    margin = 28
    scale = min((width - 2 * margin) / dx, (height - 2 * margin) / dy)

    def to_canvas(x, y):
        cx = margin + (x - min_x) * scale + ((width - 2 * margin) - dx * scale) / 2.0
        cy = height - (margin + (y - min_y) * scale + ((height - 2 * margin) - dy * scale) / 2.0)
        return cx, cy

    atom_coords = {}
    for i in range(mol.GetNumAtoms()):
        pos = conf.GetAtomPosition(i)
        atom_coords[i] = to_canvas(pos.x, pos.y)

    # 1. Draw Bonds
    for bond in mol.GetBonds():
        i1 = bond.GetBeginAtomIdx()
        i2 = bond.GetEndAtomIdx()
        p1 = atom_coords[i1]
        p2 = atom_coords[i2]

        b_type = bond.GetBondType()
        bx = p2[0] - p1[0]
        by = p2[1] - p1[1]
        dist = math.hypot(bx, by)
        if dist == 0:
            continue

        nx = -by / dist
        ny = bx / dist

        if b_type == Chem.BondType.DOUBLE:
            offset = 2.0
            draw.line([(p1[0] + nx * offset, p1[1] + ny * offset), (p2[0] + nx * offset, p2[1] + ny * offset)], fill="#1E293B", width=2)
            draw.line([(p1[0] - nx * offset, p1[1] - ny * offset), (p2[0] - nx * offset, p2[1] - ny * offset)], fill="#1E293B", width=2)
        elif b_type == Chem.BondType.TRIPLE:
            offset = 3.2
            draw.line([p1, p2], fill="#1E293B", width=2)
            draw.line([(p1[0] + nx * offset, p1[1] + ny * offset), (p2[0] + nx * offset, p2[1] + ny * offset)], fill="#1E293B", width=1)
            draw.line([(p1[0] - nx * offset, p1[1] - ny * offset), (p2[0] - nx * offset, p2[1] - ny * offset)], fill="#1E293B", width=1)
        elif b_type == Chem.BondType.AROMATIC:
            offset = 2.2
            draw.line([p1, p2], fill="#1E293B", width=2)
            # Dashed inner resonance bond
            dash_steps = max(3, int(dist / 6))
            for s in range(dash_steps):
                if s % 2 == 0:
                    t_s = s / float(dash_steps)
                    t_e = (s + 0.8) / float(dash_steps)
                    d_p1 = (p1[0] + bx * t_s + nx * offset, p1[1] + by * t_s + ny * offset)
                    d_p2 = (p1[0] + bx * t_e + nx * offset, p1[1] + by * t_e + ny * offset)
                    draw.line([d_p1, d_p2], fill="#475569", width=1)
        else:
            # Standard single bond
            draw.line([p1, p2], fill="#1E293B", width=2)

    # 2. Draw Heteroatoms and Charges
    for i in range(mol.GetNumAtoms()):
        atom = mol.GetAtomWithIdx(i)
        sym = atom.GetSymbol()
        charge = atom.GetFormalCharge()
        num_h = atom.GetTotalNumH()

        if sym == "C" and charge == 0:
            continue

        lbl = sym
        if num_h == 1:
            lbl += "H"
        elif num_h > 1:
            lbl += f"H{num_h}"

        if charge == 1:
            lbl += "⁺"
        elif charge == -1:
            lbl += "⁻"
        elif charge > 1:
            lbl += f"^{charge}+"
        elif charge < -1:
            lbl += f"^{abs(charge)}-"

        pt = atom_coords[i]
        c_color = CPK_COLORS.get(sym, "#0F172A")

        # White pill background to mask underlying bond lines
        bbox = draw.textbbox((pt[0], pt[1]), lbl, font=font, anchor="mm")
        draw.rectangle([(bbox[0] - 2, bbox[1] - 1), (bbox[2] + 2, bbox[3] + 1)], fill=(255, 255, 255, 240))
        draw.text(pt, lbl, fill=c_color, font=font, anchor="mm")

    # 3. Draw Mechanistic Curved Arrows
    if arrows:
        for arr in arrows:
            s_type = arr.get("source_type", "atom")
            s_indices = arr.get("source_indices", [])
            t_type = arr.get("target_type", "atom")
            t_indices = arr.get("target_indices", [])
            direction = arr.get("curvature_direction", "clockwise")

            p0 = None
            p2 = None

            if s_type == "atom" and s_indices and s_indices[0] in atom_coords:
                p0 = atom_coords[s_indices[0]]
            elif len(s_indices) >= 2 and s_indices[0] in atom_coords and s_indices[1] in atom_coords:
                a1 = atom_coords[s_indices[0]]
                a2 = atom_coords[s_indices[1]]
                p0 = ((a1[0] + a2[0]) / 2.0, (a1[1] + a2[1]) / 2.0)

            if t_type == "atom" and t_indices and t_indices[0] in atom_coords:
                p2 = atom_coords[t_indices[0]]
            elif len(t_indices) >= 2 and t_indices[0] in atom_coords and t_indices[1] in atom_coords:
                a1 = atom_coords[t_indices[0]]
                a2 = atom_coords[t_indices[1]]
                p2 = ((a1[0] + a2[0]) / 2.0, (a1[1] + a2[1]) / 2.0)

            if p0 and p2:
                dx = p2[0] - p0[0]
                dy = p2[1] - p0[1]
                dist = math.hypot(dx, dy)
                if dist < 8:
                    continue

                backoff = min(10.0, dist * 0.22)
                p2_adj = (p2[0] - (dx / dist) * backoff, p2[1] - (dy / dist) * backoff)
                mid_x = (p0[0] + p2_adj[0]) / 2.0
                mid_y = (p0[1] + p2_adj[1]) / 2.0

                nx = -dy / dist
                ny = dx / dist
                curvature_sign = 1 if direction == "clockwise" else -1
                h = max(20.0, dist * 0.35) * curvature_sign
                p1 = (mid_x + nx * h, mid_y + ny * h)

                draw_bezier_curve(draw, p0, p1, p2_adj, color=ARROW_COLOR, width=2)

    return img


def render_molecule_with_mechanistic_arrows(
    smiles: str, 
    arrows: list[dict] = None, 
    ref_mol = None, 
    width: int = 240, 
    height: int = 170
) -> Image.Image:
    """Primary renderer attempting rdMolDraw2D, falling back safely to draw_molecule_pure_pil."""
    mol = parse_smiles_robust(smiles)
    if not mol:
        # Fallback card only if SMILES is fundamentally unparseable
        img = Image.new("RGBA", (width, height), (248, 250, 252, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(4, 4), (width - 5, height - 5)], radius=6, outline="#CBD5E1", width=1)
        font = ImageFont.load_default()
        draw.text((10, height // 2 - 6), smiles[:24] if smiles else "Structure", fill="#334155", font=font)
        return img

    if HAS_RDKIT_DRAW:
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
            
            # If arrows are present, draw them directly onto the image
            if arrows:
                draw = ImageDraw.Draw(base_img)
                conf = mol.GetConformer()
                atom_coords = {i: (drawer.GetDrawCoords(conf.GetAtomPosition(i)).x, drawer.GetDrawCoords(conf.GetAtomPosition(i)).y) for i in range(mol.GetNumAtoms())}
                for arr in arrows:
                    s_indices = arr.get("source_indices", [])
                    t_indices = arr.get("target_indices", [])
                    direction = arr.get("curvature_direction", "clockwise")
                    if s_indices and t_indices and s_indices[0] in atom_coords and t_indices[0] in atom_coords:
                        p0 = atom_coords[s_indices[0]]
                        p2 = atom_coords[t_indices[0]]
                        dx, dy = p2[0] - p0[0], p2[1] - p0[1]
                        dist = math.hypot(dx, dy)
                        if dist >= 8:
                            p2_adj = (p2[0] - (dx / dist) * 10, p2[1] - (dy / dist) * 10)
                            mid_x, mid_y = (p0[0] + p2_adj[0]) / 2.0, (p0[1] + p2_adj[1]) / 2.0
                            nx, ny = -dy / dist, dx / dist
                            h = max(20.0, dist * 0.35) * (1 if direction == "clockwise" else -1)
                            draw_bezier_curve(draw, p0, (mid_x + nx * h, mid_y + ny * h), p2_adj, color=ARROW_COLOR, width=2)

            return base_img
        except Exception:
            pass

    # Pure PIL renderer (works anywhere without C-graphics libraries)
    return draw_molecule_pure_pil(mol, width=width, height=height, arrows=arrows)


def render_reaction_scheme(
    rxn_smarts: str, 
    sm_smiles: str = "", 
    prod_smiles: str = "", 
    conditions: str = ""
) -> io.BytesIO | None:
    """Renders high-level transformation schemes, falling back to a stitched reactant -> product diagram."""
    # 1. Attempt standard RDKit Reaction drawing
    if HAS_RDKIT_DRAW and rxn_smarts and ">" in rxn_smarts:
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
            pass

    # 2. Resilient Fallback: Render Reactants + Arrow + Products directly via PIL
    try:
        left_smiles = sm_smiles
        right_smiles = prod_smiles

        if not left_smiles and rxn_smarts and ">>" in rxn_smarts:
            left_smiles, right_smiles = rxn_smarts.split(">>")[:2]

        left_img = render_molecule_with_mechanistic_arrows(left_smiles, width=280, height=180)
        right_img = render_molecule_with_mechanistic_arrows(right_smiles, width=280, height=180)

        canvas_w = 780
        canvas_h = 190
        scheme_canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
        scheme_canvas.paste(left_img, (20, 5), left_img)
        scheme_canvas.paste(right_img, (480, 5), right_img)

        draw = ImageDraw.Draw(scheme_canvas)
        font = ImageFont.load_default()

        # Center Reaction Arrow
        arr_x1 = 315
        arr_x2 = 465
        arr_y = 95
        draw.line([(arr_x1, arr_y), (arr_x2, arr_y)], fill="#0F172A", width=2)
        draw.polygon([(arr_x2, arr_y), (arr_x2 - 10, arr_y - 5), (arr_x2 - 7, arr_y), (arr_x2 - 10, arr_y + 5)], fill="#0F172A")

        if conditions:
            draw.text((arr_x1 + 10, arr_y - 20), conditions[:32], fill="#0F172A", font=font)

        buf = io.BytesIO()
        scheme_canvas.save(buf, format="PNG", dpi=(300, 300))
        buf.seek(0)
        return buf
    except Exception:
        return None


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
