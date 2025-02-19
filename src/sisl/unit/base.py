# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import pyparsing as pp

from sisl._internal import set_module

__all__ = ["unit_group", "unit_convert", "unit_default", "units"]


# We do not import anything as it depends on the package.
# Here we only add the conversions according to the
# standard. Other programs may use their units as they
# please with non-standard conversion factors.
# This is the CODATA-2018 units

unit_table = {
    "mass": {"DEFAULT": "amu", "kg": 1.0, "g": 0.001, "amu": 1.6605390666e-27},
    "length": {
        "DEFAULT": "Ang",
        "m": 1.0,
        "cm": 0.01,
        "nm": 1e-09,
        "Ang": 1e-10,
        "pm": 1e-12,
        "fm": 1e-15,
        "Bohr": 5.29177210903e-11,
    },
    "time": {
        "DEFAULT": "fs",
        "s": 1.0,
        "ns": 1e-09,
        "ps": 1e-12,
        "fs": 1e-15,
        "min": 60.0,
        "hour": 3600.0,
        "day": 86400.0,
        "atu": 2.4188843265857e-17,
    },
    "energy": {
        "DEFAULT": "eV",
        "J": 1.0,
        "kJ": 1.0e3,
        "erg": 1e-07,
        "K": 1.380649e-23,
        "eV": 1.602176634e-19,
        "meV": 1.6021766339999998e-22,
        "Ha": 4.3597447222071e-18,
        "mHa": 4.3597447222071e-21,
        "Ry": 2.1798723611035e-18,
        "mRy": 2.1798723611035e-21,
    },
    "force": {
        "DEFAULT": "eV/Ang",
        "N": 1.0,
        "eV/Ang": 1.6021766339999998e-09,
        "Ry/Bohr": 4.1193617491269446e-08,
        "Ha/Bohr": 8.238723498254079e-08,
    },
}


@set_module("sisl.unit")
def unit_group(unit, tbl=unit_table):
    """The group of units that `unit` belong to

    Parameters
    ----------
    unit : str
      unit, e.g. kg, Ang, eV etc. returns the type of unit it is.
    tbl : dict, optional
        dictionary of units (default to the global table)

    Examples
    --------
    >>> unit_group("kg")
    "mass"
    >>> unit_group("eV")
    "energy"
    """
    for k in tbl:
        if unit in tbl[k]:
            return k
    raise ValueError(f"The unit " "{unit!s}" " could not be located in the table.")


@set_module("sisl.unit")
def unit_default(group, tbl=unit_table):
    """The default unit of the unit group `group`.

    Parameters
    ----------
    group : str
       look-up in the table for the default unit.
    tbl : dict, optional
        dictionary of units (default to the global table)

    Examples
    --------
    >>> unit_default("energy")
    "eV"
    """
    for k in tbl:
        if group == k:
            return tbl[k]["DEFAULT"]

    raise ValueError("The unit-group does not exist!")


@set_module("sisl.unit")
def unit_convert(fr, to, opts=None, tbl=unit_table):
    """Factor that takes `fr` to the units of `to`

    Parameters
    ----------
    fr : str
        starting unit
    to : str
        ending unit
    opts : dict, optional
        controls whether the unit conversion is in powers or fractional units
    tbl : dict, optional
        dictionary of units (default to the global table)

    Examples
    --------
    >>> unit_convert("kg","g")
    1000.0
    >>> unit_convert("eV","J")
    1.60217733e-19
    """
    if opts is None:
        opts = dict()

    # In the case that the conversion to is None, we should do nothing.
    frU = "FromNotFound"
    frV = None
    toU = "ToNotFound"
    toV = None

    # Check that the unit types live in the same
    # space
    # TODO this currently does not handle if powers are taken into
    # consideration.

    for k in tbl:
        if fr in tbl[k]:
            frU = k
            frV = tbl[k][fr]
        if to in tbl[k]:
            toU = k
            toV = tbl[k][to]
    if frU != toU:
        raise ValueError(
            f"The unit conversion is not from the same group: {frU} to {toU}"
        )

    # Calculate conversion factor
    val = frV / toV
    for opt in ("^", "power", "p"):
        if opt in opts:
            val = val ** opts[opt]
    for opt in ("*", "factor", "fac"):
        if opt in opts:
            val = val * opts[opt]
    for opt in ("/", "divide", "div"):
        if opt in opts:
            val = val / opts[opt]

    return val


# From here and on we implement the generalized parser required for
# doing complex unit-specifications (i.e. eV/Ang etc.)


