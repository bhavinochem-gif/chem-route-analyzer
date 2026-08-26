import io
import json
import base64
import re
from PIL import Image
from groq import Groq

def encode_image_to_base64(pil_image: Image.Image) -> str:
    """Converts a PIL image to a base64 string for vision-capable models."""
    buffered = io.BytesIO()
    pil_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def analyze_ros(client: Groq, text_context: str = None, images: list = None, model_name: str = "llama-3.3-70b-versatile") -> dict:
    """Extracts chemical route synthesis, named reactions, and mechanism steps using Groq."""
    
    system_prompt = """
    You are an expert process chemist and reaction mechanism specialist.
    Analyze the provided Route of Synthesis (ROS). You MUST return a strictly valid JSON object.
    
    JSON Schema:
    {
      "overall_route_summary": "High-level summary of the synthetic strategy and transformation steps",
      "steps": [
        {
          "step_number": 1,
          "reaction_name": "Official Named Reaction (e.g., Suzuki-Miyaura, Swern Oxidation, Buchwald-Hartwig)",
          "reagents_solvents_conditions": "e.g., Pd(dppf)Cl2, K2CO3, 1,4-Dioxane/H2O, 80 °C, 4 h",
          "starting_material_smiles": "Valid SMILES string",
          "product_smiles": "Valid SMILES string",
          "reaction_smarts": "Reactant1.Reactant2>>Product",
          "mechanism": {
            "mechanism_type": "e.g., Catalytic Cycle (Pd(0)/Pd(II)) or Polar Addition-Elimination",
            "arrow_pushing_description": [
              "Step 1: Description of electron flow",
              "Step 2: Intermediate formation",
              "Step 3: Reductive elimination / product release"
            ],
            "key_intermediates": [
              {"name": "Intermediate Name", "smiles_or_desc": "Structure or description"}
            ]
          },
          "process_parameters": {
            "critical_process_parameters": "Temperature range, stirring rate, safety constraints",
            "workup_and_isolation": "Quench, phase separation, solvent swap, crystallization",
            "impurity_profile_risks": "Regioisomers, dimeric impurities, residual catalysts"
          }
        }
      ]
    }
    """

    user_text = f"Analyze the following chemical route data:\n{text_context if text_context else 'Extract and elucidate the reaction mechanism steps from the provided synthesis route.'}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=4096
    )

    raw_output = response.choices[0].message.content
    
    # Safe JSON parse
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("Could not parse JSON output from Groq model.")
