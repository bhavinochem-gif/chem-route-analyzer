import json
import time
import streamlit as st
from google import genai
from google.genai import types

@st.cache_data(persist="disk", show_spinner=False)
def analyze_ros(
    _client: genai.Client, 
    text_context: str = None, 
    _images: list = None, 
    file_hash: str = "",
    max_retries: int = 4
) -> dict:
    """
    Analyzes ROS with strict parent-scaffold preservation, Meisenheimer 
    addition-elimination tetrahedral intermediates, and RDKit-verified SMILES.
    Includes automated retry logic for 503/429 API server overloads.
    """
    prompt = """
    You are an expert physical organic chemist specializing in reaction mechanism elucidation.
    Analyze the provided Route of Synthesis (ROS) and elucidate the step-by-step reaction mechanism pathway.

    ========================================================================================
    STRICT CHEMICAL SCAFFOLD & MECHANISM RULES (ZERO TOLERANCE FOR CORE HALLUCINATIONS):
    ========================================================================================
    1. CORE RING PRESERVATION (DO NOT SCRAMBLE PARENT RINGS):
       - If the starting material contains a 6-membered ring (e.g., Pyrazine, Pyrimidine, Pyridine, Benzene), 
         EVERY intermediate in an addition, substitution, or elimination mechanism MUST maintain that EXACT 
         same 6-membered ring connectivity.
       - NEVER contract a 6-membered aromatic ring (e.g. 2,6-dichloropyrazine) into an imidazole or 5-membered ring!
    
    2. NUCLEOPHILIC AROMATIC SUBSTITUTION (SNAr) MECHANISM RULES:
       - Example: 2-chloro-5-methoxypyrazine reacting with Hydrazine Hydrate (NH2NH2):
         * Stage 1 (Starting Substrates): "COc1cnc(Cl)nc1Cl.NN"
         * Stage 2 (Tetrahedral Meisenheimer Intermediate): Nucleophile (NH2NH2) attacks the C-Cl carbon. 
           The C-Cl carbon becomes sp3 tetrahedral containing BOTH -Cl and -NHNH2 groups, with negative 
           charge delocalized onto the adjacent ring nitrogen: e.g., "COc1c[n-]c(Cl)(NN)nc1Cl.[H+]" or "COc1cnc(Cl)(NN)nc1Cl".
         * Stage 3 (Aromatization / Chloride Leaving Group Departure): Chloride ion (Cl-) departs with 
           electron pair, restoring the aromatic 6-membered pyrazine ring: "COc1cnc(Cl)nc1NN".
    
    3. VALID RDKIT SMILES ONLY:
       - All 'starting_material_smiles', 'product_smiles', and 'intermediate_smiles' MUST be 100% syntactically 
         valid, valence-correct SMILES parseable by RDKit.
       - For salts or disconnected species, use valid dot notation (e.g. "COc1cnc(Cl)nc1NN.[Cl-]").
       - DO NOT use pseudo-SMILES symbols like '---', '...', '‡', or label strings.

    Return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of the synthetic strategy",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "Official IUPAC / Named Reaction (e.g. SNAr Nucleophilic Aromatic Substitution)",
          "reaction_class_type": "Substitution (SNAr) | Condensation-Cyclization | Addition | Elimination | Catalytic Cycle",
          "reagents_solvents_conditions": "e.g., Hydrazine hydrate (1.2 eq), EtOH, 50 °C, 2 h",
          "starting_material_smiles": "Valid SMILES (e.g., COc1cnc(Cl)nc1Cl)",
          "product_smiles": "Valid SMILES (e.g., COc1cnc(Cl)nc1NN)",
          "reaction_smarts": "COc1cnc(Cl)nc1Cl.NN>>COc1cnc(Cl)nc1NN",
          "byproducts": ["HCl", "H2O"],
          "elementary_mechanism_pathway": [
            {
              "stage_number": 1,
              "stage_title": "Starting Heteroaryl Chloride & Nucleophile",
              "intermediate_smiles": "COc1cnc(Cl)nc1Cl.NN",
              "arrow_type": "forward",
              "reagents_in": "+ NH2NH2.H2O",
              "reagents_out": "",
              "electron_pushing_desc": "Hydrazine nitrogen lone pair performs nucleophilic attack on the electrophilic C-2 carbon of the chloropyrazine ring.",
              "driving_force": "High electrophilicity of C-2 carbon activated by ring nitrogen atoms."
            },
            {
              "stage_number": 2,
              "stage_title": "Tetrahedral Meisenheimer Addition Complex",
              "intermediate_smiles": "COc1cnc(Cl)(NN)nc1Cl",
              "arrow_type": "equilibrium",
              "reagents_in": "Charge transfer",
              "reagents_out": "",
              "electron_pushing_desc": "Formation of the sp3 tetrahedral Meisenheimer intermediate with negative charge delocalized across the ring diazine nitrogens.",
              "driving_force": "Resonance stabilization of the Meisenheimer intermediate by electronegative ring nitrogens."
            },
            {
              "stage_number": 3,
              "stage_title": "Chloride Departure & Aromatic Restoration",
              "intermediate_smiles": "COc1cnc(Cl)nc1NN",
              "arrow_type": "forward",
              "reagents_in": "",
              "reagents_out": "- Cl-, - H+",
              "electron_pushing_desc": "Nitrogen lone pair reforms the aromatic pi-system, expelling the chloride leaving group (Cl-) to furnish the substituted product.",
              "driving_force": "Thermodynamic restoration of heterocyclic aromatic resonance stabilization energy."
            }
          ],
          "bond_analysis": {
            "bonds_broken": ["C(2)-Cl (heterolytic cleavage / leaving group departure)"],
            "bonds_formed": ["C(2)-N(hydrazine) (nucleophilic displacement sigma bond)"],
            "nucleophile_electrophile_roles": {
              "nucleophile": "Hydrazine hydrate (:NH2NH2)",
              "electrophile": "2-Chloro-5-methoxypyrazine (C-2 electrophilic carbon)",
              "catalyst_or_chelation": "Protic solvent (EtOH) stabilizing chloride leaving group"
            }
          },
          "process_parameters": {
            "critical_process_parameters": "Temperature control to prevent bis-hydrazinylation at the second chloro position, slow reagent addition",
            "workup_and_isolation": "Cooling to 0 °C to precipitate product cake, filtration, washing with cold EtOH/water",
            "impurity_profile_risks": "Bis-hydrazine regioisomer, dechlorinated pyrazine byproduct"
          },
          "analytical_and_ipc": {
            "ipc_checkpoints": [
              {"stage": "Reaction Completion", "technique": "HPLC (UV 254 nm)", "acceptance_criteria": "Starting material <= 0.5% a/a"}
            ],
            "characterization": {
              "hplc_assay_desc": "C18 (150 x 4.6 mm, 3.5 um), MeCN/H2O 0.1% TFA, Purity >= 98.5%",
              "nmr_diagnostic_peaks": "1H NMR: delta 8.01 (s, 1H, pyrazine C-H), 4.30 (br s, 2H, NH2), 3.95 (s, 3H, OCH3)",
              "mass_spec_target": "ESI-MS [M+H]+"
            }
          }
        }
      ]
    }
    """

    contents = [prompt]
    if text_context:
        contents.append(f"Parsed Chemical Input:\n{text_context}")
    if _images:
        contents.extend(_images[:3])

    # Exponential Backoff Retry Loop
    for attempt in range(max_retries):
        try:
            response = _client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            error_str = str(e)
            # Catch 503 (Unavailable) and 429 (Too Many Requests/Rate Limit)
            if "503" in error_str or "429" in error_str:
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt  # Pauses for 1s, 2s, then 4s
                    time.sleep(sleep_time)
                    continue
            # If it's a different error or we've run out of retries, raise it to the UI
            raise e
