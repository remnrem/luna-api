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

"""Static resource defaults and version helpers.

Exports Docker-oriented model/resource defaults and package/backend version
introspection helpers.
"""

from . import __version__


class resources:
   """Default resource locations used by high-level convenience wrappers.

   Notes
   -----
   These paths are primarily intended for containerized environments where
   POPS/model resources are mounted in known locations.
   """
   POPS_PATH = '/build/nsrr/common/resources/pops/'
   POPS_LIB = 's2'
   MODEL_PATH = '/build/luna-models/'

lp_version = __version__


def version():
   """Return version metadata for both the Python package and the C++ backend.

   Returns
   -------
   dict
       ``{'lunapi': '<version>', 'luna': '<version>'}``
   """
   from .results import version as _version
   return _version()

__all__ = ["resources", "lp_version", "version"]
