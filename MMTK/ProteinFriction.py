# Friction constants for protein C-alpha models
#
# Written by Konrad Hinsen
# last revision: 2009-5-13
#

"""
A friction constant model for C-alpha models of proteins
"""

__docformat__ = 'epytext'

import MMTK.ParticleProperties
from Scientific import N

def calphaFrictionConstants(protein, set=2):
    """
    @param protein: a c_alpha model protein
    @type protein: L{MMTK.Proteins.Protein}
    @param set: the number of a friction constant set (1, 2, 3, or 4)
    @return: the estimated friction constants for the atoms in the protein
    @rtype: L{MMTK.ParticleProperties.ParticleScalar}
    """
    radius = 1.5
    atoms = protein.atomCollection()
    f = MMTK.ParticleProperties.ParticleScalar(protein.universe())
    for chain in protein:
        for residue in chain:
            a = residue.peptide.C_alpha
            m = atoms.selectShell(a.position(), radius).mass()
            d = 3.*m/(4.*N.pi*radius**3)
            if set == 1:  # linear fit to initial slope
                f[a] = 121.2*d-8600
            elif set == 2:  # exponential fit 400 steps
                f[a] = 68.2*d-5160
            elif set == 3:  # exponential fit 200 steps
                f[a] = 38.2*d-2160
            elif set == 4:  # expansion fit 50 steps
                f[a] = 20.4*d-500.
                
    return f
