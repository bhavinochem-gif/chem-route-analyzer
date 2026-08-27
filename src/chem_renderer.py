import io
from rdkit import Chem
from rdkit.Chem import AllChem, Draw

def render_reaction_scheme(rxn_smarts: str) -> io.BytesIO | None:
    """Renders a 2D reaction scheme (Reactants > Reagents > Products)."""
    try:
        rxn = AllChem.ReactionFromSmarts(rxn_smarts, useSmiles=True)
        drawer = Draw.MolDraw2DCairo(750, 240)
        drawer.DrawReaction(rxn)
        drawer.FinishDrawing()
        
        output = io.BytesIO(drawer.GetDrawingText())
        output.seek(0)
        return output
    except Exception:
        return None

def render_molecule_smiles(smiles: str) -> io.BytesIO | None:
    """Renders a 2D chemical structure from a SMILES string."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None
        img = Draw.MolToImage(mol, size=(320, 240))
        output = io.BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output
    except Exception:
        return None
