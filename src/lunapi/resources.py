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

import os
import warnings

from . import __version__


class resources:
   """Default resource locations used by high-level convenience wrappers.

   Notes
   -----
   These paths match the ``remnrem/luna`` Docker image, which unpacks the
   luna-resources bundle (https://github.com/remnrem/luna-resources) to
   ``/build/luna-resources/``.  Elsewhere, point them at a downloaded copy,
   e.g. ``lp.resources.POPS_PATH = '/path/to/luna-resources/pops/'``.
   """
   POPS_PATH = '/build/luna-resources/pops/'
   POPS_LIB = 's2a'
   MODEL_PATH = '/build/luna-resources/predict/'

lp_version = __version__


def _pops_coda_args( path, lib, coda ):
   """POPS options for CODA, as used by ``inst.pops()`` and ``proj.pops()``.

   CODA needs the model ``<path>/<lib>.coda30.mod``.  If it is missing, warn
   and return no options, so POPS runs without CODA.
   """
   if not coda: return ''
   cfile = os.path.join( path, lib + '.coda30.mod' )
   if not os.path.isfile( cfile ):
      warnings.warn( f'POPS: no CODA model for lib={lib} ({cfile}); '
                     'running without CODA (set coda=False to silence this)',
                     stacklevel = 3 )
      return ''
   return 'coda'


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
