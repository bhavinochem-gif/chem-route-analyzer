import os
import sys

# Ensure root directory is in sys.path for Streamlit Cloud deployment
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import hashlib
import json
from datetime import datetime
import streamlit as st
from google import genai

from src.db import (
    init_db,
    save_route,
    get_route_by_hash,
    get_all_routes,
    get_route_by_id,
    delete_route_by_id
)
from src.parsers import extract_chemical_text, extract_pdf_pages
from src.chem_renderer import render_reaction_scheme, generate_mechanism_flowchart_image
from src.mechanism_engine import analyze_ros
from src.exporter import generate_routes_excel
from src.pdf_generator import build_pdf_report

# Initialize persistent SQLite storage
init_db()

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Chemical Route & Mechanism Engine",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Header ---
st.title("⚗️ Chemical Route & Step-by-Step Reaction Mechanism Engine")
st.caption("Upload Route of Synthesis (ROS) files to elucidate named reactions, 2D intermediate cascades, coordination states, and electron-pushing pathways.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_key_input = st.text_input(
        "Gemini API Key",
        type="password",
        help="Paste your Google AI Studio API key (starts with 'AQ.' or 'AIza...')"
    )
    
    raw_key = api_key_input or st.secrets.get("GEMINI_API_KEY", "")
    resolved_api_key = raw_key.strip().strip('"').strip("'")
    
    if st.button("🔌 Test API Connection", use_container_width=True):
        if not resolved_api_key:
            st.warning("⚠️ Please provide an API key or define it in Secrets.")
        elif not (resolved_api_key.startswith("AQ.") or resolved_api_key.startswith("AIza")):
            st.error("❌ Invalid format: Key must start with 'AQ.' or 'AIza'.")
        else:
            with st.spinner("Testing API connection with Gemini 3.6 Flash..."):
                try:
                    test_client = genai.Client(api_key=resolved_api_key)
                    ping_res = test_client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents="Respond with 'OK'."
                    )
                    if ping_res.text:
                        st.success("✅ Connection Successful! Gemini API key is active.")
                except Exception as err:
                    err_text = str(err)
                    if "400" in err_text or "API_KEY_INVALID" in err_text:
                        st.error("❌ Invalid API Key: Key rejected by Google authentication.")
                    elif "403" in err_text:
                        st.error("❌ Access Denied: Verify Generative Language API is enabled.")
                    elif "404" in err_text:
                        st.error("❌ Model Not Found: Please verify that gemini-3.6-flash is accessible.")
                    else:
                        st.error(f"❌ Connection failed: {err_text}")

    st.markdown("---")
    st.header("🎨 Dossier Branding")
    selected_theme = st.selectbox(
        "Color Palette",
        options=["Pharma Blue (Default)", "Emerald Biotech", "Crimson Process R&D"],
        index=0
    )
    org_name_input = st.text_input("Organization / Facility Name", value="Process Chemistry R&D")
    uploaded_logo = st.file_uploader("Upload Company Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

    st.markdown("---")
    st.header("📚 Saved Routes Library")
    
    saved_routes = get_all_routes()
    if saved_routes:
        route_options = {
            f"#{r['id']} | {r['file_name']} ({r['total_steps']} steps)": r['id'] 
            for r in saved_routes
        }
        selected_label = st.selectbox(
            "Load from Database:", 
            options=["-- Select Saved Route --"] + list(route_options.keys())
        )
        
        if selected_label != "-- Select Saved Route --":
            selected_id = route_options[selected_label]
            col_load, col_del = st.columns([1, 1])
            with col_load:
                if st.button("📂 Load Route", use_container_width=True):
                    st.session_state["analysis_results"] = get_route_by_id(selected_id)
                    st.session_state["active_file_name"] = f"Route_{selected_id}"
                    st.toast("Loaded route from SQLite database!")
            with col_del:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_route_by_id(selected_id)
                    st.rerun()

        excel_data = generate_routes_excel()
        if excel_data:
            st.download_button(
                label="📊 Export Database to Excel (.xlsx)",
                data=excel_data,
                file_name=f"chemical_synthesis_routes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.caption("No routes saved in database yet.")

    st.markdown("---")
    st.header("📁 Route Upload")
    uploaded_chem = st.file_uploader(
        "Upload Structure File (.cdxml, .cdx, .sk2, .csk)", 
        type=["cdxml", "xml", "cdx", "sk2", "csk"],
        help="Supports ChemDraw XML/Binary and ACD/ChemSketch formats."
    )
    uploaded_pdf = st.file_uploader("Upload Route (.pdf)", type=["pdf"])

# --- Main Route Processing Section ---
active_file = uploaded_chem or uploaded_pdf

if active_file:
    st.subheader("📄 Route Preview & Pre-processing")
    col1, col2 = st.columns(2)
    file_bytes = active_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    parsed_text = ""
    pdf_images = []

    with col1:
        if uploaded_chem:
            st.success(f"Loaded Structure File: `{uploaded_chem.name}`")
            parsed_text = extract_chemical_text(file_bytes, uploaded_chem.name)
            with st.expander("Parsed Structure Metadata", expanded=False):
                st.text_area("Extracted Context", parsed_text, height=180)

    with col2:
        if uploaded_pdf:
            st.success(f"Loaded PDF: `{uploaded_pdf.name}`")
            pdf_images = extract_pdf_pages(file_bytes)
            if pdf_images:
                st.image(pdf_images[0], caption="Route Scheme (Page 1)", use_container_width=True)

    # Check for existing database analysis by SHA-256 fingerprint
    existing_entry = get_route_by_hash(file_hash)
    if existing_entry and "analysis_results" not in st.session_state:
        st.info("💡 Existing analysis found in database for this exact file. Load immediately without using API tokens.")
        if st.button("⚡ Fast Load from Database (0 Tokens)", type="secondary"):
            st.session_state["analysis_results"] = existing_entry
            st.session_state["active_file_name"] = active_file.name
            st.rerun()

    # Trigger Mechanism Elucidation Analysis
    if st.button("🚀 Elucidate Full Reaction Mechanism", type="primary", use_container_width=True):
        if not resolved_api_key:
            st.error("Please enter a valid Gemini API Key in the sidebar.")
            st.stop()
            
        client = genai.Client(api_key=resolved_api_key)
        
        with st.spinner("Constructing 2D elementary mechanism cascade, intermediates, and chelate pathways..."):
            try:
                results = analyze_ros(
                    _client=client,
                    text_context=parsed_text,
                    _images=pdf_images,
                    file_hash=file_hash
                )
                save_route(
                    file_hash=file_hash,
                    file_name=active_file.name,
                    analysis_data=results
                )
                st.session_state["analysis_results"] = results
                st.session_state["active_file_name"] = active_file.name
                st.success("✅ Reaction mechanism pathway generated and saved!")
            except Exception as ex:
                st.error(f"Error during mechanism analysis: {ex}")

# --- Results Presentation ---
if "analysis_results" in st.session_state:
    results = st.session_state["analysis_results"]
    active_filename = st.session_state.get("active_file_name", "Synthesis Route")
    
    st.markdown("---")
    st.header("🧪 Comprehensive Reaction Mechanism Elucidation")
    st.info(f"**Route Strategy Overview:** {results.get('overall_route_summary', 'No summary generated.')}")

    for step in results.get("steps", []):
        step_num = step.get("step_number", 1)
        rxn_name = step.get("reaction_name", "Unclassified Transformation")
        rxn_class = step.get("reaction_class_type", "General Transformation")
        
        with st.container():
            # Step Header
            header_col1, header_col2 = st.columns([3, 1])
            with header_col1:
                st.markdown(f"### (a) Synthesis Route {step_num}: {rxn_name}")
            with header_col2:
                st.markdown(f"#### `🏷️ {rxn_class}`")
            
            st.markdown(f"**Conditions & Solvents:** `{step.get('reagents_solvents_conditions', 'N/A')}`")
            
            # (a) Overall Scheme Diagram
            rxn_smarts = step.get("reaction_smarts", "")
            if rxn_smarts and ">" in rxn_smarts:
                rxn_buf = render_reaction_scheme(rxn_smarts)
                if rxn_buf:
                    st.image(rxn_buf, caption=f"Overall Step {step_num} Transformation", use_container_width=True)

            # (b) Visual Reaction Mechanism Pathway Canvas
            st.markdown(f"### (b) Reaction Mechanism Pathway (Step-by-Step Cascade)")
            pathway = step.get("elementary_mechanism_pathway", [])
            
            if pathway:
                # 1. Render Continuous Flowchart Image
                flowchart_buf = generate_mechanism_flowchart_image(pathway, title=f"(b) Reaction Mechanism — Step {step_num} Elementary Pathway")
                if flowchart_buf:
                    st.image(flowchart_buf, caption=f"Step {step_num} Elementary Mechanism Flowchart", use_container_width=True)
                
                # 2. PERMANENT DISPLAY: Detailed Electron Movement & Driving Force Breakdown
                st.markdown("#### ⚡ Detailed Electron Movement & Mechanistic Driving Force Breakdown")
                
                for stage in pathway:
                    s_num = stage.get("stage_number", "")
                    s_title = stage.get("stage_title", "Stage")
                    s_in = stage.get("reagents_in", "")
                    s_out = stage.get("reagents_out", "")
                    s_flow = stage.get("electron_pushing_desc", "")
                    s_drive = stage.get("driving_force", "")

                    with st.container():
                        st.markdown(
                            f"""
                            <div style="background-color: #F8FAFC; border-left: 4px solid #1E3A8A; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                                <strong style="color: #1E3A8A; font-size: 1.05rem;">Stage {s_num}: {s_title}</strong>
                                <div style="margin-top: 4px; color: #475569; font-size: 0.9rem;">
                                    <b>Reagents Influx:</b> <code style="color: #0F172A;">{s_in or 'None'}</code> &nbsp;|&nbsp; 
                                    <b>Species Eliminated:</b> <code style="color: #0F172A;">{s_out or 'None'}</code>
                                </div>
                                <div style="margin-top: 6px; color: #0F172A; font-size: 0.92rem;">
                                    <b>Curved-Arrow Electron Movement:</b> {s_flow}
                                </div>
                                <div style="margin-top: 4px; color: #065F46; font-size: 0.9rem;">
                                    <b>Thermodynamic / Kinetic Driving Force:</b> <i>{s_drive or 'Thermodynamically favored step'}</i>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            # Bond Changes & Chelation Roles Matrix
            st.markdown("#### ⚡ Bond Changes & Chelation Roles")
            bond_info = step.get("bond_analysis", {})
            b_col1, b_col2, b_col3 = st.columns(3)
            
            with b_col1:
                st.markdown("**✂️ Bonds Broken:**")
                for b in bond_info.get("bonds_broken", []):
                    st.markdown(f"- 🔴 `{b}`")
            with b_col2:
                st.markdown("**🔗 Bonds Formed:**")
                for b in bond_info.get("bonds_formed", []):
                    st.markdown(f"- 🟢 `{b}`")
            with b_col3:
                roles = bond_info.get("nucleophile_electrophile_roles", {})
                st.markdown("**🎯 Chelation & Roles:**")
                if roles.get("catalyst_or_chelation"):
                    st.markdown(f"- **Chelation:** `{roles.get('catalyst_or_chelation')}`")
                if roles.get("nucleophile"):
                    st.markdown(f"- **Nucleophile:** `{roles.get('nucleophile')}`")
                if roles.get("electrophile"):
                    st.markdown(f"- **Electrophile:** `{roles.get('electrophile')}`")

            # Scale-Up & Process Controls
            proc_params = step.get("process_parameters", {})
            with st.expander(f"📋 Step {step_num} Scale-Up, CPPs & Impurity Risks", expanded=False):
                p1, p2, p3 = st.columns(3)
                p1.markdown(f"**Critical Process Parameters (CPPs):**\n\n{proc_params.get('critical_process_parameters', 'N/A')}")
                p2.markdown(f"**Workup & Isolation:**\n\n{proc_params.get('workup_and_isolation', 'N/A')}")
                p3.markdown(f"**Impurity Risks:**\n\n{proc_params.get('impurity_profile_risks', 'N/A')}")

            st.markdown("---")

    # --- Export Controls ---
    st.markdown("### 📥 Export Comprehensive Mechanism Dossier")
    exp_col1, exp_col2 = st.columns(2)
    
    with exp_col1:
        logo_data = uploaded_logo.getvalue() if uploaded_logo else None
        pdf_bytes = build_pdf_report(
            route_data=results,
            file_name=active_filename,
            logo_bytes=logo_data,
            org_name=org_name_input,
            theme_name=selected_theme
        )
        st.download_button(
            label="📄 Download Mechanism Dossier (PDF)",
            data=pdf_bytes,
            file_name=f"mechanism_dossier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with exp_col2:
        st.download_button(
            label="📊 Download Raw Analysis (JSON)",
            data=json.dumps(results, indent=2),
            file_name=f"mechanism_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
