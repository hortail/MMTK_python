# This module contains code for solvation.
#
# Written by Konrad Hinsen
# last revision: 2009-4-29
#

"""
Solvation of solute molecules
"""

__docformat__ = 'epytext'

from MMTK import ChemicalObjects, Units, Universe
from MMTK.MolecularSurface import surfaceAndVolume
from MMTK.Minimization import SteepestDescentMinimizer
from MMTK.Dynamics import VelocityVerletIntegrator, VelocityScaler, \
                          TranslationRemover, RotationRemover
from MMTK.Trajectory import Trajectory, TrajectoryOutput, SnapshotGenerator, \
                            StandardLogOutput
import copy

#
# Calculate the number of solvent molecules
#
def numberOfSolventMolecules(universe, solvent, density):
    """
    @param universe: a finite universe
    @type universe: L{MMTK.Universe.Universe}
    @param solvent: a molecule, or the name of a molecule in the database
    @type solvent: L{MMTK.ChemicalObject.Molecule} or C{str}
    @param density: the density of the solvent (amu/nm**3)
    @type density: C{float}
    @returns: the number of solvent molecules that must be added to the
              universe, in addition to whatever it already contains,
              to obtain the given solvent density.
    @rtype: C{int}
    """
    if isinstance(solvent, str):
	solvent = ChemicalObjects.Molecule(solvent)
    cell_volume = universe.cellVolume()
    if cell_volume is None:
	raise TypeError("universe volume is undefined")
    solute_volume = 0.
    for o in universe._objects:
	solute_volume = solute_volume + surfaceAndVolume(o)[1]
    return int(round(density*(cell_volume-solute_volume)/solvent.mass()))

#
# Add solvent to a universe containing solute molecules.
#
def addSolvent(universe, solvent, density, scale_factor=4.):
    """
    Scales up the universeand adds as many solvent molecules
    as are necessary to obtain the specified solvent density,
    taking account of the solute molecules that are already present
    in the universe. The molecules are placed at random positions
    in the scaled-up universe, but without overlaps between
    any two molecules.

    @param universe: a finite universe
    @type universe: L{MMTK.Universe.Universe}
    @param solvent: a molecule, or the name of a molecule in the database
    @type solvent: L{MMTK.ChemicalObject.Molecule} or C{str}
    @param density: the density of the solvent (amu/nm**3)
    @type density: C{float}
    @param scale_factor: the factor by which the initial universe is
                         expanded before adding the solvent molecules
    @type scale_factor: C{float}
    """

    # Calculate number of solvent molecules and universe size
    if isinstance(solvent, str):
	solvent = ChemicalObjects.Molecule(solvent)
    cell_volume = universe.cellVolume()
    if cell_volume is None:
	raise TypeError("universe volume is undefined")
    solute = copy.copy(universe._objects)
    solute_volume = 0.
    excluded_regions = []
    for o in solute:
	solute_volume = solute_volume + surfaceAndVolume(o)[1]
	excluded_regions.append(o.boundingSphere())
    n_solvent = int(round(density*(cell_volume-solute_volume)/solvent.mass()))
    solvent_volume = n_solvent*solvent.mass()/density
    cell_volume = solvent_volume + solute_volume
    universe.translateBy(-solute.position())
    universe.scaleSize((cell_volume/universe.cellVolume())**(1./3.))

    # Scale up the universe and add solvent molecules at random positions
    universe.scaleSize(scale_factor)
    universe.scale_factor = scale_factor
    for i in range(n_solvent):
	m = copy.copy(solvent)
	m.translateTo(universe.randomPoint())
	while True:
	    s = m.boundingSphere()
	    collision = False
	    for region in excluded_regions:
		if (s.center-region.center).length() < s.radius+region.radius:
		    collision = True
		    break
	    if not collision:
		break
	    m.translateTo(universe.randomPoint())
	universe.addObject(m)
	excluded_regions.append(s)

#
# Shrink the universe to its final size
#
def shrinkUniverse(universe, temperature=300.*Units.K, trajectory=None,
                   scale_factor=0.95):
    """
    Shrinks the universe, which must have been scaled up by
    L{MMTK.Solvation.addSolvent}, back to its original size.
    The compression is performed in small steps, in between which
    some energy minimization and molecular dynamics steps are executed.
    The molecular dynamics is run at the given temperature, and
    an optional trajectory can be specified in which intermediate
    configurations are stored.

    @param universe: a finite universe
    @type universe: L{MMTK.Universe.Universe}
    @param temperature: the temperature at which the Molecular Dynamics
                        steps are run
    @type temperature: C{float}
    @param trajectory: the trajectory in which the progress of the
                       shrinking procedure is stored, or a filename
    @type trajectory: L{MMTK.Trajectory.Trajectory} or C{str}
    @param scale_factor: the factor by which the universe is scaled
                         at each reduction step
    @type scale_factor: C{float}
    """

    # Set velocities and initialize trajectory output
    universe.initializeVelocitiesToTemperature(temperature)
    if trajectory is not None:
        if isinstance(trajectory, str):
            trajectory = Trajectory(universe, trajectory, "w",
                                    "solvation protocol")
            close_trajectory = True
        else:
            close_trajectory = False
        actions = [TrajectoryOutput(trajectory, ["configuration"], 0, None, 1)]
        snapshot = SnapshotGenerator(universe, actions=actions)
        snapshot()

    # Do some minimization and equilibration
    minimizer = SteepestDescentMinimizer(universe, step_size = 0.05*Units.Ang)
    actions = [VelocityScaler(temperature, 0.01*temperature, 0, None, 1),
               TranslationRemover(0, None, 20)]
    integrator = VelocityVerletIntegrator(universe, delta_t = 0.5*Units.fs,
                                          actions = actions)
    for i in range(5):
	minimizer(steps = 40)
    integrator(steps = 200)

    # Scale down the system in small steps
    i = 0
    while universe.scale_factor > 1.:
        if trajectory is not None and i % 1 == 0:
            snapshot()
        i = i + 1
	step_factor = max(scale_factor, 1./universe.scale_factor)
	for object in universe:
	    object.translateTo(step_factor*object.position())
	universe.scaleSize(step_factor)
	universe.scale_factor = universe.scale_factor*step_factor
	for i in range(3):
	    minimizer(steps = 10)
	integrator(steps = 50)

    del universe.scale_factor

    if trajectory is not None:
        snapshot()
        if close_trajectory:
            trajectory.close()
