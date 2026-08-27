import io
import xml.etree.ElementTree as ET
from PIL import Image
import pdf2image

def extract_cdxml_data(file_bytes: bytes) -> str:
    """Extracts chemical text, molecular formulas, and reaction fragments from CDXML."""
    try:
        root = ET.fromstring(file_bytes)
        text_nodes = [elem.text.strip() for elem in root.iter() if elem.text and elem.text.strip()]
        return "\n".join(text_nodes) if text_nodes else "CDXML structure data extracted."
    except Exception as e:
        return f"CDXML extraction note: {e}"

def extract_pdf_pages(file_bytes: bytes, max_pages: int = 4) -> list[Image.Image]:
    """Converts multi-page synthesis route PDFs into high-resolution images."""
    try:
        images = pdf2image.convert_from_bytes(file_bytes, dpi=200, first_page=1, last_page=max_pages)
        return images
    except Exception:
        return []
