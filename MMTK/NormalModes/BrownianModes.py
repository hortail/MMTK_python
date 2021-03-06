# Brownian normal mode calculations.
#
# Written by Konrad Hinsen
# last revision: 2009-5-12
#

"""
Brownian normal modes
"""

__docformat__ = 'epytext'

from MMTK import Features, Units, ParticleProperties, Random
from Scientific.Functions.Interpolation import InterpolatingFunction
from Scientific import N

from MMTK.NormalModes import Core

#
# Class for a single mode
#
class BrownianMode(Core.Mode):

    """
    Single Brownian normal mode

    Mode objects are created by indexing a L{BrownianModes} object.
    They contain the atomic displacements corresponding to a single
    mode. In addition, the inverse of the relaxation time corresponding
    to the mode is stored in the attribute "inv_relaxation_time".

    Note: the Brownian mode vectors are not friction weighted and therefore
    not orthogonal to each other.
    """

    def __init__(self, universe, n, inv_relaxation_time, mode):
        self.inv_relaxation_time = inv_relaxation_time
        Core.Mode.__init__(self, universe, n, mode)

    def __str__(self):
        return 'Mode ' + `self.number` + \
               ' with inverse relaxation time ' \
               + `self.inv_relaxation_time`

    __repr__ = __str__

