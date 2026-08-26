import io
import json
import streamlit as st
from PIL import Image
from groq import Groq

from src.parsers import extract_cdxml_data, extract_pdf_pages
from src.chem_renderer import render_reaction_scheme, render_molecule_smiles
from src.mechanism_engine import analyze_ros

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Chemical Route & Mechanism Engine",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚗️ Chemical Route & Mechanism Platform (Groq Engine)")
st.caption("Automated reaction classification, 2D structures, electron-pushing mechanisms, and process scale-up parameters.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Groq Configuration")
    
    api_key_input = st.text_input(
        "Groq API Key",
        type="password",
        help="Paste your Groq API key starting with gsk_..."
    )
    
    raw_key = api_key_input or st.secrets.get("GROQ_API_KEY", "")
    resolved_api_key = raw_key.strip().strip('"').strip("'")
    
    # Pre-Flight Connection Tester & Dynamic Model Fetcher
    if st.button("🔌 Test Groq Connection", use_container_width=True):
        if not resolved_api_key:
            st.warning("⚠️ Please provide a Groq API key or define it in Secrets.")
        elif not resolved_api_key.startswith("gsk_"):
            st.error("❌ Invalid format: Groq API keys must start with 'gsk_'.")
        else:
            with st.spinner("Connecting to Groq and fetching active models..."):
                try:
                    test_client = Groq(api_key=resolved_api_key)
                    # Fetch active models dynamically to prevent 404 errors
                    models_response = test_client.models.list()
                    active_models = [
                        m.id for m in models_response.data 
                        if "whisper" not in m.id and "guard" not in m.id
                    ]
                    st.session_state["groq_available_models"] = active_models
                    st.success(f"✅ Connected! Found {len(active_models)} available models.")
                except Exception as err:
                    st.error(f"❌ Connection failed: {err}")

    st.markdown("---")
    
    # Dynamic or Fallback Model Selector
    available_models = st.session_state.get(
        "groq_available_models", 
        ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
    )
    
    selected_model = st.selectbox(
        "Select Active Model",
        options=available_models,
        index=0,
        help="Select any active text/multimodal model from your Groq account."
    )

    st.markdown("---")
    st.header("📁 Route Upload")
    uploaded_cdxml = st.file_uploader("Upload ChemDraw File (.cdxml)", type=["cdxml", "xml"])
    uploaded_pdf = st.file_uploader("Upload Synthesis Route (.pdf)", type=["pdf"])

# Enforce API Key
if not resolved_api_key:
    st.info("👈 Enter your Groq API key (`gsk_...`) in the sidebar to begin.")
    st.stop()

# Initialize Groq Client
client = Groq(api_key=resolved_api_key)

# --- File Ingestion & Preview Section ---
if uploaded_cdxml or uploaded_pdf:
    st.subheader("📄 Route Preview & Pre-processing")
    col_cdxml, col_pdf = st.columns(2)
    
    parsed_text = ""
    pdf_images = []

    with col_cdxml:
        if uploaded_cdxml:
            st.success(f"Loaded ChemDraw: `{uploaded_cdxml.name}`")
            parsed_text = extract_cdxml_data(uploaded_cdxml.getvalue())
            with st.expander("Parsed CDXML Content", expanded=False):
                st.text(parsed_text)

    with col_pdf:
        if uploaded_pdf:
            st.success(f"Loaded PDF: `{uploaded_pdf.name}`")
            pdf_images = extract_pdf_pages(uploaded_pdf.getvalue())
            if pdf_images:
                st.image(pdf_images[0], caption="Route Scheme (Page 1)", use_container_width=True)

    # --- Run Analysis ---
    if st.button("🚀 Analyze Route & Elucidate Mechanisms", type="primary", use_container_width=True):
        with st.spinner(f"Elucidating mechanisms via {selected_model}..."):
            try:
                results = analyze_ros(
                    client=client,
                    text_context=parsed_text,
                    images=pdf_images,
                    model_name=selected_model
                )
                st.session_state["analysis_results"] = results
            except Exception as ex:
                st.error(f"Error during mechanism elucidation: {ex}")

# --- Results Presentation ---
if "analysis_results" in st.session_state:
    results = st.session_state["analysis_results"]
    
    st.markdown("---")
    st.header("🧪 Synthetic Route Evaluation")
    st.info(f"**Route Strategy Overview:** {results.get('overall_route_summary', 'No summary generated.')}")

    for step in results.get("steps", []):
        step_num = step.get("step_number", 1)
        rxn_name = step.get("reaction_name", "Unclassified Transformation")
        
        with st.container():
            st.markdown(f"### Step {step_num}: {rxn_name}")
            
            scheme_col, mech_col = st.columns([1, 1])
            
            with scheme_col:
                st.markdown("#### 🔄 Reaction Scheme & Conditions")
                st.markdown(f"**Reagents & Conditions:** `{step.get('reagents_solvents_conditions', 'N/A')}`")
                
                rxn_smarts = step.get("reaction_smarts", "")
                rxn_rendered = False
                
                if rxn_smarts and ">" in rxn_smarts:
                    rxn_buf = render_reaction_scheme(rxn_smarts)
                    if rxn_buf:
                        st.image(rxn_buf, caption=f"Step {step_num} 2D Transformation", use_container_width=True)
                        rxn_rendered = True
                
                if not rxn_rendered:
                    sm_col, prod_col = st.columns(2)
                    sm_smiles = step.get("starting_material_smiles", "")
                    prod_smiles = step.get("product_smiles", "")
                    
                    sm_buf = render_molecule_smiles(sm_smiles) if sm_smiles else None
                    prod_buf = render_molecule_smiles(prod_smiles) if prod_smiles else None
                    
                    if sm_buf:
                        sm_col.image(sm_buf, caption="Starting Material", use_container_width=True)
                    elif sm_smiles:
                        sm_col.code(sm_smiles, language="text")
                        
                    if prod_buf:
                        prod_col.image(prod_buf, caption="Product / Intermediate", use_container_width=True)
                    elif prod_smiles:
                        prod_col.code(prod_smiles, language="text")

            with mech_col:
                st.markdown("#### ⚡ Reaction Mechanism & Electron Flow")
                mech_data = step.get("mechanism", {})
                st.markdown(f"**Mechanism Class:** `{mech_data.get('mechanism_type', 'N/A')}`")
                
                for flow_step in mech_data.get("arrow_pushing_description", []):
                    st.markdown(f"• {flow_step}")
                
                intermediates = mech_data.get("key_intermediates", [])
                if intermediates:
                    st.markdown("**Key Intermediates / Catalytic Species:**")
                    for inter in intermediates:
                        st.markdown(f"- **{inter.get('name', 'Intermediate')}:** `{inter.get('smiles_or_desc', '')}`")

            proc_params = step.get("process_parameters", {})
            with st.expander(f"📋 Step {step_num} Process Chemistry & Scale-Up Controls", expanded=False):
                p1, p2, p3 = st.columns(3)
                p1.markdown(f"**Critical Process Parameters (CPPs):**\n\n{proc_params.get('critical_process_parameters', 'N/A')}")
                p2.markdown(f"**Workup & Isolation:**\n\n{proc_params.get('workup_and_isolation', 'N/A')}")
                p3.markdown(f"**Impurity Profile Risks:**\n\n{proc_params.get('impurity_profile_risks', 'N/A')}")

            st.markdown("---")

    st.download_button(
        label="📥 Download Route Analysis (JSON)",
        data=json.dumps(results, indent=2),
        file_name="route_of_synthesis_analysis.json",
        mime="application/json",
        use_container_width=True
    )
