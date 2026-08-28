import io
from rdkit import Chem
from rdkit.Chem import AllChem, Draw

def render_reaction_scheme(rxn_smarts: str, show_atom_numbers: bool = False) -> io.BytesIO | None:
    """Renders 2D reaction transformation with optional atom-mapping numbers."""
    try:
        rxn = AllChem.ReactionFromSmarts(rxn_smarts, useSmiles=True)
        drawer = Draw.MolDraw2DCairo(800, 240)
        opts = drawer.drawOptions()
        opts.showAtomMapNumber = show_atom_numbers
        opts.bondLineWidth = 2
        opts.fixedFontSize = 13
        
        drawer.DrawReaction(rxn)
        drawer.FinishDrawing()
        
        output = io.BytesIO(drawer.GetDrawingText())
        output.seek(0)
        return output
    except Exception:
        return None

def render_molecule_smiles(smiles: str, width: int = 300, height: int = 200) -> io.BytesIO | None:
    """Renders 2D chemical structure from SMILES."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None
            
        drawer = Draw.MolDraw2DCairo(width, height)
        opts = drawer.drawOptions()
        opts.bondLineWidth = 2
        opts.clearBackground = True
        
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        
        output = io.BytesIO(drawer.GetDrawingText())
        output.seek(0)
        return output
    except Exception:
        return None
