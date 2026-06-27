#    --------------------------------------------------------------------
#
#    This file is part of Luna.
#
#    LUNA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Luna is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Luna. If not, see <http://www.gnu.org/licenses/>.
#
#    Please see LICENSE.txt for more details.
#
#    --------------------------------------------------------------------

"""Python API for the Luna C/C++ signal processing engine.

The package exposes a high-level, Pythonic API surface backed by the
compiled ``lunapi0`` extension and convenience wrappers in ``lunapi1``.

Modules
-------
lunapi.lunapi0
    Low-level pybind11 bindings to core Luna engine types.
lunapi.lunapi1
    High-level convenience API for projects, instances, tables, and
    visualization helpers.
"""

__version__ = "1.6.5"

from lunapi.lunapi1 import *
