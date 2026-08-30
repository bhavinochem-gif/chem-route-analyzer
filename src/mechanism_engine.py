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
    Analyzes ROS with explicit elementary mechanistic pathways,
    intermediates, curved-arrow electron flow, and thermodynamic driving forces.
    """
    prompt = """
    You are an expert physical organic chemist and reaction mechanism specialist.
    Analyze the provided Route of Synthesis (ROS) and elucidate the complete step-by-step 
    reaction mechanism pathway matching scientific publication standards.

    CRITICAL RDKIT SMILES INSTRUCTIONS:
    1. Every 'intermediate_smiles' MUST be 100% syntactically valid SMILES parseable by RDKit.
    2. DO NOT use pseudo-SMILES symbols like '---', '...', '‡', or text labels in SMILES strings.
    3. For metal/chelate coordination complexes or salts, USE DISCONNECTED DOT-NOTATION with valid fragments.
       - Example: "Nc1ccccc1C=O.[K+].C1CCOC1"

    Return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of the synthetic sequence",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "Official IUPAC / Named Reaction (e.g., Skraup / Friedländer Annulation)",
          "reaction_class_type": "Condensation-Cyclization | Substitution | Addition | Elimination | Catalytic Cycle",
          "reagents_solvents_conditions": "e.g., KOtBu, THF, 25 °C, 10-20 mins",
          "starting_material_smiles": "Nc1ccccc1C=O",
          "product_smiles": "Cc1nc2ccccc2cc1",
          "reaction_smarts": "Nc1ccccc1C=O.CC(=O)C(C)C>>Cc1nc2ccccc2cc1",
          "byproducts": ["H2O", "tBuOH", "KOH"],
          "elementary_mechanism_pathway": [
            {
              "stage_number": 1,
              "stage_title": "Lewis Acid / Cation Chelation",
              "intermediate_smiles": "Nc1ccccc1C=O.[K+].C1CCOC1",
              "arrow_type": "forward",
              "reagents_in": "+ K+ (THF)3",
              "reagents_out": "",
              "electron_pushing_desc": "Potassium cation coordinates to the aldehyde carbonyl oxygen and aniline nitrogen lone pairs, increasing carbonyl electrophilicity.",
              "driving_force": "Chelation pre-organization & Lewis acid activation reducing kinetic activation barrier."
            },
            {
              "stage_number": 2,
              "stage_title": "Alpha-Deprotonation & Imine Condensation",
              "intermediate_smiles": "CC(C)C(=O)C=Nc1ccccc1C=O.[K+]",
              "arrow_type": "forward",
              "reagents_in": "+ KOtBu",
              "reagents_out": "- tBuOH, - H2O",
              "electron_pushing_desc": "tBuO- deprotonates alpha-methyl carbon to generate enolate; nucleophilic addition onto coordinated formyl group yields the imine adduct.",
              "driving_force": "Thermodynamic conjugation of the extended imine pi-system."
            },
            {
              "stage_number": 3,
              "stage_title": "Intramolecular Aldol Cyclization",
              "intermediate_smiles": "CC(C)C1=Nc2ccccc2C([O-])C1.[K+]",
              "arrow_type": "equilibrium",
              "reagents_in": "Enolate equilibrium",
              "reagents_out": "",
              "electron_pushing_desc": "Nucleophilic attack of enamine/enolate alpha-carbon on the adjacent ketone carbonyl carbon forms the 6-membered dihydroquinoline alkoxide.",
              "driving_force": "Kinetically favored 6-endo-trig ring closure."
            },
            {
              "stage_number": 4,
              "stage_title": "Dehydration & Aromatization",
              "intermediate_smiles": "Cc1nc2ccccc2cc1",
              "arrow_type": "forward",
              "reagents_in": "- OtBu",
              "reagents_out": "- HOtBu, - [K-OH]",
              "electron_pushing_desc": "E1cB elimination of potassium-coordinated hydroxide furnishes the aromatic quinoline system.",
              "driving_force": "Large thermodynamic aromatic resonance stabilization energy."
            }
          ],
          "bond_analysis": {
            "bonds_broken": ["C=O (aldehyde carbonyl pi-bond)", "C-H (alpha to ketone)", "C-O (hydroxyl elimination)"],
            "bonds_formed": ["C=N (imine double bond)", "C-C (intramolecular ring closure)", "C=C (aromatic quinoline core)"],
            "nucleophile_electrophile_roles": {
              "nucleophile": "Enolate alpha-carbon / Aniline nitrogen lone pair",
              "electrophile": "Aldehyde carbonyl carbon / Ketone carbonyl carbon",
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
