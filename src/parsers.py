import io
import re
import struct
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image
import pdf2image
from rdkit import Chem

PERIODIC_TABLE = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
    "K": 19, "Ca": 20, "Br": 35, "I": 53
}

BOND_ORDER_MAP = {
    1: Chem.BondType.SINGLE,
    2: Chem.BondType.DOUBLE,
    3: Chem.BondType.TRIPLE,
    4: Chem.BondType.AROMATIC
}


def extract_strings_from_binary(file_bytes: bytes, min_len: int = 3) -> list[str]:
    """Extracts printable ASCII and UTF-8 strings from binary streams."""
    pattern = rb'[\w\s\(\)\[\]\{\}\-\+\=\#\:\@\/\.\,\>\<\\\%]{' + str(min_len).encode() + rb',}'
    raw_matches = re.findall(pattern, file_bytes)
    cleaned = []
    for match in raw_matches:
        try:
            decoded = match.decode('utf-8', errors='ignore').strip()
            if len(decoded) >= min_len and not decoded.isnumeric():
                cleaned.append(decoded)
        except Exception:
            continue
    return cleaned


def parse_cdxml_to_molecules(file_bytes: bytes) -> tuple[list[str], str]:
    """
    Decodes CDXML XML trees by extracting node/bond graphs directly 
    into RDKit molecules and canonical SMILES.
    """
    extracted_smiles = []
    text_blocks = []
    
    try:
        root = ET.fromstring(file_bytes)
        
        # 1. Extract plain text annotations (reaction conditions, step numbers)
        for elem in root.iter():
            if elem.tag == "t" and elem.text and elem.text.strip():
                text_blocks.append(elem.text.strip())
            for s in elem.findall(".//s"):
                if s.text and s.text.strip():
                    text_blocks.append(s.text.strip())

        # 2. Extract structural fragments as RDKit molecules
        for fragment in root.iter("fragment"):
            rw_mol = Chem.RWMol()
            node_to_idx = {}
            
            nodes = fragment.findall("n")
            bonds = fragment.findall("b")
            
            if not nodes:
                continue

            for node in nodes:
                n_id = node.attrib.get("id")
                elem_sym = node.attrib.get("Element", "6") # Default Carbon
                charge = int(node.attrib.get("Charge", "0"))
                
                atomic_num = int(elem_sym) if elem_sym.isdigit() else PERIODIC_TABLE.get(elem_sym, 6)
                
                atom = Chem.Atom(atomic_num)
                if charge != 0:
                    atom.SetFormalCharge(charge)
                    
                idx = rw_mol.AddAtom(atom)
                node_to_idx[n_id] = idx

            for bond in bonds:
                b_node = bond.attrib.get("B")
                e_node = bond.attrib.get("E")
                order_raw = int(bond.attrib.get("Order", "1"))
                
                if b_node in node_to_idx and e_node in node_to_idx:
                    b_type = BOND_ORDER_MAP.get(order_raw, Chem.BondType.SINGLE)
                    rw_mol.AddBond(node_to_idx[b_node], node_to_idx[e_node], b_type)

            try:
                mol = rw_mol.GetMol()
                Chem.SanitizeMol(mol)
                smiles = Chem.MolToSmiles(mol)
                if smiles:
                    extracted_smiles.append(smiles)
            except Exception:
                try:
                    mol = rw_mol.GetMol()
                    smiles = Chem.MolToSmiles(mol)
                    if smiles:
                        extracted_smiles.append(smiles)
                except Exception:
                    pass

    except Exception as e:
        text_blocks.append(f"[CDXML Parsing Fallback: {e}]")

    return extracted_smiles, "\n".join(text_blocks)


