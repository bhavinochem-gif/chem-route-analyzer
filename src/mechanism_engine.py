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
    Extracts elementary mechanistic pathways, chelation states, 
    intermediates, and arrow annotations for visual cascade generation.
    """
    prompt = """
    You are an expert physical organic chemist. Analyze the provided Route of Synthesis (ROS) and 
    elucidate the step-by-step reaction mechanism pathway similar to publication figures.
    
    You MUST decompose every reaction step into an 'elementary_mechanism_pathway' list of 3 to 6 discrete 
    chemical states (starting material -> coordination complex -> enolate/reactive intermediate -> cyclized intermediate -> product).
    
    Return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of the synthetic sequence",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "e.g., Skraup / Friedländer Quinoline Synthesis",
          "reaction_class_type": "Condensation-Cyclization",
          "reagents_solvents_conditions": "KOtBu, THF, 25 °C, 10-20 mins",
          "starting_material_smiles": "Nc1ccccc1C=O",
          "product_smiles": "Cc1nc2ccccc2cc1",
          "reaction_smarts": "Nc1ccccc1C=O.CC(=O)C(C)C>>Cc1nc2ccccc2cc1",
          "elementary_mechanism_pathway": [
            {
              "stage_number": 1,
              "stage_title": "Starting Reactant / Substrate",
              "intermediate_smiles": "Nc1ccccc1C=O",
              "arrow_type": "forward",
              "reagents_in": "+ K+",
              "reagents_out": "THF",
              "electron_pushing_desc": "Potassium cation coordinates to the aldehyde carbonyl oxygen and aniline nitrogen."
            },
            {
              "stage_number": 2,
              "stage_title": "Chelated Coordination Complex",
              "intermediate_smiles": "Nc1ccccc1C=O",
              "arrow_type": "forward",
              "reagents_in": "+ Ketone",
              "reagents_out": "- H2O",
              "electron_pushing_desc": "Intermolecular condensation of the amine onto the coordinated ketone/aldehyde furnishes the conjugated imine intermediate."
            },
            {
              "stage_number": 3,
              "stage_title": "Enolate-Imine Intermediate",
              "intermediate_smiles": "CC(C)C(=O)C=Nc1ccccc1C=O",
              "arrow_type": "equilibrium",
              "reagents_in": "KOtBu",
              "reagents_out": "",
              "electron_pushing_desc": "Base-mediated enolization sets up the intramolecular nucleophilic addition."
            },
            {
              "stage_number": 4,
              "stage_title": "Cyclized Dihydroquinoline Intermediate",
              "intermediate_smiles": "CC(C)C1=Nc2ccccc2C(O)C1",
              "arrow_type": "forward",
              "reagents_in": "- OtBu",
              "reagents_out": "- HOtBu",
              "electron_pushing_desc": "Intramolecular 6-endo-trig cyclization furnishes the alkoxide/alcohol adduct."
            },
            {
              "stage_number": 5,
              "stage_title": "Aromatized Quinolone Product",
              "intermediate_smiles": "Cc1nc2ccccc2cc1",
              "arrow_type": "forward",
              "reagents_in": "- [K-OH]",
              "reagents_out": "",
              "electron_pushing_desc": "Dehydration/elimination restores full aromatic resonance stabilization."
            }
          ],
          "bond_analysis": {
            "bonds_broken": ["C=O (aldehyde)", "C-H (alpha)", "C-O (hydroxyl elimination)"],
            "bonds_formed": ["C=N (imine)", "C-C (aldol cyclization)", "C=C (aromatic quinoline core)"],
            "nucleophile_electrophile_roles": {
              "nucleophile": "Enolate alpha-carbon / Aniline nitrogen",
              "electrophile": "Aldehyde carbonyl carbon",
              "catalyst_or_chelation": "K+ cation stabilized by THF solvation sphere"
            }
          },
          "process_parameters": {
            "critical_process_parameters": "Strict moisture exclusion (<150 ppm), controlled KOtBu charge rate, 20-25 °C temp hold",
            "workup_and_isolation": "Aqueous quench, EtOAc extraction, brine wash, crystallization",
            "impurity_profile_risks": "Uncyclized imine intermediate, self-aldol ketone dimers"
          },
          "analytical_and_ipc": {
            "ipc_checkpoints": [
              {"stage": "Reaction Completion", "technique": "HPLC (UV 254 nm)", "acceptance_criteria": "Starting aldehyde <= 0.5% a/a"}
            ],
            "characterization": {
              "hplc_assay_desc": "C18 (150 x 4.6 mm, 3.5 um), 10-90% MeCN/H2O (0.1% TFA), Purity >= 98.5%",
              "nmr_diagnostic_peaks": "1H NMR: delta 8.08 (d, J = 8.4 Hz, 1H), 7.30 (s, 1H)",
              "mass_spec_target": "ESI-MS [M+H]+"
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
