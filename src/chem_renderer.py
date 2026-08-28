import io
from rdkit import Chem
from rdkit.Chem import AllChem, Draw
from rdkit.Chem.Draw import rdMolDraw2D

def render_reaction_scheme(rxn_smarts: str, show_atom_numbers: bool = True) -> io.BytesIO | None:
    """Renders 2D reaction transformation with optional atom-mapping numbers."""
    try:
        rxn = AllChem.ReactionFromSmarts(rxn_smarts, useSmiles=True)
        drawer = Draw.MolDraw2DCairo(800, 260)
        
        # Configure drawing options for clear textbook presentation
        opts = drawer.drawOptions()
        opts.showAtomMapNumber = show_atom_numbers
        opts.bondLineWidth = 2
        opts.fixedFontSize = 14
        
        drawer.DrawReaction(rxn)
        drawer.FinishDrawing()
        
        output = io.BytesIO(drawer.GetDrawingText())
        output.seek(0)
        return output
    except Exception:
        return None

def render_molecule_smiles(smiles: str, show_atom_numbers: bool = True) -> io.BytesIO | None:
    """Renders 2D chemical structure with atom numbers on carbons."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return None
            
        drawer = Draw.MolDraw2DCairo(350, 240)
        opts = drawer.drawOptions()
        opts.bondLineWidth = 2
        
        # Label heavy atoms with sequential numbers if requested
        if show_atom_numbers:
            for idx, atom in enumerate(mol.GetAtoms()):
                if atom.GetSymbol() == "C":
                    atom.SetProp("atomLabel", f"{atom.GetSymbol()}_{idx+1}")
                    
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        
        output = io.BytesIO(drawer.GetDrawingText())
        output.seek(0)
        return output
    except Exception:
        return None
