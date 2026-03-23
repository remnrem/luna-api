"""Result and metadata utilities.

This module provides helper functions for:

- discovering Luna command domains/tables/variables
- reading command files
- converting raw return tuples into DataFrames
- subsetting/concatenating result collections
"""

from .resources import lp_version
import lunapi.lunapi0 as _luna

import pandas as pd
try:
    from IPython.display import display as ICD
except ImportError:
    ICD = None


def fetch_doms():
   """Return all top-level Luna command domains.

   Returns
   -------
   list of str
       Domain names (e.g. ``'PSG'``, ``'Spectral'``).
   """
   return _luna.fetch_doms( True )


def fetch_cmds( dom ):
   """Return all Luna commands belonging to a domain.

   Parameters
   ----------
   dom : str
       Domain name as returned by :func:`fetch_doms`.

   Returns
   -------
   list of str
       Command names within *dom*.
   """
   return _luna.fetch_cmds( dom, True )


def fetch_params( cmd ):
   """Return the accepted parameters for a Luna command.

   Parameters
   ----------
   cmd : str
       Luna command name (e.g. ``'PSD'``).

   Returns
   -------
   list of str
       Parameter names accepted by *cmd*.
   """
   return _luna.fetch_params( cmd, True )


def fetch_tbls( cmd ):
   """Return the output tables produced by a Luna command.

   Parameters
   ----------
   cmd : str
       Luna command name.

   Returns
   -------
   list of str
       Strata labels for the tables produced by *cmd*
       (e.g. ``['BL', 'CH', 'CH_F']``).
   """
   return _luna.fetch_tbls( cmd, True )


def fetch_vars( cmd, tbl ):
   """Return the output variables in a specific command/table.

   Parameters
   ----------
   cmd : str
       Luna command name.
   tbl : str
       Strata label identifying the table within *cmd*.

   Returns
   -------
   list of str
       Variable names present in the specified output table.
   """
   return _luna.fetch_vars( cmd, tbl, True )


def fetch_desc_dom( dom ):
   """Return a short description for a Luna command domain.

   Parameters
   ----------
   dom : str
       Domain name.

   Returns
   -------
   str
       Human-readable description of *dom*.
   """
   return _luna.fetch_desc_dom( dom  )


def fetch_desc_cmd( cmd ):
   """Return a short description for a Luna command.

   Parameters
   ----------
   cmd : str
       Luna command name.

   Returns
   -------
   str
       Human-readable description of *cmd*.
   """
   return _luna.fetch_desc_cmd( cmd )


def fetch_desc_param( cmd , param ):
   """Return a short description for a Luna command parameter.

   Parameters
   ----------
   cmd : str
       Luna command name.
   param : str
       Parameter name within *cmd*.

   Returns
   -------
   str
       Human-readable description of *param*.
   """
   return _luna.fetch_desc_param( cmd, param )


def fetch_desc_tbl( cmd , tbl ):
   """Return a short description for a Luna command output table.

   Parameters
   ----------
   cmd : str
       Luna command name.
   tbl : str
       Strata label identifying the table within *cmd*.

   Returns
   -------
   str
       Human-readable description of the table.
   """
   return _luna.fetch_desc_tbl( cmd, tbl )


def fetch_desc_var( cmd, tbl, var ):
   """Return a short description for a variable in a Luna output table.

   Parameters
   ----------
   cmd : str
       Luna command name.
   tbl : str
       Strata label identifying the table.
   var : str
       Variable name within the table.

   Returns
   -------
   str
       Human-readable description of *var*.
   """
   return _luna.fetch_desc_var( cmd, tbl, var )


# --------------------------------------------------------------------------------


def cmdfile( f ):
   """Read and return the full text of a Luna command script file.

   Preserves original line structure so that ``IF``/``FI`` blocks are parsed
   as separate Luna commands (some workflows rely on multiline control
   statements).

   Parameters
   ----------
   f : str or path-like
       Path to a ``.txt`` (or ``.luna``) script file.

   Returns
   -------
   str
       Raw text content of the file.
   """

   # Preserve original line structure so IF/FI blocks are parsed as separate
   # Luna commands (some workflows rely on multiline control statements).
   with open(f, "r", encoding="utf-8") as fh:
      return fh.read()


# --------------------------------------------------------------------------------


def strata( ts ):
   """List all (command, stratum) pairs present in a result collection.

   Parameters
   ----------
   ts : dict
       Nested dict returned by :func:`tables`, mapping command names to
       stratum-keyed dicts of raw result tuples.

   Returns
   -------
   list of tuple
       List of ``(command, stratum)`` string pairs.
   """
   r = [ ]
   for cmd in ts:
      for stratum in ts[cmd].keys():
         r.append( ( cmd , stratum ) )
   return r

# --------------------------------------------------------------------------------


def table( ts, cmd , strata = 'BL' ):
   """Extract a single output table as a DataFrame from a raw result dict.

   Parameters
   ----------
   ts : dict
       Raw result dict as returned by the C++ backend (before conversion).
   cmd : str
       Luna command name.
   strata : str, optional
       Stratum label.  Default ``'BL'``.

   Returns
   -------
   pandas.DataFrame
       Result table with properly named columns.
   """
   r = ts[cmd][strata]
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------