def parse_cdx_binary_to_molecules(file_bytes: bytes) -> tuple[list[str], str]:
    """
    Decodes binary ChemDraw (.cdx) VjCD0100 tag streams to extract chemical nodes, 
    atomic charges, bond orders, and textual parameters.
    """
    extracted_smiles = []
    extracted_text = []

    pos = 8 if file_bytes.startswith(b'VjCD0100') else 0
    file_len = len(file_bytes)

    rw_mol = Chem.RWMol()
    node_id_map = {}
    current_node_counter = 0

    while pos + 4 < file_len:
        tag, val_len = struct.unpack_from("<HH", file_bytes, pos)
        pos += 4

        # Tag 0x8004 = Node Object
        if tag == 0x8004:
            current_node_counter += 1
            atom = Chem.Atom(6) # Default Carbon
            idx = rw_mol.AddAtom(atom)
            node_id_map[current_node_counter] = idx

        # Tag 0x0400 / 0x0402 = Atomic Number / Element
        elif tag in [0x0400, 0x0402] and pos + 2 <= file_len and current_node_counter in node_id_map:
            atomic_num = struct.unpack_from("<h", file_bytes, pos)[0]
            if 1 <= atomic_num <= 118:
                atom_idx = node_id_map[current_node_counter]
                rw_mol.GetAtomWithIdx(atom_idx).SetAtomicNum(atomic_num)

        # Tag 0x0421 = Formal Charge
        elif tag == 0x0421 and pos + 2 <= file_len and current_node_counter in node_id_map:
            charge = struct.unpack_from("<h", file_bytes, pos)[0]
            atom_idx = node_id_map[current_node_counter]
            rw_mol.GetAtomWithIdx(atom_idx).SetFormalCharge(charge)

        # Tag 0x8005 = Bond Object
        elif tag == 0x8005 and pos + 8 <= file_len:
            b_id, e_id, b_order = struct.unpack_from("<HHH", file_bytes, pos)
            if b_id in node_id_map and e_id in node_id_map:
                b_type = BOND_ORDER_MAP.get(b_order, Chem.BondType.SINGLE)
                try:
                    rw_mol.AddBond(node_id_map[b_id], node_id_map[e_id], b_type)
                except Exception:
                    pass

        # Tag 0x0A00 = Text Property
        elif tag in [0x0A00, 0x000E, 0x0600] and pos + val_len <= file_len:
            try:
                chunk = file_bytes[pos:pos + val_len].decode('utf-8', errors='ignore').strip()
                if len(chunk) >= 2:
                    extracted_text.append(chunk)
            except Exception:
                pass

        if val_len & 0x8000:
            pos += 2
        else:
            pos += val_len

    # Extract parsed molecules
    try:
        mol = rw_mol.GetMol()
        if mol.GetNumAtoms() > 0:
            Chem.SanitizeMol(mol, catchErrors=True)
            for frag in Chem.GetMolFrags(mol, asMols=True):
                sm = Chem.MolToSmiles(frag)
                if len(sm) > 1:
                    extracted_smiles.append(sm)
    except Exception:
        pass

    # Extract remaining textual comments/reagents
    extracted_text.extend(extract_strings_from_binary(file_bytes, min_len=3))
    
    return extracted_smiles, "\n".join(extracted_text)


def extract_chemsketch_data(file_bytes: bytes, ext: str = "sk2") -> tuple[list[str], str]:
    """Extracts ChemSketch files (.sk2, .csk) with embedded Molblock extraction."""
    extracted_smiles = []
    text_blocks = [f"[Format: ACD/ChemSketch .{ext.upper()}]"]

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                content = zip_ref.read(file_name).decode('utf-8', errors='ignore')
                if file_name.endswith(('.mol', '.sdf')):
                    mol = Chem.MolFromMolBlock(content)
                    if mol:
                        extracted_smiles.append(Chem.MolToSmiles(mol))
                elif file_name.endswith(('.xml', '.txt', '.json')):
                    text_blocks.append(content)
    except Exception:
        pass

    text_blocks.extend(extract_strings_from_binary(file_bytes, min_len=3))
    return extracted_smiles, "\n".join(text_blocks)


def extract_chemical_text(file_bytes: bytes, file_name: str) -> str:
    """
    Master extractor dispatcher. Builds precise structured context 
    containing exact extracted SMILES and chemical annotations.
    """
    ext = file_name.split(".")[-1].lower()
    extracted_smiles = []
    raw_text = ""

    if ext in ["cdxml", "xml"]:
        extracted_smiles, raw_text = parse_cdxml_to_molecules(file_bytes)
    elif ext == "cdx":
        extracted_smiles, raw_text = parse_cdx_binary_to_molecules(file_bytes)
    elif ext in ["sk2", "csk"]:
        extracted_smiles, raw_text = extract_chemsketch_data(file_bytes, ext=ext)
    else:
        raw_text = "\n".join(extract_strings_from_binary(file_bytes))

    output_lines = [f"--- FILE STRUCTURE DATA: {file_name} ---"]
    if extracted_smiles:
        output_lines.append("EXTRACTED MOLECULAR STRUCTURES (FROM FILE GRAPH):")
        for i, sm in enumerate(extracted_smiles, 1):
            output_lines.append(f"  Structure {i} Canonical SMILES: {sm}")
    
    if raw_text:
        output_lines.append("\nEXTRACTED TEXT & REAGENT ANNOTATIONS:")
        output_lines.append(raw_text)

    return "\n".join(output_lines)


def extract_pdf_pages(file_bytes: bytes, max_pages: int = 4) -> list[Image.Image]:
    """Converts multi-page synthesis route PDFs into high-resolution images."""
    try:
        images = pdf2image.convert_from_bytes(file_bytes, dpi=200, first_page=1, last_page=max_pages)
        return images
    except Exception:
        return []
