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
    Analyzes ROS with explicit bond-breaking, bond-forming, 
    atom-mapping, and fundamental mechanism classification.
    """
    prompt = """
    You are an expert organic reaction mechanism specialist.
    Analyze the provided Route of Synthesis (ROS) and extract the step-by-step electron movement,
    bond-breaking, and bond-forming events similar to standard organic textbook mechanism charts.
    
    You MUST return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of the synthetic strategy",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "Specific Name (e.g., SN2 Nucleophilic Substitution / Suzuki Coupling / E2 Elimination)",
          "reaction_class_type": "Substitution | Addition | Elimination | Acid-Base | Catalytic Cycle | Rearrangement",
          "reagents_solvents_conditions": "e.g., NaCN, DMF, 60 °C, 2 h",
          "starting_material_smiles": "Valid SMILES",
          "product_smiles": "Valid SMILES",
          "byproducts": ["NaBr", "H2O"],
          "reaction_smarts": "Reactants>>Products",
          "atom_mapped_smarts": "e.g., [CH3:4][CH:3]([CH3:5])[CH2:2][CH2:1][Br:6].[Na+:7].[C-:8]#[N:9]>>[CH3:4][CH:3]([CH3:5])[CH2:2][CH2:1][C:8]#[N:9].[Na+:7].[Br-:6]",
          "bond_analysis": {
            "bonds_broken": [
              "C(1)-Br (Heterolytic cleavage / Leaving group departure)",
              "Other broken bonds..."
            ],
            "bonds_formed": [
              "C(1)-C(N) (Nucleophilic displacement / sigma bond formation)",
              "Other formed bonds..."
            ],
            "nucleophile_electrophile_roles": {
              "nucleophile": "Cyanide anion (:CN-)",
              "electrophile": "Alkyl bromide (C-1 electrophilic carbon)",
              "leaving_group": "Bromide ion (:Br-)"
            }
          },
          "mechanism": {
            "mechanism_type": "Concerted bimolecular substitution (SN2)",
            "arrow_pushing_description": [
              "1. Nucleophilic attack: Cyanide lone pair attacks the backside of C(1).",
              "2. Transition state: Pentacoordinate carbon with partial C-CN bond formation and partial C-Br bond cleavage.",
              "3. Inversion of configuration & departure of bromide anion."
            ],
            "key_intermediates": [
              {"name": "SN2 Transition State", "smiles_or_desc": "[NC---C(1)---Br]‡"}
            ]
          },
          "process_parameters": {
            "critical_process_parameters": "Exotherm control, dipole-aprotic solvent selectivity",
            "workup_and_isolation": "Aqueous wash, organic extraction, distillation",
            "impurity_profile_risks": "E2 elimination byproducts, isonitrile regioisomers"
          },
          "analytical_and_ipc": {
            "ipc_checkpoints": [
              {"stage": "Reaction Completion", "technique": "GC / HPLC", "acceptance_criteria": "SM <= 0.5%"}
            ],
            "characterization": {
              "hplc_assay_desc": "Reverse Phase C18, 254 nm",
              "nmr_diagnostic_peaks": "1H NMR: C(1)-H shifted from 3.4 ppm (alkyl-Br) to 2.3 ppm (alkyl-CN)",
              "mass_spec_target": "MS [M+H]+"
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
