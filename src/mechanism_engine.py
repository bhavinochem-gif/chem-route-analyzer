import json
from google import genai
from google.genai import types

def analyze_ros(client: genai.Client, text_context: str = None, images: list = None) -> dict:
    """Classifies reactions, maps 2D SMILES, and generates electron-pushing mechanisms."""
    prompt = """
    You are an expert process organic chemist and reaction mechanism specialist.
    Analyze the provided Route of Synthesis (ROS). Return a strictly valid JSON object matching this schema:
    {
      "overall_route_summary": "High-level summary of the synthetic strategy and total steps",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "Official Named Reaction (e.g., Suzuki-Miyaura Coupling, Swern Oxidation)",
          "reagents_solvents_conditions": "e.g., Pd(dppf)Cl2, K2CO3, 1,4-Dioxane/H2O, 80 °C, 4 h",
          "starting_material_smiles": "SMILES string",
          "product_smiles": "SMILES string",
          "reaction_smarts": "Reactants...>>Products...",
          "mechanism": {
            "mechanism_type": "e.g., Catalytic Cycle (Pd(0)/Pd(II)) or Polar Addition-Elimination",
            "arrow_pushing_description": [
              "Step 1: Description of electron flow",
              "Step 2: Intermediate formation",
              "Step 3: Product release"
            ],
            "key_intermediates": [
              {"name": "Intermediate Name", "smiles_or_desc": "Structure or description"}
            ]
          },
          "process_parameters": {
            "critical_process_parameters": "Temperature range, stirring rate, safety constraints",
            "workup_and_isolation": "Quench, phase separation, solvent swap, crystallization",
            "impurity_profile_risks": "Regioisomers, dimeric impurities, residual metals"
          }
        }
      ]
    }
    """
    contents = [prompt]
    if text_context:
        contents.append(f"Parsed CDXML Text:\n{text_context}")
    if images:
        contents.extend(images[:3])

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)
