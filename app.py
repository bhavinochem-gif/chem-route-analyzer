import io
import json
import streamlit as st
from PIL import Image
from google import genai

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

# --- Custom Styling ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .stCodeBlock {
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("⚗️ Automated Chemical Route & Mechanism Engine")
st.caption("Upload Route of Synthesis (CDXML / PDF) to elucidate named reactions, 2D structures, arrow-pushing mechanisms, and process scale-up parameters.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_key_input = st.text_input(
        "Gemini API Key",
        type="password",
        help="Paste your Google AI Studio API key starting with AIzaSy..."
    )
    
    # Resolve and clean up API key
    raw_key = api_key_input or st.secrets.get("GEMINI_API_KEY", "")
    resolved_api_key = raw_key.strip().strip('"').strip("'")
    
    # Pre-Flight Connection Tester
    if st.button("🔌 Test API Connection", use_container_width=True):
        if not resolved_api_key:
            st.warning("⚠️ Please provide an API key or define it in Secrets.")
        elif not resolved_api_key.startswith("AIzaSy"):
            st.error("❌ Invalid format: Google AI Studio keys must start with 'AIzaSy'.")
        else:
            with st.spinner("Testing API connection..."):
                try:
                    test_client = genai.Client(api_key=resolved_api_key)
                    ping_res = test_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents="Respond with 'OK'."
                    )
                    if ping_res.text:
                        st.success("✅ Connection Successful! API key is active.")
                except Exception as err:
                    err_text = str(err)
                    if "400" in err_text or "API_KEY_INVALID" in err_text:
                        st.error("❌ Invalid API Key: Key rejected by Google authentication.")
                    elif "403" in err_text:
                        st.error("❌ Access Denied: Verify Generative Language API is enabled.")
                    else:
                        st.error(f"❌ Connection failed: {err_text}")

    st.markdown("---")
    st.header("📁 Route Upload")
    uploaded_cdxml = st.file_uploader("Upload ChemDraw File (.cdxml)", type=["cdxml", "xml"])
    uploaded_pdf = st.file_uploader("Upload Synthesis Route (.pdf)", type=["pdf"])

# Enforce API Key
if not resolved_api_key:
    st.info("👈 Please enter your Gemini API key in the sidebar and verify connection to proceed.")
    st.stop()

# Initialize Client
client = genai.Client(api_key=resolved_api_key)

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
        with st.spinner("Classifying named reactions, mapping 2D structures, and detailing electron flow..."):
            try:
                results = analyze_ros(
                    client=client,
                    text_context=parsed_text,
                    images=pdf_images
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
                
                # Attempt 2D Reaction SMARTS rendering first
                rxn_smarts = step.get("reaction_smarts", "")
                rxn_rendered = False
                
                if rxn_smarts and ">" in rxn_smarts:
                    rxn_buf = render_reaction_scheme(rxn_smarts)
                    if rxn_buf:
                        st.image(rxn_buf, caption=f"Step {step_num} 2D Transformation", use_container_width=True)
                        rxn_rendered = True
                
                # Fallback to individual Starting Material & Product rendering
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
                
                arrow_steps = mech_data.get("arrow_pushing_description", [])
                for flow_step in arrow_steps:
                    st.markdown(f"• {flow_step}")
                
                intermediates = mech_data.get("key_intermediates", [])
                if intermediates:
                    st.markdown("**Key Intermediates / Transition States:**")
                    for inter in intermediates:
                        st.markdown(f"- **{inter.get('name', 'Intermediate')}:** `{inter.get('smiles_or_desc', '')}`")

            # Process Parameters Expander
            proc_params = step.get("process_parameters", {})
            with st.expander(f"📋 Step {step_num} Process Chemistry & Scale-Up Controls", expanded=False):
                p1, p2, p3 = st.columns(3)
                p1.markdown(f"**Critical Process Parameters (CPPs):**\n\n{proc_params.get('critical_process_parameters', 'N/A')}")
                p2.markdown(f"**Workup & Isolation:**\n\n{proc_params.get('workup_and_isolation', 'N/A')}")
                p3.markdown(f"**Impurity Profile Risks:**\n\n{proc_params.get('impurity_profile_risks', 'N/A')}")

            st.markdown("---")

    # Download Report Option
    st.download_button(
        label="📥 Download Route Analysis (JSON)",
        data=json.dumps(results, indent=2),
        file_name="route_of_synthesis_analysis.json",
        mime="application/json",
        use_container_width=True
    )
else:
    if not (uploaded_cdxml or uploaded_pdf):
        st.info("👈 Upload a `.cdxml` or `.pdf` file in the sidebar to begin synthetic route analysis.")
