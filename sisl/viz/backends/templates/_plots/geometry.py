from collections.abc import Iterable
import numpy as np

from ..backend import Backend

from ....plots import GeometryPlot


class GeometryBackend(Backend):
    """Draws the geometry as provided by `GeometryPlot`.

    Checks the dimensionality of the geometry and then calls:
        - 1D case: `self.draw_1D`
        - 2D case: `self.draw_2D`
        - 3D case: `self.draw_3D`

    These 3 functions contain generic implementations, although some parts may need
    a method to be implemented. Here are more details of each case:

    1D workflow (`self.draw_1D`):
        `self._draw_atoms_2D_scatter()`, generic implementation that calls `self.draw_scatter`

    2D workflow (`self.draw_2D`):
        if (bonds need to be drawn):
            Calls `self._draw_bonds_2D()` which may call:
            if (all bonds are same size and same color):
                `self._draw_bonds_2D_single_color_size`, generic implementation that calls `self.draw_line`
            else:
                `self._draw_bonds_2D_multi_color_size`, generic implementation that calls `self.draw_scatter`
        Then call `self._draw_atoms_2D_scatter()` to draw the atoms, generic implementation that calls `self.draw_scatter`
        And finally draw the cell:
            if (cell to be drawn as axes):
                `self._draw_cell_2D_axes()`:
                for axis in axes:
                    `self._draw_axis_2D()`, generic implementation that calls `self.draw_line`
            elif (cell to be drawn as a box):
                `self._draw_cell_2D_box()`, generic implementation that calls `self.draw_line`

    3D workflow (`self.draw_3D`):
        if (bonds need to be drawn):
            if (all bonds are same size and same color):
                `self._bonds_3D_scatter()`:
                Manages all arguments and then calls `self._draw_bonds_3D`, generic implementation that uses `self.draw_line3D`.
            else:
                for bond in bonds:
                    `self._draw_single_bond_3D()`, generic implementation that uses `self.draw_line3D`.
        if (atoms need to be drawn):
            for atom in atoms:
                `self._draw_single_atom_3D`, NOT IMPLEMENTED (optional)
        And finally draw the cell:
            if (cell to be drawn as axes):
                `self._draw_cell_3D_axes()`, generic implementation that calls `self.draw_line3D` for each axis.
            elif (cell to be drawn as a box):
                `self._draw_cell_3D_box()`, generic implementation that calls `self.draw_line3D`
    """

    def draw(self, backend_info):
        drawing_func = getattr(self, f"draw_{backend_info['ndim']}D")

        drawing_func(backend_info)

    def draw_1D(self, backend_info, **kwargs):
        # Add the atoms trace
        self._draw_atoms_2D_scatter(**backend_info["atoms_props"])

    def draw_2D(self, backend_info, **kwargs):
        geometry = backend_info["geometry"]
        xaxis = backend_info["xaxis"]
        yaxis = backend_info["yaxis"]
        bonds_props = backend_info["bonds_props"]

        # If there are bonds to draw, draw them
        if len(bonds_props) > 0:
            bonds_kwargs = {}
            for k in bonds_props[0]:
                if k == "xys":
                    new_k = k
                else:
                    new_k = f"bonds_{k}"
                bonds_kwargs[new_k] = [x[k] for x in bonds_props]

            self._draw_bonds_2D(**bonds_kwargs, points_per_bond=backend_info["points_per_bond"])

        # Add the atoms trace
        self._draw_atoms_2D_scatter(**backend_info["atoms_props"])

        # And finally draw the unit cell
        show_cell = backend_info["show_cell"]
        cell = geometry.cell
        if show_cell == "axes":
            self._draw_cell_2D_axes(geometry=geometry, cell=cell, xaxis=xaxis, yaxis=yaxis)
        elif show_cell == "box":
            self._draw_cell_2D_box(
                geometry=geometry, cell=cell,
                xaxis=xaxis, yaxis=yaxis
                )

    def _draw_atoms_2D_scatter(self, xy, color="gray", size=10, name='atoms', marker_colorscale=None, **kwargs):
        self.draw_scatter(xy[0], xy[1], name=name, marker={'size': size, 'color': color, 'colorscale': marker_colorscale}, **kwargs)

    def _draw_bonds_2D(self, xys, points_per_bond=5, force_bonds_as_points=False,
        bonds_color='#cccccc', bonds_size=3, bonds_name=None, name="bonds", **kwargs):
        """
        Cheaper than _bond_trace2D because it draws all bonds in a single trace.
        It is also more flexible, since it allows providing bond colors as floats that all
        relate to the same colorscale.
        However, the bonds are represented as dots between the two atoms (if you use enough
        points per bond it almost looks like a line).
        """
        # Check if we need to build the markers_properties from atoms_* arguments
        if isinstance(bonds_color, Iterable) and not isinstance(bonds_color, str):
            bonds_color = np.repeat(bonds_color, points_per_bond)
            single_color = False
        else:
            single_color = True

        if isinstance(bonds_size, Iterable):
            bonds_size = np.repeat(bonds_size, points_per_bond)
            single_size = False
        else:
            single_size = True

        x = []
        y = []
        text = []
        if single_color and single_size and not force_bonds_as_points:
            # Then we can display this trace as lines! :)
            for i, ((x1, y1), (x2, y2)) in enumerate(xys):

                x = [*x, x1, x2, None]
                y = [*y, y1, y2, None]

                if bonds_name:
                    text = np.repeat(bonds_name, 3)

            draw_bonds_func = self._draw_bonds_2D_single_color_size

        else:
            # Otherwise we will need to draw points in between atoms
            # representing the bonds
            for i, ((x1, y1), (x2, y2)) in enumerate(xys):

                x = [*x, *np.linspace(x1, x2, points_per_bond)]
                y = [*y, *np.linspace(y1, y2, points_per_bond)]

            draw_bonds_func = self._draw_bonds_2D_multi_color_size
            if bonds_name:
                text = np.repeat(bonds_name, points_per_bond)

        draw_bonds_func(x, y, bonds_color, bonds_size, name=name, text=text if len(text) != 0 else None, **kwargs)

    def _draw_bonds_2D_single_color_size(self, x, y, color, size, name, text, **kwargs):
        self.draw_line(x, y, name=name, line={"color": color, "width": size}, text=text, **kwargs)

    def _draw_bonds_2D_multi_color_size(self, x, y, color, size, name, text, coloraxis="coloraxis", colorscale=None, **kwargs):
        self.draw_scatter(x, y, name=name, marker={"color": color, "size": size, "coloraxis": coloraxis, "colorscale": colorscale}, text=text, **kwargs)

    def _draw_cell_2D_axes(self, geometry, cell, xaxis="x", yaxis="y"):
        cell_xy = GeometryPlot._projected_2Dcoords(geometry, xyz=cell, xaxis=xaxis, yaxis=yaxis)
        origo_xy = GeometryPlot._projected_2Dcoords(geometry, xyz=geometry.origin, xaxis=xaxis, yaxis=yaxis)

        for i, vec in enumerate(cell_xy):
            x = np.array([0, vec[0]]) + origo_xy[0]
            y = np.array([0, vec[1]]) + origo_xy[1]
            name = f'Axis {i}'
            self._draw_axis_2D(x, y, name=name)

    def _draw_axis_2D(self, x, y, name):
        self.draw_line(x, y, name=name)

    def _draw_cell_2D_box(self, cell, geometry, xaxis="x", yaxis="y", color=None, **kwargs):

        cell_corners = GeometryPlot._get_cell_corners(cell) + geometry.origin
        x, y = GeometryPlot._projected_2Dcoords(geometry, xyz=cell_corners, xaxis=xaxis, yaxis=yaxis).T

        self.draw_line(x, y, line={"color": color}, name="Unit cell", **kwargs)

    def draw_3D(self, backend_info):

        geometry = backend_info["geometry"]
        bonds_props = backend_info["bonds_props"]

        # If there are bonds to draw, draw them
        if len(bonds_props) > 0:
            # Unless we have different bond sizes, we want to plot all bonds in the same trace
            different_bond_sizes = False
            if "size" in bonds_props[0]:
                first_size = bonds_props[0].get("size")
                for bond_prop in bonds_props:
                    if bond_prop.get("size") != first_size:
                        different_bond_sizes = True
                        break

            if different_bond_sizes:
                for bond_props in backend_info["bonds_props"]:
                    self._draw_single_bond_3D(**bond_props)
            else:
                bonds_kwargs = {}
                for k in bonds_props[0]:
                    if k == "r":
                        v = bonds_props[0][k]
                    else:
                        v = [x[k] for x in bonds_props]
                    bonds_kwargs[f"bonds_{k}"] = v

                self._bonds_3D_scatter(geometry, backend_info["bonds"], **bonds_kwargs)

        # Now draw the atoms
        for atom_props in backend_info["atoms_props"]:
            self._draw_single_atom_3D(**atom_props)

        # And finally draw the unit cell
        show_cell = backend_info["show_cell"]
        cell = geometry.cell
        if show_cell == "axes":
            self._draw_cell_3D_axes(cell=cell, geometry=geometry)
        elif show_cell == "box":
            self._draw_cell_3D_box(cell=cell, geometry=geometry)

    def _bonds_3D_scatter(self, geometry, bonds, bonds_xyz1, bonds_xyz2, bonds_r=10, bonds_color='gray', bonds_name=None,
        atoms=False, atoms_color="blue", atoms_size=None, name=None, coloraxis='coloraxis', **kwargs):
        """This method is capable of plotting all the geometry in one 3d trace."""
        bonds_labels=bonds_name
        # If only bonds are in this trace, we will name it "bonds".
        if not name:
            name = 'Bonds and atoms' if atoms else 'Bonds'

        # Check if we need to build the markers_properties from atoms_* arguments
        if atoms and isinstance(atoms_color, Iterable) and not isinstance(atoms_color, str):
            build_marker_color = True
            atoms_color = np.array(atoms_color)
            marker_color = []
        else:
            build_marker_color = False
            marker_color = atoms_color

        if atoms and isinstance(atoms_size, Iterable):
            build_marker_size = True
            atoms_size = np.array(atoms_size)
            marker_size = []
        else:
            build_marker_size = False
            marker_size = atoms_size

        # Bond color
        if isinstance(bonds_color, Iterable) and not isinstance(bonds_color, str):
            build_line_color = True
            bonds_color = np.array(bonds_color)
            line_color = []
        else:
            build_line_color = False
            line_color = bonds_color

        x = []; y = []; z = []

        for i, bond in enumerate(bonds):

            x = [*x, bonds_xyz1[i][0], bonds_xyz2[i][0], None]
            y = [*y, bonds_xyz1[i][1], bonds_xyz2[i][1], None]
            z = [*z, bonds_xyz1[i][2], bonds_xyz2[i][2], None]

            if build_marker_color:
                marker_color = [*marker_color, *atoms_color[bond], "white"]
            if build_marker_size:
                marker_size = [*marker_size, *atoms_size[bond], 0]
            if build_line_color:
                line_color = [*line_color, bonds_color[i], bonds_color[i], 0]

        x_labels, y_labels, z_labels = None, None, None
        if bonds_labels:
            x_labels, y_labels, z_labels = np.array([geometry[bond].mean(axis=0) for bond in bonds]).T

        self._draw_bonds_3D(
            x, y, z, name=name,
            line={'width': bonds_r, 'color': line_color, 'coloraxis': coloraxis},
            marker={'size': marker_size, 'color': marker_color},
            show_markers=atoms,
            bonds_labels=bonds_labels, x_labels=x_labels, y_labels=y_labels, z_labels=z_labels,
            **kwargs
        )

    def _draw_bonds_3D(self, x, y, z, name=None, line={}, marker={}, show_markers=False, bonds_labels=None, x_labels=None, y_labels=None, z_labels=None, **kwargs):
        """Draws all bonds in a single line in 3D

        This method should be overwritten to implement:
            - show_markers=True -> Draw markers as well
            - Write bonds_labels
        """
        self.draw_line3D(x, y, z, line=line, marker=marker, name=name, **kwargs)

    def _draw_single_atom_3D(self, xyz, size, color="gray", name=None, group=None, showlegend=False, vertices=15, **kwargs):
        raise NotImplementedError(f"{self.__class__.__name__} does not implement a method to draw a single atom in 3D")

    def _draw_single_bond_3D(self, xyz1, xyz2, size=0.3, color="#ccc", name=None, group=None, showlegend=False, line_kwargs={}, **kwargs):
        x, y, z = np.array([xyz1, xyz2]).T

        self.draw_line3D(x, y, z, line={'width': size, 'color': color, **line_kwargs}, name=name, **kwargs)

    def _draw_cell_3D_axes(self, cell, geometry, **kwargs):

        for i, vec in enumerate(cell):
            self.draw_line3D(
                x=np.array([0, vec[0]]) + geometry.origin[0],
                y=np.array([0, vec[1]]) + geometry.origin[1],
                z=np.array([0, vec[2]]) + geometry.origin[2],
                name=f'Axis {i}',
                **kwargs
            )

    def _draw_cell_3D_box(self, cell, geometry, color=None, width=2, **kwargs):
        x, y, z = (GeometryPlot._get_cell_corners(cell) + geometry.origin).T

        self.draw_line3D(x, y, z, line={'color': color, 'width': width}, name="Unit cell", **kwargs)

GeometryPlot.backends.register_template(GeometryBackend)