#
# Class for a full set of normal modes
#
class BrownianModes(Core.NormalModes):

    """
    Brownian modes describe the independent relaxation motions of a
    harmonic system with friction. They are obtained by diagonalizing the
    friction-weighted force constant matrix.

    In order to obtain physically reasonable normal modes, the configuration
    of the universe must correspond to a local minimum of the potential
    energy.

    Individual modes (see class L{BrownianMode})
    can be extracted by indexing with an integer. Looping over the modes
    is possible as well.
    """

    """Brownian normal modes

    Constructor: BrownianModes(|universe|, |friction|, |temperature|=300,
                               |subspace|=None, |delta|=None, |sparse|=None)

    Arguments:

    |friction| -- a Class:MMTK.ParticleScalar object specifying the
                  friction coefficient for each particle.
                  Note: The friction coefficients are not mass-weighted,
                  i.e. they have the dimension of an inverse time.

    Brownian modes describe the independent relaxation motions of a
    harmonic system with friction. They are obtained by diagonalizing the
    friction-weighted force constant matrix.

    In order to obtain physically reasonable normal modes, the configuration
    of the universe must correspond to a local minimum of the potential
    energy.

    A BrownianModes object behaves like a sequence of modes.
    Individual modes (see class Class:MMTK.NormalModes.BrownianMode)
    can be extracted by indexing with an integer. Looping over the modes
    is possible as well.
    """

    features = []

    def __init__(self, universe = None, friction = None,
                 temperature = 300.*Units.K,
                 subspace = None, delta = None, sparse = False):
        """
        @param universe: the system for which the normal modes are calculated;
                         it must have a force field which provides the second
                         derivatives of the potential energy
        @type universe: L{MMTK.Universe.Universe}
        @param friction: the friction coefficient for each particle.
                         Note: The friction coefficients are not mass-weighted,
                         i.e. they have the dimension of an inverse time.
        @type friction: L{MMTK.ParticleProperties.ParticleScalar}
        @param temperature: the temperature for which the amplitudes of the
                            atomic displacement vectors are calculated. A
                            value of C{None} can be specified to have no scaling
                            at all. In that case the mass-weighted norm
                            of each normal mode is one.
        @type temperature: C{float}
        @param subspace: the basis for the subspace in which the normal modes
                         are calculated (or, more precisely, a set of vectors
                         spanning the subspace; it does not have to be
                         orthogonal). This can either be a sequence of
                         L{MMTK.ParticleProperties.ParticleVector} objects
                         or a tuple of two such sequences. In the second case,
                         the subspace is defined by the space spanned by the
                         second set of vectors projected on the complement of
                         the space spanned by the first set of vectors.
                         The first set thus defines directions that are
                         excluded from the subspace.
                         The default value of C{None} indicates a standard
                         normal mode calculation in the 3N-dimensional
                         configuration space.
        @param delta: the rms step length for numerical differentiation.
                      The default value of C{None} indicates analytical
                      differentiation.
                      Numerical differentiation is available only when a
                      subspace basis is used as well. Instead of calculating
                      the full force constant matrix and then multiplying
                      with the subspace basis, the subspace force constant
                      matrix is obtained by numerical differentiation of the
                      energy gradients along the basis vectors of the subspace.
                      If the basis is much smaller than the full configuration
                      space, this approach needs much less memory.
        @type delta: C{float}
        @param sparse: a flag that indicates if a sparse representation of
                       the force constant matrix is to be used. This is of
                       interest when there are no long-range interactions and
                       a subspace of smaller size then 3N is specified. In that
                       case, the calculation will use much less memory with a
                       sparse representation.
        @type sparse: C{bool}
        """
        if universe == None:
            return
        Features.checkFeatures(self, universe)
        Core.NormalModes.__init__(self, universe, subspace, delta, sparse,
                                  ['array', 'inv_relaxation_times'])
        self.friction = friction
        self.temperature = temperature

        self.weights = N.sqrt(friction.array)
        self.weights = self.weights[:, N.NewAxis]

        self._forceConstantMatrix()
        ev = self._diagonalize()

        self.inv_relaxation_times = ev
        self.sort_index = N.argsort(self.inv_relaxation_times)
        self.array.shape = (self.nmodes, self.natoms, 3)

        self.cleanup()

    def __getitem__(self, item):
        index = self.sort_index[item]
        return BrownianMode(self.universe, item,
                            self.inv_relaxation_times[index],
                            self.array[index]/self.weights)

    def rawMode(self, item):
        """
        @param item: the index of a normal mode
        @type item: C{int}
        @returns: the unscaled mode vector
        @rtype: L{BrownianMode}
        """
        index = self.sort_index[item]
        return BrownianMode(self.universe, item,
                            self.inv_relaxation_times[index],
                            self.array[index])

    def fluctuations(self, first_mode=6):
        f = ParticleProperties.ParticleScalar(self.universe)
        for i in range(first_mode, self.nmodes):
            mode = self.rawMode(i)
            f += (mode*mode)/mode.inv_relaxation_time
        f = Units.k_B*self.temperature*f/self.friction
        return f

    def meanSquareDisplacement(self, subset=None, weights=None,
                               time_range = (0., None, None),
                               first_mode = 6):
        """
        @param subset: the subset of the universe used in the calculation
                       (default: the whole universe)
        @type subset: L{MMTK.Collections.GroupOfAtoms}
        @param weights: the weight to be given to each atom in the average
                        (default: atomic masses)
        @type weights: L{MMTK.ParticleVectors.ParticleScalar}
        @param time_range: the time values at which the mean-square
                           displacement is evaluated, specified as a
                           range tuple (first, last, step).
                           The defaults are first=0, last=
                           20 times the longest vibration perdiod,
                           and step defined such that 300 points are
                           used in total.
        @type time_range: C{tuple}
        @param first_mode: the first mode to be taken into account for
                           the fluctuation calculation. The default value
                           of 6 is right for molecules in vacuum.
        @type first_mode: C{int}
        @returns: the averaged mean-square displacement of the
                  atoms in subset as a function of time
        @rtype: C{Scientific.Functions.Interpolation.InterpolatingFunction}
        """
        if subset is None:
            subset = self.universe
        if weights is None:
            weights = self.universe.masses()
        weights = weights*subset.booleanMask()
        total = weights.sumOverParticles()
        weights = weights/(total*self.friction)
        first, last, step = (time_range + (None, None))[:3]
        if last is None:
            last = 3./self.rawMode(first_mode).inv_relaxation_time
        if step is None:
            step = (last-first)/300.
        time = N.arange(first, last, step)
        msd = N.zeros(time.shape, N.Float)
        for i in range(first_mode, self.nmodes):
            mode = self.rawMode(i)
            rt = mode.inv_relaxation_time
            d = (weights*(mode*mode)).sumOverParticles()
            N.add(msd, d*(1.-N.exp(-rt*time))/rt, msd)
        N.multiply(msd, 2.*Units.k_B*self.temperature, msd)
        return InterpolatingFunction((time,), msd)

    def staticStructureFactor(self, q_range = (1., 15.), subset=None,
                              weights=None, random_vectors=15,
                              first_mode = 6):
        """
        @param q_range: the range of angular wavenumber values
        @type q_range: C{tuple}
        @param subset: the subset of the universe used in the calculation
                       (default: the whole universe)
        @type subset: L{MMTK.Collections.GroupOfAtoms}
        @param weights: the weight to be given to each atom in the average
                        (default: coherent scattering lengths)
        @type weights: L{MMTK.ParticleVectors.ParticleScalar}
        @param random_vectors: the number of random direction vectors
                               used in the orientational average
        @type random_vectors: C{int}
        @param first_mode: the first mode to be taken into account for
                           the fluctuation calculation. The default value
                           of 6 is right for molecules in vacuum.
        @type first_mode: C{int}
        @returns: the Static Structure Factor as a
                  function of angular wavenumber
        @rtype: C{Scientific.Functions.Interpolation.InterpolatingFunction}
        """
        if subset is None:
            subset = self.universe
        if weights is None:
            weights = self.universe.getParticleScalar('b_coherent')
        mask = subset.booleanMask()
        weights = N.repeat(weights.array, mask.array)
        weights = weights/N.sqrt(N.add.reduce(weights*weights))
        friction = N.repeat(self.friction.array, mask.array)
        r = N.repeat(self.universe.configuration().array, mask.array)

        first, last, step = (q_range+(None,))[:3]
        if step is None:
            step = (last-first)/50.
        q = N.arange(first, last, step)

        kT = Units.k_B*self.temperature
        natoms = subset.numberOfAtoms()
        sq = 0.
        random_vectors = Random.randomDirections(random_vectors)
        for v in random_vectors:
            sab = N.zeros((natoms, natoms), N.Float)
            for i in range(first_mode, self.nmodes):
                irt = self.rawMode(i).inv_relaxation_time
                d = N.repeat((self.rawMode(i)*v).array, mask.array) \
                       / N.sqrt(friction)
                sab = sab + (d[N.NewAxis,:]-d[:,N.NewAxis])**2/irt
            sab = sab[N.NewAxis,:,:]*q[:, N.NewAxis, N.NewAxis]**2
            phase = N.exp(-1.j*q[:, N.NewAxis]
                          * N.dot(r, v.array)[N.NewAxis, :]) \
                    * weights[N.NewAxis, :]
            temp = N.sum(phase[:, :, N.NewAxis]*N.exp(-0.5*kT*sab), 1)
            temp = N.sum(N.conjugate(phase)*temp, 1)
            sq = sq + temp.real
        return InterpolatingFunction((q,), sq/len(random_vectors))

    def coherentScatteringFunction(self, q, time_range = (0., None, None),
                                   subset=None, weights=None,
                                   random_vectors=15, first_mode = 6):
        """
        @param q: the angular wavenumber
        @type q: C{float}
        @param time_range: the time values at which the mean-square
                           displacement is evaluated, specified as a
                           range tuple (first, last, step).
                           The defaults are first=0, last=
                           20 times the longest vibration perdiod,
                           and step defined such that 300 points are
                           used in total.
        @type time_range: C{tuple}
        @param subset: the subset of the universe used in the calculation
                       (default: the whole universe)
        @type subset: L{MMTK.Collections.GroupOfAtoms}
        @param weights: the weight to be given to each atom in the average
                        (default: coherent scattering lengths)
        @type weights: L{MMTK.ParticleVectors.ParticleScalar}
        @param random_vectors: the number of random direction vectors
                               used in the orientational average
        @type random_vectors: C{int}
        @param first_mode: the first mode to be taken into account for
                           the fluctuation calculation. The default value
                           of 6 is right for molecules in vacuum.
        @type first_mode: C{int}
        @returns: the Coherent Scattering Function as a function of time
        @rtype: C{Scientific.Functions.Interpolation.InterpolatingFunction}
        """
        if subset is None:
            subset = self.universe
        if weights is None:
            weights = self.universe.getParticleScalar('b_coherent')
        mask = subset.booleanMask()
        weights = N.repeat(weights.array, mask.array)
        weights = weights/N.sqrt(N.add.reduce(weights*weights))
        friction = N.repeat(self.friction.array, mask.array)
        r = N.repeat(self.universe.configuration().array, mask.array)

        first, last, step = (time_range + (None, None))[:3]
        if last is None:
            last = 3./self.rawMode(first_mode).inv_relaxation_time
        if step is None:
            step = (last-first)/300.
        time = N.arange(first, last, step)

        natoms = subset.numberOfAtoms()
        kT = Units.k_B*self.temperature
        fcoh = N.zeros((len(time),), N.Complex)
        random_vectors = Random.randomDirections(random_vectors)
        for v in random_vectors:
            phase = N.exp(-1.j*q*N.dot(r, v.array))
            for ai in range(natoms):
                fbt = N.zeros((natoms, len(time)), N.Float)
                for i in range(first_mode, self.nmodes):
                    irt = self.rawMode(i).inv_relaxation_time
                    d = q * N.repeat((self.rawMode(i)*v).array, mask.array) \
                        / N.sqrt(friction)
                    ft = N.exp(-irt*time)/irt
                    N.add(fbt,
                          d[ai] * d[:, N.NewAxis] * ft[N.NewAxis, :],
                          fbt)
                    N.add(fbt,
                          (-0.5/irt) * (d[ai]**2 + d[:, N.NewAxis]**2),
                          fbt)
                N.add(fcoh,
                      weights[ai]*phase[ai]
                      * N.dot(weights*N.conjugate(phase),
                              N.exp(kT*fbt)),
                      fcoh)
        return InterpolatingFunction((time,), fcoh.real/len(random_vectors))

    def incoherentScatteringFunction(self, q, time_range = (0., None, None),
                                     subset=None, random_vectors=15,
                                     first_mode = 6):
        """
        @param q: the angular wavenumber
        @type q: C{float}
        @param time_range: the time values at which the mean-square
                           displacement is evaluated, specified as a
                           range tuple (first, last, step).
                           The defaults are first=0, last=
                           20 times the longest vibration perdiod,
                           and step defined such that 300 points are
                           used in total.
        @type time_range: C{tuple}
        @param subset: the subset of the universe used in the calculation
                       (default: the whole universe)
        @type subset: L{MMTK.Collections.GroupOfAtoms}
        @param random_vectors: the number of random direction vectors
                               used in the orientational average
        @type random_vectors: C{int}
        @param first_mode: the first mode to be taken into account for
                           the fluctuation calculation. The default value
                           of 6 is right for molecules in vacuum.
        @type first_mode: C{int}
        @returns: the Incoherent Scattering Function as a function of time
        @rtype: C{Scientific.Functions.Interpolation.InterpolatingFunction}
        """
        if subset is None:
            subset = self.universe
        mask = subset.booleanMask()
        weights_inc = self.universe.getParticleScalar('b_incoherent')
        weights_inc = N.repeat(weights_inc.array**2, mask.array)
        weights_inc = weights_inc/N.add.reduce(weights_inc)
        friction = N.repeat(self.friction.array, mask.array)
        mass = N.repeat(self.universe.masses().array, mask.array)
        r = N.repeat(self.universe.configuration().array, mask.array)

        first, last, step = (time_range + (None, None))[:3]
        if last is None:
            last = 3./self.weighedMode(first_mode).inv_relaxation_time
        if step is None:
            step = (last-first)/300.
        time = N.arange(first, last, step)

        natoms = subset.numberOfAtoms()
        kT = Units.k_B*self.temperature
        finc = N.zeros((len(time),), N.Float)
        eisf = 0.
        random_vectors = Random.randomDirections(random_vectors)
        for v in random_vectors:
            phase = N.exp(-1.j*q*N.dot(r, v.array))
            faat = N.zeros((natoms, len(time)), N.Float)
            eisf_sum = N.zeros((natoms,), N.Float)
            for i in range(first_mode, self.nmodes):
                irt = self.rawMode(i).inv_relaxation_time
                d = q * N.repeat((self.rawMode(i)*v).array, mask.array) \
                    / N.sqrt(friction)
                ft = (N.exp(-irt*time)-1.)/irt
                N.add(faat,
                      d[:, N.NewAxis]**2 * ft[N.NewAxis, :],
                      faat)
                N.add(eisf_sum, -d**2/irt, eisf_sum)
            N.add(finc,
                  N.sum(weights_inc[:, N.NewAxis]
                        * N.exp(kT*faat), 0),
                  finc)
            eisf = eisf + N.sum(weights_inc*N.exp(kT*eisf_sum))
        return InterpolatingFunction((time,), finc/len(random_vectors))


    def EISF(self, q_range = (0., 15.), subset=None, weights = None,
             random_vectors = 15, first_mode = 6):
        """
        @param q_range: the range of angular wavenumber values
        @type q_range: C{tuple}
        @param subset: the subset of the universe used in the calculation
                       (default: the whole universe)
        @type subset: L{MMTK.Collections.GroupOfAtoms}
        @param weights: the weight to be given to each atom in the average
                        (default: incoherent scattering lengths)
        @type weights: L{MMTK.ParticleVectors.ParticleScalar}
        @param random_vectors: the number of random direction vectors
                               used in the orientational average
        @type random_vectors: C{int}
        @param first_mode: the first mode to be taken into account for
                           the fluctuation calculation. The default value
                           of 6 is right for molecules in vacuum.
        @type first_mode: C{int}
        @returns: the Elastic Incoherent Structure Factor (EISF) as a
                  function of angular wavenumber
        @rtype: C{Scientific.Functions.Interpolation.InterpolatingFunction}
        """
        if subset is None:
            subset = self.universe
        if weights is None:
            weights = self.universe.getParticleScalar('b_incoherent')
            weights = weights*weights
        weights = weights*subset.booleanMask()
        total = weights.sumOverParticles()
        weights = weights/total

        first, last, step = (q_range+(None,))[:3]
        if step is None:
            step = (last-first)/50.
        q = N.arange(first, last, step)

        f = ParticleProperties.ParticleTensor(self.universe)
        for i in range(first_mode, self.nmodes):
            mode = self.rawMode(i)
            f = f + (1./mode.inv_relaxation_time)*mode.dyadicProduct(mode)
        f = Units.k_B*self.temperature*f/self.friction

        eisf = N.zeros(q.shape, N.Float)
        random_vectors = Random.randomDirections(random_vectors)
        for v in random_vectors:
            for a in subset.atomList():
                exp = N.exp(-v*(f[a]*v))
                N.add(eisf, weights[a]*exp**(q*q), eisf)
        return InterpolatingFunction((q,), eisf/len(random_vectors))
