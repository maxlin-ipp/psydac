# coding: utf-8

from numpy import unique

from spl.linalg.stencil import (Vector, VectorSpace)
from spl.fem.basic import (SpaceBase, FieldBase)


#===============================================================================
class SplineSpace( SpaceBase ):
    """
    a 1D Splines Finite Element space

    Parameters
    ----------
    knots : array_like
        Coordinates of knots (clamped or extended by periodicity).

    degree : int
        Polynomial degree.

    periodic : bool
        True if domain is periodic, False otherwise.
        Default: False

    dirichlet : tuple, list
        True if using homogeneous dirichlet boundary conditions, False
        otherwise. Must be specified for each bound
        Default: (False, False)

    """
    def __init__( self, knots, degree, periodic=False, dirichlet=(False, False) ):

        self._knots    = knots
        self._degree   = degree
        self._periodic = periodic
        self._dirichlet = dirichlet
        self._ncells   = None # TODO will be computed later
        self._nbasis   = None # TODO self._ncells if periodic else self._ncells+degree
        if periodic:
            raise NotImplementedError('periodic bc not yet available')
        else:
            defect = 0
            if dirichlet[0]: defect += 1
            if dirichlet[1]: defect += 1
            self._nbasis = len(knots) - degree - 1 - defect

        starts = [0]            # [0, 0]
        ends = [self.dimension] # [n1, n2]
        pads = [degree]         # [p1, p2]
        self._vector_space = VectorSpace(starts, ends, pads)

    @property
    def vector_space(self):
        """Returns the topological associated vector space."""
        return self._vector_space

    @property
    def degree( self ):
        """ Degree of B-splines.
        """
        return self._degree

    @property
    def ncells( self ):
        """ Number of cells in domain.
        """
        return self._ncells

    @property
    def dimension( self ):
        """
        """
        return self._nbasis

    @property
    def periodic( self ):
        """ True if domain is periodic, False otherwise.
        """
        return self._periodic

    @property
    def dirichlet( self ):
        """ True if using homogeneous dirichlet boundary conditions, False otherwise.
        """
        return self._dirichlet

    @property
    def knots( self ):
        """ Knot sequence.
        """
        return self._knots

    @property
    def breaks( self ):
        """ List of breakpoints.
        """
        if not self.periodic:
            return unique(self.knots)
        else:
            p = self._degree
            return self._knots[p:-p]

    @property
    def domain( self ):
        """ Domain boundaries [a,b].
        """
        breaks = self.breaks
        return breaks[0], breaks[-1]

    @property
    def greville( self ):
        """ Coordinates of all Greville points.
        """
        raise NotImplementedError('TODO')

    def __str__(self):
        """Pretty printing"""
        txt  = '\n'
        txt += '> Dimension :: {dim}\n'.format(dim=self.dimension)
        txt += '> Degree    :: {degree}'.format(degree=self.degree)
        return txt

#===============================================================================
class Spline( FieldBase ):
    """
    A field spline is an element of the SplineSpace.

    """
    def __init__(self, space):
        self._space = space
        self._vector = Vector( space.vector_space )

    @property
    def space( self ):
        return self._space

    @property
    def vector( self ):
        return self._vector



def test_1d():
    knots = [0., 0., 0., 1., 1., 1.]
    p = 2
    V = SplineSpace(knots, p)
    print (V)
    F = Spline(V)

def test_2d():
    knots_1 = [0., 0., 0., 1., 1., 1.]
    knots_2 = [0., 0., 0., 0.5, 1., 1., 1.]
    p_1 = 2
    p_2 = 2
    V1 = SplineSpace(knots_1, p_1)
    V2 = SplineSpace(knots_2, p_2)

    from spl.linalg.tensor import TensorSpace
    V = TensorSpace(V1, V2)
    print (V)


###############################################
if __name__ == '__main__':
#    test_1d()
    test_2d()
