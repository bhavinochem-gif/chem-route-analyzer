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
    You are an expert physical organic and process chemist specializing in reaction mechanisms.
    Analyze the provided Route of Synthesis (ROS) and elucidate the step-by-step elementary mechanistic pathway,
    including coordination states, reactive intermediates, formal charge shifts, and electron-pushing sequences.
    
    Return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of the synthetic sequence",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "e.g., Friedländer / Skraup Quinoline Annulation",
          "reaction_class_type": "Condensation-Cyclization / Annulation",
          "reagents_solvents_conditions": "KOtBu, THF, 25 °C, 10-20 min",
          "starting_material_smiles": "Nc1ccccc1C=O",
          "product_smiles": "Cc1nc2ccccc2cc1",
          "reaction_smarts": "Nc1ccccc1C=O.CC(=O)C(C)C>>Cc1nc2ccccc2cc1",
          "byproducts": ["H2O", "tBuOH", "KOH"],
          "bond_analysis": {
            "bonds_broken": ["C=O (aldehyde carbonyl pi-bond)", "C-H (alpha to ketone)", "C-O (alcohol elimination)"],
            "bonds_formed": ["C=N (imine double bond)", "C(Ar)-C(alkyl) (intramolecular aldol condensation)", "C=C (aromatic quinoline core)"],
            "nucleophile_electrophile_roles": {
              "nucleophile": "Aniline nitrogen lone pair & potassium enolate alpha-carbon",
              "electrophile": "Aldehyde carbonyl carbon & ketone carbonyl carbon",
              "catalyst_or_chelation": "K+ cation coordinated by solvent (THF)3 stabilizing oxo/aza chelates"
            }
          },
          "elementary_mechanism_pathway": [
            {
              "micro_step_num": 1,
              "stage_title": "Lewis Acid / Cation Chelation",
              "reagents_in_out": "+ K+ (THF)3",
              "reactant_smiles": "Nc1ccccc1C=O",
              "intermediate_smiles": "Nc1ccccc1C=O",
              "micro_smarts": "Nc1ccccc1C=O>>Nc1ccccc1C=O",
              "arrow_pushing": "Potassium cation coordinates simultaneously to the formyl oxygen and amino nitrogen lone pairs in THF.",
              "driving_force": "Chelation pre-organization reducing activation energy."
            },
            {
              "micro_step_num": 2,
              "stage_title": "Enolate Formation & Intermolecular Imine Condensation",
              "reagents_in_out": "+ KOtBu, - tBuOH, - H2O",
              "reactant_smiles": "CC(=O)C(C)C",
              "intermediate_smiles": "CC(C)C(=O)C=Nc1ccccc1C=O",
              "micro_smarts": "Nc1ccccc1C=O.CC(=O)C(C)C>>CC(C)C(=O)C=Nc1ccccc1C=O",
              "arrow_pushing": "tBuO- deprotonates alpha-methyl carbon to generate enolate; nucleophilic attack on coordinated formyl group yields the imine-enolate adduct.",
              "driving_force": "Thermodynamic stability of conjugated imine."
            },
            {
              "micro_step_num": 3,
              "stage_title": "Intramolecular Cyclization (Aldol Addition)",
              "reagents_in_out": "Base-promoted enolization",
              "reactant_smiles": "CC(C)C(=O)C=Nc1ccccc1C=O",
              "intermediate_smiles": "CC(C)C1=Nc2ccccc2C(O)C1",
              "micro_smarts": "CC(C)C(=O)C=Nc1ccccc1C=O>>CC(C)C1=Nc2ccccc2C(O)C1",
              "arrow_pushing": "Nucleophilic addition of enamine/enolate alpha-carbon to the adjacent carbonyl carbon generates the dihydroquinoline alkoxide.",
              "driving_force": "Favorable 6-endo-trig ring closure."
            },
            {
              "micro_step_num": 4,
              "stage_title": "Dehydration & Aromatization",
              "reagents_in_out": "- tBuOH, - [K(THF)3-OH]",
              "reactant_smiles": "CC(C)C1=Nc2ccccc2C(O)C1",
              "intermediate_smiles": "Cc1nc2ccccc2cc1",
              "micro_smarts": "CC(C)C1=Nc2ccccc2C(O)C1>>Cc1nc2ccccc2cc1",
              "arrow_pushing": "E1cB elimination of hydroxide coordinated to potassium furnishes the aromatic quinoline system.",
              "driving_force": "Aromatic resonance stabilization (quinoline core)."
            }
          ],
          "process_parameters": {
            "critical_process_parameters": "Base stoichiometry (KOtBu), strict moisture control in THF (<200 ppm), reaction temperature 20-25 °C",
            "workup_and_isolation": "Quench with water, extract with ethyl acetate, wash with brine, vacuum distillation or recrystallization",
            "impurity_profile_risks": "Uncyclized imine intermediate, self-condensation of ketone, dihydroquinoline byproduct"
          },
          "analytical_and_ipc": {
            "ipc_checkpoints": [
              {"stage": "Reaction Completion", "technique": "HPLC (UV 254 nm)", "acceptance_criteria": "2-Aminobenzaldehyde <= 0.5% a/a"}
            ],
            "characterization": {
              "hplc_assay_desc": "C18 (150 x 4.6 mm, 3.5 um), MeCN/H2O 0.1% TFA",
              "nmr_diagnostic_peaks": "1H NMR (400 MHz, CDCl3): delta 8.05 (d, J = 8.4 Hz, 1H, H-4 quinoline), 7.28 (s, 1H, H-3 quinoline)",
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
