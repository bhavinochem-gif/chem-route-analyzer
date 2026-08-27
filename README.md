# ⚗️ Automated Chemical Route & Mechanism Engine

An automated synthesis route evaluation and electron-pushing mechanism elucidation platform built with Streamlit, RDKit, ReportLab, SQLite, and Google Gemini 2.5 Flash.

## 🚀 Features
- **Upload Formats:** Native ChemDraw (`.cdxml`) and synthesis route PDF reports.
- **Cheminformatics Engine:** Automatic RDKit 2D reaction SMARTS and SMILES structure rendering.
- **AI Mechanism Elucidation:** Powered by Gemini 2.5 Flash for reaction naming, arrow-pushing steps, catalytic cycles, and CPPs.
- **Analytical & IPC Specifications:** In-Process Control (IPC) checkpoints, HPLC assay conditions, diagnostic $^1\text{H}$ NMR peak shifts, and MS target predictions.
- **Persistent Storage:** SQLite database library storing past routes with SHA-256 fingerprinting to eliminate redundant API token consumption.
- **Multi-Format Exports:** Branded multi-page PDF dossiers (with company logo and color palettes) and multi-tab Excel spreadsheets.

## ⚙️ Deployment & Setup

1. Clone the repository and install requirements:
   ```bash
   pip install -r requirements.txt
