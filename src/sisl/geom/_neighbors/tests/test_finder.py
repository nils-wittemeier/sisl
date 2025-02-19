from functools import partial

import numpy as np
import pytest

from sisl import Geometry
from sisl.geom import NeighborFinder

pytestmark = [pytest.mark.neighbor]


tr_fixture = partial(pytest.fixture, scope="module", params=[True, False])


def request_param(request):
    return request.param


sphere_overlap = tr_fixture()(request_param)
multiR = tr_fixture()(request_param)
self_interaction = tr_fixture()(request_param)
post_setup = tr_fixture()(request_param)
pbc = tr_fixture()(request_param)


@pytest.fixture(scope="module")
def neighfinder(sphere_overlap, multiR):
    geom = Geometry([[0, 0, 0], [1.2, 0, 0], [9, 0, 0]], lattice=[10, 10, 7])

    R = np.array([1.1, 1.5, 1.2]) if multiR else 1.5

    neighfinder = NeighborFinder(geom, R=R, overlap=sphere_overlap)

    neighfinder.assert_consistency()

    return neighfinder


@pytest.fixture(scope="module")
def expected_neighs(sphere_overlap, multiR, self_interaction, pbc):
    first_at_neighs = []
    if not (multiR and not sphere_overlap):
        first_at_neighs.append([0, 1, 0, 0, 0])
    if self_interaction:
        first_at_neighs.append([0, 0, 0, 0, 0])
    if pbc:
        first_at_neighs.append([0, 2, -1, 0, 0])

    second_at_neighs = [[1, 0, 0, 0, 0]]
    if self_interaction:
        second_at_neighs.insert(0, [1, 1, 0, 0, 0])
    if pbc and sphere_overlap:
        second_at_neighs.append([1, 2, -1, 0, 0])

    third_at_neighs = []
    if self_interaction:
        third_at_neighs.append([2, 2, 0, 0, 0])
    if pbc:
        if sphere_overlap:
            third_at_neighs.append([2, 1, 1, 0, 0])
        third_at_neighs.append([2, 0, 1, 0, 0])

    return (
        np.array(first_at_neighs),
        np.array(second_at_neighs),
        np.array(third_at_neighs),
    )


def test_neighfinder_setup(sphere_overlap, multiR, post_setup):
    geom = Geometry([[0, 0, 0], [1, 0, 0]], lattice=[10, 10, 7])

    R = np.array([0.9, 1.5]) if multiR else 1.5

    if post_setup:
        # We are going to create a data structure with the wrong parameters,
        # and then update it.
        finder = NeighborFinder(geom, R=R - 0.7, overlap=not sphere_overlap)
        finder.setup(R=R, overlap=sphere_overlap)
    else:
        # Initialize finder with the right parameters.
        finder = NeighborFinder(geom, R=R, overlap=sphere_overlap)

    # Check that R is properly set when its a scalar and an array.
    if multiR:
        assert isinstance(finder.R, np.ndarray)
        assert np.all(finder.R == R)
    else:
        assert finder.R.ndim == 0
        assert finder.R == R

    # Assert that we have stored a copy of the geometry
    assert isinstance(finder.geometry, Geometry)
    assert finder.geometry == geom
    assert finder.geometry is not geom

    # Check that the total number of bins is correct. If sphere_overlap is
    # True, bins are much bigger.
    nbins = (1, 1, 1) if sphere_overlap else (3, 3, 2)
    assert finder.nbins == nbins

    total_bins = 1 if sphere_overlap else 18
    assert finder.total_nbins == total_bins

    # Assert that the data structure is generated.
    for k in ("_list", "_counts", "_heads"):
        assert hasattr(finder, k), k
        assert isinstance(finder._list, np.ndarray), k

    finder.assert_consistency()

    # Check that all bins are empty except one, which contains the two atoms.
    assert (finder._counts == 0).sum() == finder.total_nbins - 1
    assert finder._counts.sum() == 2


def test_neighbor_pairs(neighfinder, self_interaction, pbc, expected_neighs):
    neighs = neighfinder.find_neighbors(
        as_pairs=True, self_interaction=self_interaction, pbc=pbc
    )

    assert isinstance(neighs, np.ndarray)

    first_at_neighs, second_at_neighs, third_at_neighs = expected_neighs

    n_neighs = len(first_at_neighs) + len(second_at_neighs) + len(third_at_neighs)

    assert neighs.shape == (n_neighs, 5)

    assert np.all(neighs == [*first_at_neighs, *second_at_neighs, *third_at_neighs])


def test_neighbors_lists(neighfinder, self_interaction, pbc, expected_neighs):
    neighs = neighfinder.find_neighbors(
        as_pairs=False, self_interaction=self_interaction, pbc=pbc
    )

    assert isinstance(neighs, list)
    assert len(neighs) == 3

    assert all(isinstance(n, np.ndarray) for n in neighs)

    first_at_neighs, second_at_neighs, third_at_neighs = expected_neighs

    # Check shapes
    for i, i_at_neighs in enumerate(
        [first_at_neighs, second_at_neighs, third_at_neighs]
    ):
        assert neighs[i].shape == (
            len(i_at_neighs),
            4,
        ), f"Wrong shape for neighbors of atom {i}"

    # Check values
    for i, i_at_neighs in enumerate(
        [first_at_neighs, second_at_neighs, third_at_neighs]
    ):
        if len(neighs[i]) == 0:
            continue

        assert np.all(
            neighs[i] == i_at_neighs[:, 1:]
        ), f"Wrong values for neighbors of atom {i}"


