import streamlit as st
from google import genai
from src.parsers import extract_cdxml_data, extract_pdf_pages
from src.chem_renderer import render_reaction_scheme, render_molecule_smiles
from src.mechanism_engine import analyze_ros

st.set_page_config(page_title="AI Chemical Route & Mechanism Engine", layout="wide", page_icon="⚗️")

st.title("⚗️ Chemical Route & Mechanism Platform")
st.caption("Upload ChemDraw (.cdxml) or synthesis route PDFs to automatically generate named reactions, 2D structures, arrow-pushing mechanisms, and plant process summaries.")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password", help="Enter your Gemini API key")
    st.markdown("---")
    uploaded_cdxml = st.file_uploader("Upload ChemDraw File (.cdxml)", type=["cdxml", "xml"])
    uploaded_pdf = st.file_uploader("Upload Route PDF (.pdf)", type=["pdf"])

resolved_api_key = api_key or st.secrets.get("GEMINI_API_KEY", None)

if not resolved_api_key:
    st.info("👈 Enter your Gemini API key in the sidebar to begin.")
    st.stop()

client = genai.Client(api_key=resolved_api_key)

if uploaded_cdxml or uploaded_pdf:
    st.subheader("📄 Route Inputs Preview")
    prev_col1, prev_col2 = st.columns(2)
    parsed_text = ""
    pdf_images = []

    with prev_col1:
        if uploaded_cdxml:
            st.success(f"ChemDraw Loaded: `{uploaded_cdxml.name}`")
            parsed_text = extract_cdxml_data(uploaded_cdxml.getvalue())
            with st.expander("Extracted CDXML Entities"):
                st.text(parsed_text)

    with prev_col2:
        if uploaded_pdf:
            st.success(f"PDF Route Loaded: `{uploaded_pdf.name}`")
            pdf_images = extract_pdf_pages(uploaded_pdf.getvalue())
            if pdf_images:
                st.image(pdf_images[0], caption="Route Scheme (Page 1)", use_container_width=True)

    if st.button("🚀 Analyze Route & Elucidate Mechanisms", type="primary"):
        with st.spinner("Classifying named reactions, mapping 2D structures, and detailing electron flow..."):
            try:
                results = analyze_ros(client, text_context=parsed_text, images=pdf_images)
                
                st.markdown("---")
                st.header("🧪 Synthesis Route Breakdown")
                st.info(f"**Route Overview:** {results.get('overall_route_summary')}")

                for step in results.get("steps", []):
                    st.subheader(f"Step {step['step_number']}: {step['reaction_name']}")
                    col_scheme, col_mech = st.columns([1, 1])
                    
                    with col_scheme:
                        st.markdown("#### 🔄 Reaction Scheme & Conditions")
                        st.markdown(f"**Conditions:** `{step.get('reagents_solvents_conditions')}`")
                        rxn_buf = render_reaction_scheme(step.get("reaction_smarts", ""))
                        if rxn_buf:
                            st.image(rxn_buf, caption=f"Step {step['step_number']} Scheme", use_container_width=True)
                        else:
                            sub1, sub2 = st.columns(2)
                            sm_buf = render_molecule_smiles(step.get("starting_material_smiles", ""))
                            prod_buf = render_molecule_smiles(step.get("product_smiles", ""))
                            if sm_buf:
                                sub1.image(sm_buf, caption="Starting Material")
                            if prod_buf:
                                sub2.image(prod_buf, caption="Product")

                    with col_mech:
                        st.markdown("#### ⚡ Reaction Mechanism & Electron Flow")
                        mech_data = step.get("mechanism", {})
                        st.markdown(f"**Mechanism Class:** `{mech_data.get('mechanism_type')}`")
                        for flow_step in mech_data.get("arrow_pushing_description", []):
                            st.markdown(f"• {flow_step}")
                            
                        intermediates = mech_data.get("key_intermediates", [])
                        if intermediates:
                            st.markdown("**Key Intermediates:**")
                            for inter in intermediates:
                                st.markdown(f"- *{inter.get('name')}:* `{inter.get('smiles_or_desc')}`")

                    proc = step.get("process_parameters", {})
                    with st.expander(f"📋 Step {step['step_number']} Process & Scale-up Parameters"):
                        p1, p2, p3 = st.columns(3)
                        p1.markdown(f"**Critical Parameters:**\n{proc.get('critical_process_parameters', 'N/A')}")
                        p2.markdown(f"**Workup & Isolation:**\n{proc.get('workup_and_isolation', 'N/A')}")
                        p3.markdown(f"**Impurity Profile:**\n{proc.get('impurity_profile_risks', 'N/A')}")
                    st.markdown("---")
            except Exception as ex:
                st.error(f"Error during analysis: {ex}")
