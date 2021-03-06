# Harmonic restraint terms that can be added to a force field.
#
# Written by Konrad Hinsen
# last revision: 2009-5-13
#

"""
Harmonic restraint terms that can be added to any force field

Example::

 from MMTK import *
 from MMTK.ForceFields import Amber99ForceField
 from MMTK.ForceFields.Restraints import HarmonicDistanceRestraint
 
 universe = InfiniteUniverse()
 universe.protein = Protein('bala1')
 force_field = Amber99ForceField() + \
               HarmonicDistanceRestraint(universe.protein[0][1].peptide.N,
                                         universe.protein[0][1].peptide.O,
                                         0.5, 10.)
 universe.setForceField(force_field)
"""

__docformat__ = 'epytext'

from MMTK.ForceFields.ForceField import ForceField
from MMTK_forcefield import HarmonicDistanceTerm, HarmonicAngleTerm, \
                            CosineDihedralTerm
from Scientific import N

class HarmonicDistanceRestraint(ForceField):

    """
    Harmonic distance restraint between two atoms
    """

    def __init__(self, atom1, atom2, distance, force_constant):
        """
        @param atom1: first atom
        @type atom1: L{MMTK.ChemicalObjects.Atom}
        @param atom2: second atom
        @type atom2: L{MMTK.ChemicalObjects.Atom}
        @param distance: the distance at which the restraint is zero
        @type distance: C{float}
        @param force_constant: the force constant of the restraint term.
                               The functional form of the restraint is
                               force_constant*((r1-r2).length()-distance)**2,
                               where r1 and r2 are the positions of the
                               two atoms.
        """
        self.index1, self.index2 = self.getAtomParameterIndices((atom1, atom2))
        self.arguments = (self.index1, self.index2, distance, force_constant) 
        self.distance = distance
        self.force_constant = force_constant
        ForceField.__init__(self, 'harmonic distance restraint')

    def evaluatorParameters(self, universe, subset1, subset2, global_data):
        if subset1 is not None:
            s1 = subset1.atomList()
            s2 = subset2.atomList()
            if not ((self.atom1 in s1 and self.atom2 in s2) or \
                    (self.atom1 in s2 and self.atom2 in s1)):
                raise ValueError("restraint outside subset")
        return {'harmonic_distance_term':
                [(self.index1, self.index2,
                  self.distance, self.force_constant)]}

    def evaluatorTerms(self, universe, subset1, subset2, global_data):
        params = self.evaluatorParameters(universe, subset1, subset2,
                                          global_data)['harmonic_distance_term']
        assert len(params) == 1
        indices = N.array([params[0][:2]])
        parameters = N.array([params[0][2:]])
        return [HarmonicDistanceTerm(universe._spec, indices, parameters,
                                     self.name)]

    def description(self):
        return 'ForceFields.Restraints.' + self.__class__.__name__ + \
               `self.arguments`


class HarmonicAngleRestraint(ForceField):

    """
    Harmonic angle restraint between three atoms
    """

    def __init__(self, atom1, atom2, atom3, angle, force_constant):
        """
        @param atom1: first atom
        @type atom1: L{MMTK.ChemicalObjects.Atom}
        @param atom2: second (central) atom
        @type atom2: L{MMTK.ChemicalObjects.Atom}
        @param atom3: third atom
        @type atom3: L{MMTK.ChemicalObjects.Atom}
        @param angle: the angle at which the restraint is zero
        @type angle: C{float}
        @param force_constant: the force constant of the restraint term.
                               The functional form of the restraint is
                               force_constant*(phi-angle)**2, where
                               phi is the angle atom1-atom2-atom3.
        """
        self.index1, self.index2, self.index3 = \
                    self.getAtomParameterIndices((atom1, atom2, atom3))
        self.arguments = (self.index1, self.index2, self.index3,
                          angle, force_constant) 
        self.angle = angle
        self.force_constant = force_constant
        ForceField.__init__(self, 'harmonic angle restraint')

    def evaluatorParameters(self, universe, subset1, subset2, global_data):
        return {'harmonic_angle_term':
                 [(self.index1, self.index2, self.index3,
                   self.angle, self.force_constant)]}

    def evaluatorTerms(self, universe, subset1, subset2, global_data):
        params = self.evaluatorParameters(universe, subset1, subset2,
                                          global_data)['harmonic_angle_term']
        assert len(params) == 1
        indices = N.array([params[0][:3]])
        parameters = N.array([params[0][3:]])
        return [HarmonicAngleTerm(universe._spec, indices, parameters,
                                  self.name)]

class HarmonicDihedralRestraint(ForceField):

    """
    Harmonic dihedral angle restraint between four atoms
    """

    def __init__(self, atom1, atom2, atom3, atom4, dihedral, force_constant):
        """
        @param atom1: first atom
        @type atom1: L{MMTK.ChemicalObjects.Atom}
        @param atom2: second (axis) atom
        @type atom2: L{MMTK.ChemicalObjects.Atom}
        @param atom3: third (axis)atom
        @type atom3: L{MMTK.ChemicalObjects.Atom}
        @param atom4: fourth atom
        @type atom4: L{MMTK.ChemicalObjects.Atom}
        @param dihedral: the dihedral angle at which the restraint is zero
        @type dihedral: C{float}
        @param force_constant: the force constant of the restraint term.
                               The functional form of the restraint is
                               force_constant*(phi-|dihedral|)**2, where
                               phi is the dihedral angle
                               atom1-atom2-atom3-atom4.
        """
        self.index1, self.index2, self.index3, self.index4 = \
                   self.getAtomParameterIndices((atom1, atom2, atom3, atom4))
        self.dihedral = dihedral
        self.force_constant = force_constant
        self.arguments = (self.index1, self.index2, self.index3, self.index4,
                          dihedral, force_constant) 
        ForceField.__init__(self, 'harmonic dihedral restraint')

    def evaluatorParameters(self, universe, subset1, subset2, global_data):
        return {'cosine_dihedral_term': [(self.index1, self.index2,
                                          self.index3, self.index4,
                                          0., self.dihedral,
                                          0., self.force_constant)]}

    def evaluatorTerms(self, universe, subset1, subset2, global_data):
        params = self.evaluatorParameters(universe, subset1, subset2,
                                          global_data)['cosine_dihedral_term']
        assert len(params) == 1
        indices = N.array([params[0][:4]])
        parameters = N.array([params[0][4:]])
        return [CosineDihedralTerm(universe._spec, indices, parameters,
                                   self.name)]
