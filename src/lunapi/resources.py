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
