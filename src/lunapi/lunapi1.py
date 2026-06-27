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

"""High-level Luna API facade.

This module re-exports the split API modules while preserving legacy
``lunapi.lunapi1`` import behavior.

Submodules are intentionally wildcard-imported so users can continue to use
the historical single-module API surface during migration.
"""

from .project import *
from .instance import *
from .results import *
from .parallel import *
from .segsrv import *
from .viz import *
from .moonbeam import *
from .resources import *
from .gpa import gpa_prep, gpa_manifest, gpa_run, gpa_dump, gpa_get_xy, gpa_get_xy_partial, gpa_clear_cache
from .destrat import *
from .edf_utils import *