def tables( ts ):
   """Convert a raw backend result dict to a collection of DataFrames.

   Parameters
   ----------
   ts : dict
       Raw result dict returned by the C++ backend, mapping command names
       to stratum-keyed dicts of ``(column_names, data_matrix)`` tuples.

   Returns
   -------
   dict
       Mapping of ``"COMMAND: STRATA"`` string keys to
       ``pandas.DataFrame`` values.
   """
   r = { }
   for cmd in ts.keys():
      strata = ts[cmd].keys()
      for stratum in strata:
         r[ cmd + ": " + stratum ] = _table2df( ts[cmd][stratum] )
   return r

# --------------------------------------------------------------------------------


def _table2df( r ):
   """Convert a single raw ``(column_names, data_matrix)`` tuple to a DataFrame."""
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------


def show( dfs ):
   """Display a result collection in the notebook with bold headings.

   Parameters
   ----------
   dfs : dict
       Mapping of label strings to ``pandas.DataFrame`` objects, as
       returned by :func:`tables`.

   Returns
   -------
   None
       Output is rendered via ``IPython.display``.
   """
   for title , df in dfs.items():
      print( _color.BOLD + _color.DARKCYAN + title + _color.END )
      if ICD is not None:
         ICD(df)


# --------------------------------------------------------------------------------


def subset( df , ids = None , qry = None , vars = None  ):
   """Subset rows and/or columns of a Luna result DataFrame.

   Parameters
   ----------
   df : pandas.DataFrame
       Result table to filter, typically containing an ``'ID'`` column.
   ids : str or list of str, optional
       Keep only rows whose ``'ID'`` value is in *ids*.
   qry : str, optional
       A :meth:`pandas.DataFrame.query` expression for row filtering
       (e.g. ``'F > 10 and F < 20'``).
   vars : str or list of str, optional
       Column names to retain.  ``'ID'`` is always kept as the first
       column.

   Returns
   -------
   pandas.DataFrame
       Filtered DataFrame.
   """

   # subset rows (ID)
   if ids is not None:
      if type(ids) is not list: ids = [ ids ]
      df = df[ df[ 'ID' ].isin( ids ) ]

   # subset rows (factors/levels)
   if type(qry) is str:
      df = df.query( qry )

   # subset cols (vars)
   if vars is not None:
      if type(vars) is not list: vars = [ vars ]
      vars.insert( 0, 'ID' )
      df = df[ vars ]

   return df

# --------------------------------------------------------------------------------


def concat( dfs , tlab , vars = None , add_index = None , ignore_index = True ):
   """Concatenate matching tables from a dict of result sets.

   Assumes *dfs* is a ``dict`` where each value is itself a result dict
   (as returned by :func:`tables`), and extracts the table labelled *tlab*
   from each, then concatenates them.  Commonly used to stack results from
   multiple individuals or conditions that were processed separately.

   Parameters
   ----------
   dfs : dict
       Outer dict mapping arbitrary keys (e.g. individual IDs) to inner
       result dicts (``"CMD: STRATA"`` → ``DataFrame``).
   tlab : str
       Result key (``"CMD: STRATA"``) identifying which table to extract
       from each inner dict.
   vars : str or list of str, optional
       Columns to keep from each extracted table.  If omitted, all
       columns are included.
   add_index : str, optional
       If provided, a column with this name is added to each table and
       populated with the corresponding outer key from *dfs*.
   ignore_index : bool, optional
       Passed directly to :func:`pandas.concat`.  Default ``True``.

   Returns
   -------
   pandas.DataFrame
       Concatenated table.
   """

   # assume dict[k]['cmd: faclvl']->table
   # and we want to concatenate over 'k'
   # assume 'k' will be tracked in the tables (e.g. via TAG)

   if add_index is not None:
      for k in dfs.keys():
         dfs[k][tlab][ [add_index] ] = k

   if vars is not None:
      if type(vars) is not list: vars = [ vars ]
      dfs = pd.concat( [ dfs[ k ][ tlab ][ vars ] for k in dfs.keys() ] , ignore_index = ignore_index )
   if vars is None:
      dfs = pd.concat( [ dfs[ k ][ tlab ] for k in dfs.keys() ] , ignore_index = ignore_index )

   return dfs


# --------------------------------------------------------------------------------
#
# Helpers
#
# --------------------------------------------------------------------------------


def version():
   """Return version information for both the Python package and the C++ backend.

   Returns
   -------
   dict
       ``{'lunapi': '<version>', 'luna': '<version>'}``
   """
   return { "lunapi": lp_version , "luna": _luna.version() }


class _color:
   """ANSI color escape codes used for lightweight terminal formatting."""
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'


__all__ = [
    "fetch_doms",
    "fetch_cmds",
    "fetch_params",
    "fetch_tbls",
    "fetch_vars",
    "fetch_desc_dom",
    "fetch_desc_cmd",
    "fetch_desc_param",
    "fetch_desc_tbl",
    "fetch_desc_var",
    "cmdfile",
    "strata",
    "table",
    "tables",
    "_table2df",
    "show",
    "subset",
    "concat",
    "version",
    "_color",
]