def test_all_unique_pairs(neighfinder, self_interaction, pbc, expected_neighs):
    if neighfinder.R.ndim == 1 and not neighfinder._overlap:
        with pytest.raises(ValueError):
            neighfinder.find_all_unique_pairs(
                self_interaction=self_interaction, pbc=pbc
            )
        return

    neighs = neighfinder.find_all_unique_pairs(
        self_interaction=self_interaction, pbc=pbc
    )

    first_at_neighs, second_at_neighs, third_at_neighs = expected_neighs

    all_expected_neighs = np.array(
        [*first_at_neighs, *second_at_neighs, *third_at_neighs]
    )

    unique_neighs = []
    for neigh_pair in all_expected_neighs:
        if not np.all(neigh_pair[2:] == 0):
            unique_neighs.append(neigh_pair)
        else:
            for others in unique_neighs:
                if np.all(others == [neigh_pair[1], neigh_pair[0], *neigh_pair[2:]]):
                    break
            else:
                unique_neighs.append(neigh_pair)

    assert neighs.shape == (len(unique_neighs), 5)


def test_close(neighfinder, pbc):
    neighs = neighfinder.find_close([0.3, 0, 0], as_pairs=True, pbc=pbc)

    expected_neighs = [[0, 1, 0, 0, 0], [0, 0, 0, 0, 0]]
    if pbc and neighfinder.R.ndim == 0:
        expected_neighs.append([0, 2, -1, 0, 0])

    assert neighs.shape == (len(expected_neighs), 5)
    assert np.all(neighs == expected_neighs)


def test_no_neighbors(pbc):
    """Test the case where there are no neighbors, to see that it doesn't crash."""

    geom = Geometry([[0, 0, 0]])

    finder = NeighborFinder(geom, R=1.5)

    neighs = finder.find_neighbors(as_pairs=True, pbc=pbc)

    assert isinstance(neighs, np.ndarray)
    assert neighs.shape == (0, 5)

    neighs = finder.find_neighbors(as_pairs=False, pbc=pbc)

    assert isinstance(neighs, list)
    assert len(neighs) == 1

    assert isinstance(neighs[0], np.ndarray)
    assert neighs[0].shape == (0, 4)

    neighs = finder.find_all_unique_pairs(pbc=pbc)

    assert isinstance(neighs, np.ndarray)
    assert neighs.shape == (0, 5)


def test_R_too_big(pbc):
    """Test the case when R is so big that it needs a bigger bin
    than the unit cell."""

    geom = Geometry([[0, 0, 0], [1, 0, 0]], lattice=[2, 10, 10])

    neighfinder = NeighborFinder(geom, R=1.5)

    neighs = neighfinder.find_all_unique_pairs(pbc=pbc)

    expected_neighs = [[0, 1, 0, 0, 0]]
    if pbc:
        expected_neighs.append([0, 1, -1, 0, 0])
        expected_neighs.append([1, 0, 1, 0, 0])

    assert neighs.shape == (len(expected_neighs), 5)
    assert np.all(neighs == expected_neighs)

    neighfinder = NeighborFinder(geom, R=[0.6, 2.2], overlap=True)

    neighs = neighfinder.find_close([[0.5, 0, 0]], as_pairs=True, pbc=pbc)

    expected_neighs = [[0, 1, 0, 0, 0], [0, 0, 0, 0, 0]]
    if pbc:
        expected_neighs.insert(0, [0, 1, -1, 0, 0])

    assert neighs.shape == (len(expected_neighs), 5)
    assert np.all(neighs == expected_neighs)


def test_bin_sizes():
    geom = Geometry([[0, 0, 0], [1, 0, 0]], lattice=[2, 10, 10])

    # We should have fewer bins along the first lattice vector
    n1 = NeighborFinder(geom, R=1.5, bin_size=2)
    n2 = NeighborFinder(geom, R=1.5, bin_size=4)

    assert n1.total_nbins > n2.total_nbins
    # When the bin is bigger than the unit cell, this situation
    # occurs
    assert n1.nbins[0] == n2.nbins[0]
    assert n1.nbins[1] > n2.nbins[1]
    assert n1.nbins[2] > n2.nbins[2]

    # We should have the same number of bins the 2nd and 3rd lattice vectors
    n3 = NeighborFinder(geom, R=1.5, bin_size=2)
    n4 = NeighborFinder(geom, R=1.5, bin_size=(2, 4, 4))

    assert n3.nbins[0] == n4.nbins[0]
    assert n3.nbins[1] > n4.nbins[1]
    assert n3.nbins[2] > n4.nbins[2]
