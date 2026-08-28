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
    coordination complexes, intermediate structures, and arrow-pushing logic.
    """
    prompt = """
    You are an expert physical organic chemist. Analyze the provided Route of Synthesis (ROS) and 
    elucidate the step-by-step reaction mechanism pathway.

    CRITICAL RDKIT SMILES INSTRUCTIONS:
    1. Every 'intermediate_smiles' MUST be 100% syntactically valid SMILES parseable by RDKit.
    2. DO NOT use pseudo-SMILES symbols like '---', '...', '‡', or text labels in SMILES strings.
    3. For metal/chelate coordination complexes, USE DISCONNECTED DOT-NOTATION with valid fragments.
       - Example: "Nc1ccccc1C=O.[K+].C1CCOC1"

    Return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of synthetic sequence",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "Official IUPAC / Named Reaction",
          "reaction_class_type": "Condensation-Cyclization | Substitution | Addition | Elimination | Catalytic",
          "reagents_solvents_conditions": "Reagents, solvents, temp, time",
          "starting_material_smiles": "Valid SMILES",
          "product_smiles": "Valid SMILES",
          "reaction_smarts": "Reactants>>Products",
          "elementary_mechanism_pathway": [
            {
              "stage_number": 1,
              "stage_title": "Stage Title",
              "intermediate_smiles": "Valid SMILES",
              "arrow_type": "forward",
              "reagents_in": "+ Reagent",
              "reagents_out": "- Byproduct",
              "electron_pushing_desc": "Curved-arrow description"
            }
          ],
          "bond_analysis": {
            "bonds_broken": ["C=O", "C-H"],
            "bonds_formed": ["C=N", "C-C"],
            "nucleophile_electrophile_roles": {
              "nucleophile": "Nucleophilic group",
              "electrophile": "Electrophilic group",
              "catalyst_or_chelation": "Metal / catalyst coordination"
            }
          },
          "process_parameters": {
            "critical_process_parameters": "CPPs",
            "workup_and_isolation": "Workup procedure",
            "impurity_profile_risks": "Impurity risks"
          },
          "analytical_and_ipc": {
            "ipc_checkpoints": [
              {"stage": "Completion", "technique": "HPLC", "acceptance_criteria": "SM <= 0.5%"}
            ],
            "characterization": {
              "hplc_assay_desc": "Method description",
              "nmr_diagnostic_peaks": "1H NMR diagnostic peaks",
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
