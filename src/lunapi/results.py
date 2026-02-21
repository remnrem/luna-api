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
from IPython.core import display as ICD


def fetch_doms():
   """Fetch all command domains
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_doms( True )


def fetch_cmds( dom ):
   """Fetch all commands
      
      Parameters
      ----------
      dom : object\n        Input argument `dom`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_cmds( dom, True )


def fetch_params( cmd ):
   """Fetch all command parameters
      
      Parameters
      ----------
      cmd : object\n        Input argument `cmd`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_params( cmd, True )


def fetch_tbls( cmd ):
   """Fetch all command tables
      
      Parameters
      ----------
      cmd : object\n        Input argument `cmd`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_tbls( cmd, True )


def fetch_vars( cmd, tbl ):
   """Fetch all command/table variables
      
      Parameters
      ----------
      cmd : object\n        Input argument `cmd`.
      tbl : object\n        Input argument `tbl`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_vars( cmd, tbl, True )


def fetch_desc_dom( dom ):
   """Description for a domain
      
      Parameters
      ----------
      dom : object\n        Input argument `dom`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_desc_dom( dom  )


def fetch_desc_cmd( cmd ):
   """Description for a command
      
      Parameters
      ----------
      cmd : object\n        Input argument `cmd`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_desc_cmd( cmd )


def fetch_desc_param( cmd , param ):
   """Description for a command/parameter
      
      Parameters
      ----------
      cmd : object\n        Input argument `cmd`.
      param : object\n        Input argument `param`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_desc_param( cmd, param )


def fetch_desc_tbl( cmd , tbl ):
   """Description for a command/table
      
      Parameters
      ----------
      cmd : object\n        Input argument `cmd`.
      tbl : object\n        Input argument `tbl`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_desc_tbl( cmd, tbl )


def fetch_desc_var( cmd, tbl, var ):
   """Fetch all command/table variable
      
      Parameters
      ----------
      cmd : object\n        Input argument `cmd`.
      tbl : object\n        Input argument `tbl`.
      var : object\n        Input argument `var`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   return _luna.fetch_desc_var( cmd, tbl, var )


# --------------------------------------------------------------------------------


def cmdfile( f ):
   """load and parse a Luna command script from a file
      
      Parameters
      ----------
      f : object\n        Input argument `f`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """

   return _luna.cmdfile( f )


# --------------------------------------------------------------------------------


def strata( ts ):
   """Utility function to format tables
      
      Parameters
      ----------
      ts : object\n        Input argument `ts`.
      
      Returns
      -------
      object
              See function description for the concrete return type.
   """
   r = [ ] 
   for cmd in ts:
      strata = ts[cmd].keys()
      for stratum in strata:
         r.append( ( cmd , strata ) )
      return r

   t = pd.DataFrame( self.edf.strata() )
   t.columns = ["Command","Strata"]
   return t

# --------------------------------------------------------------------------------


def table( ts, cmd , strata = 'BL' ):
   """Utility function to format tables
      
      Parameters
      ----------
      ts : object\n        Input argument `ts`.
      cmd : object\n        Input argument `cmd`.
      strata : object\n        Input argument `strata`.
      
      Returns
      -------
      object
              See function description for the concrete return type.
   """
   r = ts[cmd][strata]
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------


def tables( ts ):
   """Utility function to format tables
      
      Parameters
      ----------
      ts : object\n        Input argument `ts`.
      
      Returns
      -------
      object
              See function description for the concrete return type.
   """
   r = { }
   for cmd in ts.keys():
      strata = ts[cmd].keys()
      for stratum in strata:
         r[ cmd + ": " + stratum ] = _table2df( ts[cmd][stratum] ) 
   return r

# --------------------------------------------------------------------------------


def _table2df( r ):
   """Utility function to format tables"""
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------


def show( dfs ):
   """Utility function to format tables
      
      Parameters
      ----------
      dfs : object\n        Input argument `dfs`.
      
      Returns
      -------
      None
              This function displays output and returns no value.
   """
   for title , df in dfs.items():
      print( _color.BOLD + _color.DARKCYAN + title + _color.END )
      ICD.display(df)


# --------------------------------------------------------------------------------


def subset( df , ids = None , qry = None , vars = None  ):
   """Utility function to subset table rows/columns
      
      Parameters
      ----------
      df : object\n        Input argument `df`.
      ids : object\n        Input argument `ids`.
      qry : object\n        Input argument `qry`.
      vars : object\n        Input argument `vars`.
      
      Returns
      -------
      object
              See function description for the concrete return type.
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
   """Utility function to extract and concatenate tables
      
      Parameters
      ----------
      dfs : object\n        Input argument `dfs`.
      tlab : object\n        Input argument `tlab`.
      vars : object\n        Input argument `vars`.
      add_index : object\n        Input argument `add_index`.
      ignore_index : object\n        Input argument `ignore_index`.
      
      Returns
      -------
      object
              See function description for the concrete return type.
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
   """Return version of lunapi & luna
      
      Returns
      -------
      object
              See function description for the concrete return type.
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