@set_module("sisl.unit")
class UnitParser:
    """Object for converting between units for a set of unit-tables.

    Parameters
    ----------
    unit_table : dict
       a table with the units parsable by the class
    """

    __slots__ = ("_table", "_p_left", "_left", "_p_right", "_right")

    def __init__(self, table):
        self._table = table

        def value(unit):
            tbl = self._table
            for k in tbl:
                if unit in tbl[k]:
                    return tbl[k][unit]
            raise ValueError(f"The unit conversion did not contain unit {unit}!")

        def group(unit):
            tbl = self._table
            for k in tbl:
                if unit in tbl[k]:
                    return k
            raise ValueError(
                f"The unit " "{unit!s}" " could not be located in the table."
            )

        def default(group):
            tbl = self._table
            k = tbl.get(group, None)
            if k is None:
                raise ValueError(f"The unit-group {group} does not exist!")
            return k["DEFAULT"]

        self._left = []
        self._p_left = self.create_parser(value, default, group, self._left)
        self._right = []
        self._p_right = self.create_parser(value, default, group, self._right)

    @staticmethod
    def create_parser(value, default, group, group_table=None):
        """Routine to internally create a parser with specified unit_convert, unit_default and unit_group routines"""

        # Any length of characters will be used as a word.
        if group_table is None:

            def _value(t):
                return value(t[0])

            def _float(t):
                return float(t[0])

        else:

            def _value(t):
                group_table.append(group(t[0]))
                return value(t[0])

            def _float(t):
                f = float(t[0])
                group_table.append(f)  # append nothing
                return f

        # The unit extractor
        unit = pp.Word(pp.alphas).setParseAction(_value)

        integer = pp.Word(pp.nums)
        plusorminus = pp.oneOf("+ -")
        point = pp.Literal(".")
        e = pp.CaselessLiteral("E")
        sign_integer = pp.Combine(pp.Optional(plusorminus) + integer)
        exponent = pp.Combine(e + sign_integer)
        sign_integer = pp.Combine(pp.Optional(plusorminus) + integer)
        exponent = pp.Combine(e + sign_integer)
        number = pp.Or(
            [
                pp.Combine(point + integer + pp.Optional(exponent)),  # .[0-9][E+-[0-9]]
                pp.Combine(
                    integer
                    + pp.Optional(point + pp.Optional(integer))
                    + pp.Optional(exponent)
                ),
            ]  # [0-9].[0-9][E+-[0-9]]
        ).setParseAction(_float)

        # def _print_toks(name, op):
        #    """ May be used in pow_op.setParseAction(_print_toks("pow", "^")) to debug """
        #    def T(t):
        #        print("{}: {}".format(name, t))
        #        return op
        #    return T

        # def _fix_toks(op):
        #    """ May be used in pow_op.setParseAction(_print_toks("pow", "^")) to debug """
        #    def T(t):
        #        return op
        #    return T

        pow_op = pp.oneOf("^ **").setParseAction(lambda t: "^")
        mul_op = pp.Literal("*")
        div_op = pp.Literal("/")
        # Since any space in units are regarded as multiplication this will catch
        # those instances.
        base_op = pp.Empty()

        if group_table is None:

            def pow_action(toks):
                return toks[0][0] ** toks[0][2]

            def mul_action(toks):
                return toks[0][0] * toks[0][2]

            def div_action(toks):
                return toks[0][0] / toks[0][2]

            def base_action(toks):
                return toks[0][0] * toks[0][1]

        else:

            def pow_action(toks):
                # Fix table of units
                group = "{}^{}".format(group_table[-2], group_table.pop())
                group_table[-1] = group
                # print("^", toks[0], group_table)
                return toks[0][0] ** toks[0][2]

            def mul_action(toks):
                if isinstance(group_table[-2], float):
                    group_table.pop(-2)
                if isinstance(group_table[-1], float):
                    group_table.pop()
                # print("*", toks[0], group_table)
                return toks[0][0] * toks[0][2]

            def div_action(toks):
                if isinstance(group_table[-2], float):
                    group_table.pop(-2)
                if isinstance(group_table[-1], float):
                    group_table.pop()
                else:
                    group_table[-1] = "/{}".format(group_table[-1])
                # print("/", toks[0])
                return toks[0][0] / toks[0][2]

            def base_action(toks):
                if isinstance(group_table[-2], float):
                    group_table.pop(-2)
                if isinstance(group_table[-1], float):
                    group_table.pop()
                return toks[0][0] * toks[0][1]

        # We should parse numbers first
        parser = pp.infixNotation(
            number | unit,
            [
                (pow_op, 2, pp.opAssoc.RIGHT, pow_action),
                (mul_op, 2, pp.opAssoc.LEFT, mul_action),
                (div_op, 2, pp.opAssoc.LEFT, div_action),
                (base_op, 2, pp.opAssoc.LEFT, base_action),
            ],
        )

        return parser

    @staticmethod
    def same_group(A, B):
        """Return true if A and B have the same groups"""
        A.sort()
        B.sort()
        if len(A) != len(B):
            return False
        return all(a == b for a, b in zip(A, B))

    def _convert(self, A, B):
        """Internal routine used to convert unit `A` to unit `B`"""
        conv_A = self._p_left.parseString(A)[0]
        conv_B = self._p_right.parseString(B)[0]
        if not self.same_group(self._left, self._right):
            left = list(self._left)
            right = list(self._right)
            self._left.clear()
            self._right.clear()
            raise ValueError(
                f"The unit conversion is not from the same group: {left} to {right}!"
            )
        self._left.clear()
        self._right.clear()
        return conv_A / conv_B

    def convert(self, *units):
        """Conversion factors between units

        If 1 unit is passed a conversion to the default  will be returned.
        If 2 parameters are passed then a single float will be returned that converts from
        ``units[0]`` to ``units[1]``.
        If 3 or more parameters are passed then a tuple of floats will be returned where
        ``tuple[0]`` is the conversion from ``units[0]`` to ``units[1]``,
        ``tuple[1]`` is the conversion from ``units[1]`` to ``units[2]`` and so on.

        Parameters
        ----------
        *units : list of string
           units to be converted

        Examples
        --------
        >>> up = UnitParser(unit_table)
        >>> up.convert("kg", "g")
        1000.0
        >>> up.convert("kg", "g", "amu")
        (1000.0, 6.022140762081123e+23)

        Raises
        ------
        UnitSislError
            if the units are not commensurate
        """
        if len(units) == 2:
            # basic unit conversion
            return self._convert(units[0], units[1])

        elif len(units) == 1:
            # to default
            conv = self._p_left.parseString(units[0])[0]
            self._left.clear()
            return conv

        return tuple(self._convert(A, B) for A, B in zip(units[:-1], units[1:]))

    def __call__(self, *units):
        return self.convert(*units)


# Create base sisl unit conversion object
units = UnitParser(unit_table)
