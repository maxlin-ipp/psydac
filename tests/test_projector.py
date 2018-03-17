# -*- coding: UTF-8 -*-

import numpy as np
from numpy import sin, cos, pi
from numpy import bmat

from spl.core import make_open_knots
from spl.core import construct_grid_from_knots
from spl.core import construct_quadrature_grid
from spl.core import eval_on_grid_splines_ders
from spl.core import collocation_matrix
from spl.core import histopolation_matrix
from spl.core import compute_greville

from spl.utilities import gauss_legendre
from spl.utilities import Integral
from spl.utilities import Interpolation
from spl.utilities import Contribution
from spl.utilities import Integral2D

from spl.feec import build_matrices_2d_H1
from spl.feec import mass_matrix
from spl.feec import Interpolation2D

from scipy import kron
from scipy.linalg import block_diag
from scipy.interpolate import splev
from scipy.interpolate import bisplev
from scipy.sparse import diags

from scipy.sparse import csr_matrix, csc_matrix
from scipy.sparse.linalg import splu

# ...
def solve(M, x):
    """Solve y:= Mx using SuperLU."""
    M = csc_matrix(M)
    M_op = splu(M)
    return M_op.solve(x)
# ...


def tck_H1(p, n, T, c):
    return (T[0], T[1], c, p[0], p[1])

def tck_Hcurl(p, n, T, c):
    """."""
    pp = list(p) ; pp[0] -= 1
    nn = list(n) ; nn[0] -= 1
    TT = list(T) ; TT[0] = TT[0][1:-1]
    N = np.array(nn).prod()
    c0 = c[:N]
    tck0 = (TT[0], TT[1], c0, pp[0], pp[1])

    pp = list(p) ; pp[1] -= 1
    nn = list(n) ; nn[1] -= 1
    TT = list(T) ; TT[1] = TT[1][1:-1]
    c1 = c[N:]
    tck1 = (TT[0], TT[1], c1, pp[0], pp[1])

    return tck0, tck1

def tck_L2(p, n, T, c):
    return (T[0][1:-1], T[1][1:-1], c, p[0]-1, p[1]-1)


def scaling_matrix(p, n, T, kind=None):
    """Returns the scaling matrix for M-splines. It is a diagonal matrix whose
    elements are (p+1)/(T[i+p+1]-T[i])"""
    if isinstance(p, int):
        x = np.zeros(n)
        for i in range(0, n):
            x[i] = (p+1)/(T[i+p+1]-T[i])
        return diags(x)

    assert(isinstance(p, (list, tuple)))

    if kind is None:
        Ms = []
        for i in range(0, len(p)):
            M = scaling_matrix(p[i], n[i], T[i])
            Ms.append(M)
        # TODO must be improved
        # we must convert it to dense, otherwise we get a scipy
        Ms = [M.todense() for M in Ms]
        return kron(*Ms)

    elif kind == 'Hcurl':
        Ms = []
        for i in range(0, len(p)):
            pp = list(p) ; pp[i] -= 1
            nn = list(n) ; nn[i] -= 1
            TT = list(T) ; TT[i] = TT[i][1:-1]
            M = scaling_matrix(pp, nn, TT)
            Ms.append(M)
        return block_diag(*Ms)

    elif kind == 'L2':
        pp = list(p)
        nn = list(n)
        TT = list(T)
        for i in range(0, len(p)):
            pp[i] -= 1
            nn[i] -= 1
            TT[i] = TT[i][1:-1]
        return scaling_matrix(pp, nn, TT)

    raise NotImplementedError('TODO')



def test_projectors_1d(verbose=False):
    # ...
    n_elements = 4
    p = 3                    # spline degree
    n = n_elements + p - 1   # number of control points
    # ...

    T    = make_open_knots(p, n)
    grid = compute_greville(p, n, T)

    M = collocation_matrix(p, n, T, grid)
    H = histopolation_matrix(p, n, T, grid)
    mass = mass_matrix(p, n, T)

    histopolation = Integral(p, n, T, kind='greville')
    interpolation = Interpolation(p, n, T)
    contribution = Contribution(p, n, T)

    f = lambda u: u*(1.-u)

    f_0 = solve(M, interpolation(f))
    f_1 = solve(H, histopolation(f))
    f_l2 = solve(mass, contribution(f))

    # ... compute error on H1 for interpolation
    tck = (T, f_0, p)
    fh_0 = lambda x: splev(x, tck)
    diff = lambda x: (f(x) - fh_0(x))**2

    integrate = Integral(p, n, T)
    err_0 = np.sqrt(np.sum(integrate(diff)))
    # ...

    # ... compute error on L2
    pp = p-1
    nn = n-1
    TT = T[1:-1]

    # scale fh_1 coefficients
    S = scaling_matrix(pp, nn, TT)
    f_1  = S.dot(f_1)
    tck = (TT, f_1, pp)
    fh_1 = lambda x: splev(x, tck)
    diff = lambda x: (f(x) - fh_1(x))**2

    integrate = Integral(p, n, T)
    err_1 = np.sqrt(np.sum(integrate(diff)))
    # ...

    # ... compute error on H1 for L2 projection
    tck = (T, f_l2, p)
    fh_0 = lambda x: splev(x, tck)
    diff = lambda x: (f(x) - fh_0(x))**2

    integrate = Integral(p, n, T)
    err_l2 = np.sqrt(np.sum(integrate(diff)))
    # ...

    # ...
    if verbose:
        print ('==== testing projection in 1d ====')
        print ('> l2 error of `f_0` = {}'.format(err_0))
        print ('> l2 error of `f_1` = {}'.format(err_1))
        print ('> l2 error of `f_l2` = {}'.format(err_l2))
    # ...

