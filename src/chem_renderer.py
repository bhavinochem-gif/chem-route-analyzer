import io
from rdkit import Chem
from rdkit.Chem import AllChem, Draw

def render_reaction_scheme(rxn_smarts: str) -> io.BytesIO:
    """Renders 2D reaction SMARTS scheme into a PNG buffer."""
    try:
        rxn = AllChem.ReactionFromSmarts(rxn_smarts, useSmiles=True)
        drawer = Draw.MolDraw2DCairo(750, 250)
        drawer.DrawReaction(rxn)
        drawer.FinishDrawing()
        
        output = io.BytesIO(drawer.GetDrawingText())
        output.seek(0)
        return output
    except Exception:
        return None

def render_molecule_smiles(smiles: str) -> io.BytesIO:
    """Renders a single intermediate or starting material from SMILES."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None
        img = Draw.MolToImage(mol, size=(300, 250))
        output = io.BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output
    except Exception:
        return None
