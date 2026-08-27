import io
import json
import pandas as pd
from src.db import get_connection

def generate_routes_excel() -> io.BytesIO | None:
    """Exports all saved routes from SQLite into a structured multi-tab Excel workbook."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name, route_summary, reaction_names, total_steps, full_json, created_at FROM synthesis_routes ORDER BY id DESC")
        rows = cursor.fetchall()

    if not rows:
        return None

    overview_records = []
    step_records = []

    for row in rows:
        route_id = row["id"]
        file_name = row["file_name"]
        created_at = row["created_at"]
        data = json.loads(row["full_json"])

        overview_records.append({
            "Route ID": route_id,
            "File Name": file_name,
            "Total Steps": row["total_steps"],
            "Named Reactions": row["reaction_names"],
            "Synthetic Strategy Summary": data.get("overall_route_summary", ""),
            "Saved Date": created_at
        })

        for step in data.get("steps", []):
            mech = step.get("mechanism", {})
            proc = step.get("process_parameters", {})
            analytical = step.get("analytical_and_ipc", {})
            char = analytical.get("characterization", {})
            
            mech_steps_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(mech.get("arrow_pushing_description", []))])
            intermediates_text = ", ".join([f"{item.get('name')}: {item.get('smiles_or_desc')}" for item in mech.get("key_intermediates", [])])

            step_records.append({
                "Route ID": route_id,
                "File Name": file_name,
                "Step Number": step.get("step_number"),
                "Reaction Name": step.get("reaction_name"),
                "Reagents & Conditions": step.get("reagents_solvents_conditions"),
                "Starting Material SMILES": step.get("starting_material_smiles"),
                "Product SMILES": step.get("product_smiles"),
                "Reaction SMARTS": step.get("reaction_smarts"),
                "Mechanism Class": mech.get("mechanism_type"),
                "Electron Flow Steps": mech_steps_text,
                "Key Intermediates": intermediates_text,
                "Critical Process Parameters (CPPs)": proc.get("critical_process_parameters"),
                "Workup & Isolation": proc.get("workup_and_isolation"),
                "Impurity Profile Risks": proc.get("impurity_profile_risks"),
                "HPLC Assay Method": char.get("hplc_assay_desc"),
                "1H NMR Diagnostic Peaks": char.get("nmr_diagnostic_peaks"),
                "Mass Spec Target": char.get("mass_spec_target")
            })

    df_overview = pd.DataFrame(overview_records)
    df_steps = pd.DataFrame(step_records)

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_overview.to_excel(writer, sheet_name="Routes Overview", index=False)
        df_steps.to_excel(writer, sheet_name="Step-by-Step Details", index=False)

        for sheetname in writer.sheets:
            worksheet = writer.sheets[sheetname]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

    excel_buffer.seek(0)
    return excel_buffer