def test_projectors_2d(verbose=False):
    # ...
    n_elements = (8, 4)
    p = (3, 3)                                      # spline degree
    n = [_n+_p-1 for (_n,_p) in zip(n_elements, p)] # number of control points
    # ...

    T = [make_open_knots(_p, _n) for (_n,_p) in zip(n, p)]

    M0, M1, M2 = build_matrices_2d_H1(p, n, T)

    # ...
    interpolate = Interpolation2D(p, n, T)

    interpolate_H1 = lambda f: interpolate('H1', f)
    interpolate_Hcurl = lambda f: interpolate('Hcurl', f)
    interpolate_L2 = lambda f: interpolate('L2', f)
    # ...

    # ... H1
    f = lambda x,y: x*(1.-x)*y*(1.-y)
    F = interpolate_H1(f)
    # ...

    # ... Hcurl
    g0 = lambda x,y: (1.-2.*x)*y*(1.-y)
    g1 = lambda x,y: x*(1.-x)*(1.-2.*y)
#    g0 = lambda x,y: np.ones_like(x)
#    g1 = lambda x,y: np.zeros_like(x)
    g  = lambda x,y: [g0(x,y), g1(x,y)]

    G = interpolate_Hcurl(g)
    # ...

    # ... L2
    h = lambda x,y: x*(1.-x)*y*(1.-y)
    H = interpolate_L2(h)
    # ...

    # ...
    def to_array_H1(X):
        return X.flatten()

    def to_array_Hcurl(X):
        X0 = X[0] ; X1 = X[1]
        x0 = X0.flatten()
        x1 = X1.flatten()
        return np.concatenate([x0, x1])

    def to_array_L2(X):
        return X.flatten()
    # ...


    # ... compute error on H1 for interpolation
    f_0 = solve(M0, to_array_H1(F))
    tck = tck_H1(p, n, T, f_0)
    fh_0 = lambda x,y: bisplev(x, y, tck)
    diff = lambda x,y: (f(x,y) - fh_0(x,y))**2

    integrate = Integral2D(p, n, T)
    err_0 = np.sqrt(np.sum(integrate(diff)))
    # ...

    # ... compute error on L2
    h_2 = solve(M2, to_array_L2(H))
    S = scaling_matrix(p, n, T, kind='L2')
    h_2  = S.dot(h_2)
    x = np.zeros(h_2.size)
    for i in range(0, h_2.size):
        x[i] = h_2[0,i]
    h_2 = x
    tck = tck_L2(p, n, T, h_2)
    hh_0 = lambda x,y: bisplev(x, y, tck)
    diff = lambda x,y: (h(x,y) - hh_0(x,y))**2

    integrate = Integral2D(p, n, T)
    err_2 = np.sqrt(np.sum(integrate(diff)))
    # ...

    # ... compute error on Hcurl
    g_1 = solve(M1, to_array_Hcurl(G))
    S = scaling_matrix(p, n, T, kind='Hcurl')
    g_1  = S.dot(g_1)
    tck0, tck1 = tck_Hcurl(p, n, T, g_1)
    gh_0 = lambda x,y: bisplev(x, y, tck0)
    gh_1 = lambda x,y: bisplev(x, y, tck1)
    diff = lambda x,y: (g(x,y)[0] - gh_0(x,y))**2 + (g(x,y)[1] - gh_1(x,y))**2

    integrate = Integral2D(p, n, T)
    err_1 = np.sqrt(np.sum(integrate(diff)))
    # ...

#    # ...
#    import matplotlib.pyplot as plt
#
#    u = np.linspace(0., 1., 200)
#    v = np.linspace(0., 1., 400)
#
#    z = gh_0(u, v)
#    plt.contourf(u, v, z.transpose())
#    plt.colorbar()
#    plt.savefig('gh_0.png')
#    plt.clf()
#
#    U,V = np.meshgrid(u, v)
#    plt.contourf(u, v, g0(U, V))
#    plt.colorbar()
#    plt.savefig('g0.png')
#    # ...

    # ...
    if verbose:
        print ('==== testing projection in 2d ====')
        print ('> M0.shape  := {}'.format(M0.shape))
        print ('> M1.shape  := {}'.format(M1.shape))
        print ('> M2.shape  := {}'.format(M2.shape))
        print()
        print ('> F.shape  := {}'.format(F.shape))
        print ('> G.shapes := {0} | {1}'.format(G[0].shape, G[1].shape))
        print ('> H.shape  := {}'.format(H.shape))
        print()
        print ('> l2 error of `f_0` = {}'.format(err_0))
        print ('> l2 error of `g_1` = {}'.format(err_1))
        print ('> l2 error of `h_2` = {}'.format(err_2))

    # ...





####################################################################################
if __name__ == '__main__':

#    test_projectors_1d(verbose=True)
#    print('')
    test_projectors_2d(verbose=True)
