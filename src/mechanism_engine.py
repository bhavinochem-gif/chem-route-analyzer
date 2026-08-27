import json
import streamlit as st
from google import genai
from google.genai import types

@st.cache_data(persist="disk", show_spinner=False)
def analyze_ros(
    _client: genai.Client, 
    text_context: str = None, 
    _images: list = None, 
    file_hash: str = ""
) -> dict:
    """
    Cached Route of Synthesis analyzer using Gemini 3.6 Flash.
    '_client' and '_images' are ignored during hashing via leading underscores.
    'file_hash' and 'text_context' serve as the deterministic cache keys.
    """
    prompt = """
    You are an expert process organic chemist and reaction mechanism specialist.
    Analyze the provided Route of Synthesis (ROS) from the ChemDraw text and/or PDF images.
    
    Return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of the synthetic strategy, total steps, and key transformations",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "Official IUPAC / Named Reaction (e.g., Suzuki-Miyaura, Buchwald-Hartwig, Swern Oxidation)",
          "reagents_solvents_conditions": "e.g., Pd(dppf)Cl2 (0.05 eq), K2CO3 (2.0 eq), 1,4-Dioxane/H2O, 80 °C, 4 h",
          "starting_material_smiles": "Valid SMILES string",
          "product_smiles": "Valid SMILES string",
          "reaction_smarts": "Reactant1.Reactant2>>Product",
          "mechanism": {
            "mechanism_type": "e.g., Catalytic Cycle (Pd(0)/Pd(II)) or Polar Addition-Elimination",
            "arrow_pushing_description": [
              "Step 1: Description of electron movement / oxidative addition",
              "Step 2: Base-mediated transmetallation",
              "Step 3: Reductive elimination to furnish biaryl product"
            ],
            "key_intermediates": [
              {"name": "Intermediate Name", "smiles_or_desc": "Structure or description"}
            ]
          },
          "process_parameters": {
            "critical_process_parameters": "Temperature range, agitation rate, inert gas purging, exotherm controls",
            "workup_and_isolation": "Quench, phase separation, solvent swap, crystallization solvent system",
            "impurity_profile_risks": "Regioisomers, dimeric impurities, residual catalyst metals"
          },
          "analytical_and_ipc": {
            "ipc_checkpoints": [
              {
                "stage": "Reaction Completion",
                "technique": "HPLC (UV 254 nm)",
                "acceptance_criteria": "Starting Material <= 0.5% a/a, Conversion >= 98.0%"
              },
              {
                "stage": "Aqueous Phase Extraction",
                "technique": "TLC / HPLC",
                "acceptance_criteria": "Product in aqueous layer <= 0.2%"
              },
              {
                "stage": "Isolated Wet Cake",
                "technique": "Karl Fischer / LOD",
                "acceptance_criteria": "Water content <= 0.5% w/w, LOD <= 1.0%"
              }
            ],
            "characterization": {
              "hplc_assay_desc": "C18 (150 x 4.6 mm, 3.5 um), MeCN / 0.1% H3PO4 (Gradient 10-90% over 15 min), Purity >= 98.5%",
              "nmr_diagnostic_peaks": "1H NMR (400 MHz, CDCl3): key diagnostic chemical shifts and coupling constants",
              "mass_spec_target": "ESI-MS [M+H]+ target mass"
            }
          }
        }
      ]
    }
    """

    contents = [prompt]
    if text_context:
        contents.append(f"Parsed Chemical Context:\n{text_context}")
    if _images:
        contents.extend(_images[:3])

    response = _client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)
