# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from typing import Optional

import numpy as np

from sisl import Atom, Geometry, Lattice
from sisl._internal import set_module
from sisl.typing import AtomsLike

from ._common import geometry_define_nsc

__all__ = ["honeycomb", "graphene", "honeycomb_flake", "graphene_flake", "triangulene"]


@set_module("sisl.geom")
def honeycomb(bond: float, atoms: AtomsLike, orthogonal: bool = False) -> Geometry:
    """Honeycomb lattice with 2 or 4 atoms per unit-cell, latter orthogonal cell

    This enables creating BN lattices with ease, or graphene lattices.

    Parameters
    ----------
    bond :
        bond length between atoms (*not* lattice constant)
    atoms :
        the atom (or atoms) that the honeycomb lattice consists of
    orthogonal :
        if True returns an orthogonal lattice

    See Also
    --------
    graphene: the equivalent of this, but with default of Carbon atoms
    bilayer: create bilayer honeycomb lattices
    """
    sq3h = 3.0**0.5 * 0.5
    if orthogonal:
        lattice = Lattice(
            np.array(
                [[3.0, 0.0, 0.0], [0.0, 2 * sq3h, 0.0], [0.0, 0.0, 10.0]], np.float64
            )
            * bond
        )
        g = Geometry(
            np.array(
                [[0.0, 0.0, 0.0], [0.5, sq3h, 0.0], [1.5, sq3h, 0.0], [2.0, 0.0, 0.0]],
                np.float64,
            )
            * bond,
            atoms,
            lattice=lattice,
        )
    else:
        lattice = Lattice(
            np.array(
                [[1.5, -sq3h, 0.0], [1.5, sq3h, 0.0], [0.0, 0.0, 10.0]], np.float64
            )
            * bond
        )
        g = Geometry(
            np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], np.float64) * bond,
            atoms,
            lattice=lattice,
        )
    geometry_define_nsc(g, [True, True, False])
    return g


@set_module("sisl.geom")
def graphene(
    bond: float = 1.42, atoms: AtomsLike = None, orthogonal: bool = False
) -> Geometry:
    """Graphene lattice with 2 or 4 atoms per unit-cell, latter orthogonal cell

    Parameters
    ----------
    bond :
        bond length between atoms (*not* lattice constant)
    atoms : Atom, optional
        the atom (or atoms) that the honeycomb lattice consists of.
        Default to Carbon atom.
    orthogonal :
        if True returns an orthogonal lattice

    See Also
    --------
    honeycomb: the equivalent of this, but with non-default atoms
    bilayer: create bilayer honeycomb lattices
    """
    if atoms is None:
        atoms = Atom(Z=6, R=bond * 1.01)
    return honeycomb(bond, atoms, orthogonal)


