import io
import re
import struct
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image
import pdf2image

def extract_strings_from_binary(file_bytes: bytes, min_len: int = 3) -> list[str]:
    """Extracts printable ASCII and UTF-8 strings from binary data streams."""
    # Matches printable ASCII characters and common chemical symbols
    pattern = rb'[\w\s\(\)\[\]\{\}\-\+\=\#\:\@\/\.\,\>\<\\\%]{' + str(min_len).encode() + rb',}'
    raw_matches = re.findall(pattern, file_bytes)
    cleaned = []
    for match in raw_matches:
        try:
            decoded = match.decode('utf-8', errors='ignore').strip()
            # Filter out non-informative noise strings
            if len(decoded) >= min_len and not decoded.isnumeric():
                cleaned.append(decoded)
        except Exception:
            continue
    return cleaned


def extract_cdxml_data(file_bytes: bytes) -> str:
    """Extracts text, SMILES annotations, and node labels from ChemDraw XML (.cdxml)."""
    try:
        root = ET.fromstring(file_bytes)
        text_nodes = [elem.text.strip() for elem in root.iter() if elem.text and elem.text.strip()]
        
        # Extract attribute data like formulas, IDs, or chemical names
        node_attribs = []
        for elem in root.iter():
            for key in ["Formula", "ChemicalName", "Text"]:
                val = elem.attrib.get(key)
                if val and val.strip():
                    node_attribs.append(f"{key}: {val.strip()}")
                    
        combined = text_nodes + node_attribs
        return "\n".join(combined) if combined else "ChemDraw XML parsed (No explicit text blocks found)."
    except Exception as e:
        # Fallback to string extraction if XML is malformed
        extracted = extract_strings_from_binary(file_bytes)
        return "\n".join(extracted) if extracted else f"CDXML extraction note: {e}"


def extract_cdx_data(file_bytes: bytes) -> str:
    """Parses binary ChemDraw (.cdx) files by scanning header objects, text tags, and string chunks."""
    extracted_text = []
    
    # Check for ChemDraw binary magic header: VjCD0100 (0x56 0x6a 0x43 0x44 0x30 0x31 0x30 0x30)
    is_cdx_header = file_bytes.startswith(b'VjCD0100')
    if is_cdx_header:
        extracted_text.append("[Format: ChemDraw Binary CDX]")

    # Scan for CDX text property tags (Tag 0x0A00 / 0x0600 / Text Objects)
    pos = 8 if is_cdx_header else 0
    file_len = len(file_bytes)
    
    while pos + 4 < file_len:
        tag, val_len = struct.unpack_from("<HH", file_bytes, pos)
        pos += 4
        
        # Tag 0x0A00 is CDXProp_Text; Tag 0x000E is Name/Comment
        if tag in [0x0A00, 0x000E, 0x0600] and pos + val_len <= file_len:
            try:
                chunk = file_bytes[pos:pos + val_len].decode('utf-8', errors='ignore').strip()
                if chunk and len(chunk) >= 2:
                    extracted_text.append(chunk)
            except Exception:
                pass
            pos += val_len
        elif val_len & 0x8000:
            # Variable-length tag boundary
            pos += 2
        else:
            pos += val_len

    # If tagged parsing is sparse, run broad binary token aggregation
    if len(extracted_text) <= 1:
        extracted_text.extend(extract_strings_from_binary(file_bytes, min_len=3))

    return "\n".join(extracted_text) if extracted_text else "Binary ChemDraw (.cdx) parsed."


def extract_chemsketch_data(file_bytes: bytes, ext: str = "sk2") -> str:
    """
    Parses ACD/ChemSketch .sk2 and .csk files.
    Handles ZIP-compressed XML/MOL containers as well as proprietary binary/OLE formats.
    """
    extracted_info = [f"[Format: ACD/ChemSketch .{ext.upper()}]"]
    
    # 1. Try unpacking as a ZIP container (Modern .sk2 format)
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.endswith(('.xml', '.txt', '.mol', '.sdf', '.json')):
                    content = zip_ref.read(file_name).decode('utf-8', errors='ignore')
                    extracted_info.append(f"--- File: {file_name} ---")
                    extracted_info.append(content)
        if len(extracted_info) > 1:
            return "\n".join(extracted_info)
    except (zipfile.BadZipFile, Exception):
        pass

    # 2. Parse as Binary ChemSketch (.sk2 / .csk legacy structure)
    # Search for embedded MOL/SDF block markers ('M  END', '$MDL', 'V2000', 'V3000')
    if b'M  END' in file_bytes or b'V2000' in file_bytes or b'V3000' in file_bytes:
        extracted_info.append("[Embedded Molfile / Connection Table Detected]")

    # Extract all text tokens, IUPAC names, reaction conditions, and SMILES strings
    string_tokens = extract_strings_from_binary(file_bytes, min_len=3)
    extracted_info.extend(string_tokens)

    return "\n".join(extracted_info) if len(extracted_info) > 1 else f"ChemSketch .{ext} parsed."


def extract_chemical_text(file_bytes: bytes, file_name: str) -> str:
    """Master dispatcher that detects file format by extension and extracts route data."""
    ext = file_name.split(".")[-1].lower()
    
    if ext in ["cdxml", "xml"]:
        return extract_cdxml_data(file_bytes)
    elif ext == "cdx":
        return extract_cdx_data(file_bytes)
    elif ext in ["sk2", "csk"]:
        return extract_chemsketch_data(file_bytes, ext=ext)
    else:
        # Generic fallback
        return "\n".join(extract_strings_from_binary(file_bytes))


def extract_pdf_pages(file_bytes: bytes, max_pages: int = 4) -> list[Image.Image]:
    """Converts multi-page synthesis route PDFs into high-resolution images."""
    try:
        images = pdf2image.convert_from_bytes(file_bytes, dpi=200, first_page=1, last_page=max_pages)
        return images
    except Exception:
        return []