@set_module("sisl.geom")
def honeycomb_flake(
    shells: int, bond: float, atoms: AtomsLike, vacuum: float = 20.0
) -> Geometry:
    """Hexagonal flake of a honeycomb lattice, with zig-zag edges.

    Parameters
    ----------
    shells:
        Number of shells in the flake. 0 means a single hexagon, and subsequent
        shells add hexagon units surrounding the previous shell.
    bond:
        bond length between atoms (*not* lattice constant)
    atoms:
        the atom (or atoms) that the honeycomb lattice consists of
    vacuum:
        Amount of vacuum to add to the cell on all directions
    """

    # Function that generates one of the six triangular portions of the
    # hexagonal flake. The rest of the portions are obtained by rotating
    # this one by 60, 120, 180, 240 and 300 degrees.
    def _minimal_op(shells):
        # The function is based on the horizontal lines of the hexagon,
        # which are made of a pair of atoms.
        # For each shell, we first need to complete the incomplete horizontal
        # lines of the previous shell, and then branch them up and down to create
        # the next horizontal lines.

        # Displacement from the end of one horizontal pair to the beggining of the next
        branch_displ_x = bond * 0.5  # cos(60) = 0.5
        branch_displ_y = bond * 3**0.5 / 2  # sin(60) = sqrt(3)/2

        # Iterate over shells. We also keep track of the atom types, in case
        # we have two different atoms in the honeycomb lattice.
        op = np.array([[bond, 0, 0]])
        types = np.array([0])
        for shell in range(shells):
            n_new_branches = 2 + shell
            prev_edge = branch_displ_y * (shell)

            sat = np.zeros((shell + 1, 3))
            sat[:, 0] = op[-1, 0] + bond
            sat[:, 1] = np.linspace(-prev_edge, prev_edge, shell + 1)

            edge = branch_displ_y * (shell + 1)

            branches = np.zeros((n_new_branches, 3))
            branches[:, 0] = sat[0, 0] + branch_displ_x
            branches[:, 1] = np.linspace(-edge, edge, n_new_branches)

            op = np.concatenate([op, sat, branches])
            types = np.concatenate(
                [types, np.full(len(sat), 1), np.full(len(branches), 0)]
            )

        return op, types

    # Get the coordinates of 1/6 of the hexagon for the requested number of shells.
    op, types = _minimal_op(shells)

    single_atom_type = isinstance(atoms, (str, Atom)) or len(atoms) == 1

    # Create a geometry from the coordinates.
    ats = atoms if single_atom_type else np.asarray(atoms)[types]
    geom = Geometry(op, atoms=ats)

    # The second portion of the hexagon is obtained by rotating the first one by 60 degrees.
    # However, if there are two different atoms in the honeycomb lattice, we need to reverse the types.
    next_triangle = (
        geom if single_atom_type else Geometry(op, atoms=np.asarray(atoms)[types - 1])
    )
    geom += next_triangle.rotate(60, [0, 0, 1])

    # Then just rotate the two triangles by 120 and 240 degrees to get the full hexagon.
    geom += geom.rotate(120, [0, 0, 1]) + geom.rotate(240, [0, 0, 1])

    # Set the cell according to the requested vacuum
    max_x = np.max(geom.xyz[:, 0])
    geom.cell[0, 0] = max_x * 2 + vacuum
    geom.cell[1, 1] = max_x * 2 + vacuum
    geom.cell[2, 2] = 20.0

    # Center the flake
    geom = geom.translate(geom.center(what="cell"))

    # Set boundary conditions
    geometry_define_nsc(geom, [False, False, False])

    return geom


@set_module("sisl.geom")
def graphene_flake(
    shells: int, bond: float = 1.42, atoms: AtomsLike = None, vacuum: float = 20.0
) -> Geometry:
    """Hexagonal flake of graphene, with zig-zag edges.

    Parameters
    ----------
    shells:
        Number of shells in the flake. 0 means a single hexagon, and subsequent
        shells add hexagon units surrounding the previous shell.
    bond:
        bond length between atoms (*not* lattice constant)
    atoms:
        the atom (or atoms) that the honeycomb lattice consists of.
        Default to Carbon atom.
    vacuum:
        Amount of vacuum to add to the cell on all directions

    See Also
    --------
    honeycomb_flake: the equivalent of this, but with non-default atoms.
    """
    if atoms is None:
        atoms = Atom(Z=6, R=bond * 1.01)
    return honeycomb_flake(shells, bond, atoms, vacuum)


@set_module("sisl.geom")
def triangulene(
    n: int, bond: float = 1.42, atoms: Optional[AtomsLike] = None, vacuum: float = 20.0
) -> Geometry:
    """Construction of an [n]-triangulene geometry

    Parameters
    ----------
    n :
       size of the triangulene
    bond :
       bond length between atoms (*not* lattice constant)
    atoms :
        the atom (or atoms) that the honeycomb lattice consists of.
        Default to Carbon atom.
    vacuum:
        Amount of vacuum to add to the cell on all directions
    """
    if atoms is None:
        atoms = Atom(Z=6, R=bond * 1.01)
    geom = graphene(bond=bond, atoms=atoms) * (n + 1, n + 1, 1)
    idx = np.where(geom.xyz[:, 0] <= geom.cell[0, 0] + 0.01)[0]
    geom = geom.sub(idx[1:])

    # Set the cell according to the requested vacuum
    size = geom.xyz.max(axis=0) - geom.xyz.min(axis=0)
    geom.cell[:] = np.diag(size + vacuum)

    # Center the molecule in cell
    geom = geom.move(geom.center(what="cell") - geom.center())

    # Set boundary conditions
    geometry_define_nsc(geom, [False, False, False])

    return geom
