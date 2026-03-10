"""Project-level Luna API.

This module exports :class:`proj`, the primary entry point for creating and
managing a Luna project/session and sample-list lifecycle.
"""

import lunapi.lunapi0 as _luna

import pandas as pd
from IPython.display import display

from .resources import resources, lp_version
from .results import tables, cmdfile


class proj:
   """Manages a Luna engine session and an associated sample list.

   Only one engine instance is created per Python session (singleton pattern).
   Use :meth:`proj` to obtain a handle to that engine, load a sample list,
   configure project-level variables, run Luna commands across all individuals
   in the list, and retrieve the resulting output tables.

   Examples
   --------
   >>> p = proj()
   >>> p.sample_list('my-study.lst')
   >>> results = p.proc('PSD spectrum dB sig=EEG')
   >>> df = p.table('PSD', 'CH_F')
   """

   # single static engine class
   eng = _luna.inaugurate()

   def __init__(self, verbose = True ):
      self.n = 0
      if verbose: print( "initiated lunapi",lp_version,proj.eng ,"\n" )
      self.silence( False )
      self.eng = _luna.inaugurate()

   def retire(self):
      """Shut down the Luna engine and release its resources.

      Returns
      -------
      object
          Status value returned by the C++ backend.
      """
      return _luna.retire()

   def build( self, args ):
      """Build an internal sample list by scanning one or more folders.

      Equivalent to the ``--build`` option of the Luna command-line tool.
      Searches *args* for EDF and annotation files and constructs a
      three-column sample list (ID, EDF path, annotation path).

      See https://zzz.bwh.harvard.edu/luna/ref/helpers/#-build for details.

      After a successful call, :meth:`sample_list` (with no arguments) will
      return the discovered records.

      Parameters
      ----------
      args : str or list of str
          One or more folder paths to scan.  Optional ``--build`` flags may
          also be included as list elements.

      Returns
      -------
      object
          Status value returned by the C++ backend.
      """

      # first clear any existing sample list
      proj.eng.clear()

      # then try to build a new one
      if type( args ) is not list: args = [ args ]
      return proj.eng.build_sample_list( args )


   def sample_list(self, filename = None , path = None , df = True ):
      """Read a sample list from *filename*, or return the current one.

      When *filename* is given the named file is loaded as the project sample
      list.  When *filename* is omitted the function returns the list that is
      already held in memory.

      Parameters
      ----------
      filename : str, optional
          Path to a Luna sample-list file.  If omitted, returns the
          current in-memory sample list.
      path : str, optional
          If provided, sets the ``path`` project variable before reading so
          that relative EDF paths in *filename* are resolved correctly.
      df : bool, optional
          When returning the in-memory list, wrap it in a
          ``pandas.DataFrame`` with columns ``['ID', 'EDF', 'Annotations']``
          rather than returning the raw list.  Default is ``True``.

      Returns
      -------
      pandas.DataFrame or list
          When *filename* is ``None``: the current sample list as a DataFrame
          (if *df* is ``True``) or as a list of strings otherwise.
          When *filename* is given: ``None`` (the count is printed to stdout).
      """

      # return sample list
      if filename is None:
         sl = proj.eng.get_sample_list()
         if df is True:
            sl = pd.DataFrame( sl )
            sl.columns = [ 'ID' , 'EDF', 'Annotations' ]
            sl.index += 1
         return sl

      # set path?
      if path is not None:
         print( "setting path to " , path )
         self.var( 'path' , path )

      # read sample list from file, after clearing anything present
      proj.eng.clear()
      self.n = proj.eng.read_sample_list( filename )
      print( "read",self.n,"individuals from" , filename )


   #------------------------------------------------------------------------

   def nobs(self):
      """Return the number of individuals in the current sample list.

      Returns
      -------
      int
          Number of records in the in-memory sample list.
      """

      return proj.eng.nobs()

   #------------------------------------------------------------------------

   def validate( self ):
      """Validate every record in the current sample list.

      Checks that each EDF file listed in the sample list exists and is
      readable.  Equivalent to the ``--validate`` option of the Luna
      command-line tool.

      See https://zzz.bwh.harvard.edu/luna/ref/helpers/#-validate for details.

      Returns
      -------
      pandas.DataFrame
          DataFrame with columns ``['ID', 'Filename', 'Valid']``, one row
          per sample-list entry.
      """

      tbl = proj.eng.validate_sample_list()
      tbl = pd.DataFrame( tbl )
      tbl.columns = [ 'ID' , 'Filename', 'Valid' ]
      tbl.index += 1
      return tbl


   #------------------------------------------------------------------------

   def reset(self):
      """Clear the Luna problem flag so that further commands can run.

      Luna sets an internal error flag when a command fails.  Call this
      method to clear that flag and allow subsequent evaluation to proceed.

      Returns
      -------
      None
      """
      proj.eng.reset()

   def reinit(self):
      """Re-initialize the project, clearing all results and state.

      Returns
      -------
      None
      """
      proj.eng.reinit()

   #------------------------------------------------------------------------

   def inst( self, n ):
      """Return an :class:`~lunapi.instance.inst` for one sample-list record.

      Parameters
      ----------
      n : int or str
          When an ``int``, a **1-based** index into the sample list.
          When a ``str``, the individual ID as it appears in the sample list.

      Returns
      -------
      lunapi.instance.inst
          Instance object wrapping the requested EDF record.
      """

      # check bounds
      if type(n) is int:
         # use 1-based counts as inputs
         n = n - 1
         if n < 0 or n >= self.nobs():
            print( "index out-of-bounds given sample list of " + str(self.nobs()) + " records" )
            return

      # if the arg is a str that matches a sample-list
      if type(n) is str:
         sn = self.get_n(n)
         if type(sn) is int: n = sn

      # Lazy import avoids project<->instance import cycle at module import time.
      from .instance import inst as _inst

      # return based on n (from sample-list) or string/empty (new instance)
      return _inst(proj.eng.inst( n ))


   #------------------------------------------------------------------------

   def empty_inst( self, id, nr, rs, startdate = '01.01.00', starttime = '00.00.00' ):
      """Create a new :class:`~lunapi.instance.inst` backed by a blank EDF.

      Constructs an in-memory EDF of fixed size with no signals.  Signals can
      be added afterwards with :meth:`~lunapi.instance.inst.insert_signal`.

      Parameters
      ----------
      id : str
          Individual identifier to assign to the new record.
      nr : int
          Number of EDF records (data blocks).
      rs : int
          Duration of each EDF record in seconds.
      startdate : str, optional
          EDF start date in ``DD.MM.YY`` format.  Default ``'01.01.00'``.
      starttime : str, optional
          EDF start time in ``HH.MM.SS`` format.  Default ``'00.00.00'``.

      Returns
      -------
      lunapi.instance.inst
          Instance backed by the newly created blank EDF.
      """

      # check inputs
      nr = int( nr )
      rs = int( rs )
      if nr < 0:
         print( "expecting nr (number of records) to be a positive integer" )
         return
      if rs < 0:
         print( "expecting rs (record duration, secs) to be a positive integer" )
         return

      # Lazy import avoids project<->instance import cycle at module import time.
      from .instance import inst as _inst

      # return instance of fixed size
      return _inst(proj.eng.empty_inst(id, nr, rs, startdate, starttime ))

   #------------------------------------------------------------------------

   def clear(self):
      """Remove all records from the current in-memory sample list.

      Returns
      -------
      None
      """
      proj.eng.clear()


   #------------------------------------------------------------------------

   def silence(self, b = True , verbose = False ):
      """Suppress or restore Luna's console/log output.

      Parameters
      ----------
      b : bool
          ``True`` to silence output; ``False`` to re-enable it.
      verbose : bool, optional
          If ``True``, print a confirmation message.  Default ``False``.

      Returns
      -------
      None
      """
      if verbose:
         if b: print( 'silencing console outputs' )
         else: print( 'enabling console outputs' )
      proj.eng.silence(b)

   #------------------------------------------------------------------------

   def is_silenced(self, b = True ):
      """Return whether Luna's log output is currently silenced.

      Returns
      -------
      bool
          ``True`` if output is silenced, ``False`` otherwise.
      """
      return proj.eng.is_silenced()


   #------------------------------------------------------------------------

   def flush(self):
      """Flush the internal output buffer.

      Returns
      -------
      None
      """
      proj.eng.flush()

   # --------------------------------------------------------------------------------

   def include( self, f ):
      """Load options and variables from a Luna parameter file (``@``-file).

      Parameters
      ----------
      f : str
          Path to a Luna parameter file.  Lines of the form ``key=value``
          set project variables; lines starting with ``%`` are comments.

      Returns
      -------
      object
          Status value returned by the C++ backend.
      """
      return proj.eng.include( f )


   #------------------------------------------------------------------------

   def aliases( self ):
      """Display a table of signal and annotation aliases.

      Prints (and returns ``None``) a DataFrame showing all alias mappings
      currently registered with the engine.

      Returns
      -------
      None
          Output is displayed via ``IPython.display``.
      """
      t = pd.DataFrame( proj.eng.aliases() )
      t.index = t.index + 1
      if len( t ) == 0: return t
      t.columns = ["Type", "Preferred", "Case-insensitive, sanitized alias" ]
      with pd.option_context('display.max_rows', None,):
         display(t)

   #------------------------------------------------------------------------

   def var(self , key=None , value=None):
      """Get or set one or more project-level variables.

      Thin alias for :meth:`vars`.

      Parameters
      ----------
      key : str, list of str, or dict, optional
          Variable name(s) to get, or a ``{name: value}`` dict to set.
      value : str, optional
          Value to assign when *key* is a single variable name.

      Returns
      -------
      str, dict, or None
          The variable value (or dict of values) when getting;
          ``None`` when setting.
      """
      return self.vars( key, value )

   #------------------------------------------------------------------------

   def vars(self , key=None , value=None):
      """Get or set one or more project-level variables.

      When called with no arguments, returns all currently set variables.
      When *key* is a string and *value* is omitted, returns that variable's
      value.  When *key* is a list, returns a dict of values.  When both
      *key* and *value* are provided (or *key* is a dict), sets the
      variable(s).

      Parameters
      ----------
      key : str, list of str, or dict, optional
          Variable name(s) to get, or a ``{name: value}`` dict to set.
      value : str, optional
          Value to assign when *key* is a single variable name string.

      Returns
      -------
      str, dict, or None
          The variable value (or dict of values) when getting;
          ``None`` when setting.
      """

      # return all vars?
      if key is None:
         return proj.eng.get_all_opts()

      # return one or more vars?
      if value is None:

         # return 1?
         if type( key ) is str:
            return proj.eng.get_opt( key )

         # return some?
         if type( key ) is list:
            return proj.eng.get_opts( key )

      # set from a dict
      if isinstance(key, dict):
         for k, v in key.items():
            self.vars(k,v)
         return

      # set a single pair
      proj.eng.opt( key, str( value ) )


   #------------------------------------------------------------------------
#   def clear_var(self,key):
#      """Clear project-level option(s)/variable(s)"""
#      self.clear_vars(key)

   #------------------------------------------------------------------------

   def clear_vars(self,key = None ):
      """Clear one, several, or all project-level variables.

      Parameters
      ----------
      key : str or list of str, optional
          Name(s) of the variable(s) to remove.  If omitted, **all**
          project variables are cleared (including the ``sig`` channel
          selection list).

      Returns
      -------
      None
      """

      # clear all
      if key is None:
         proj.eng.clear_all_opts()
         # and a spectial case: the sig list
         self.vars( 'sig', '' )
         return

      # clear some/one
      if type(key) is not list: key = [ key ]
      proj.eng.clear_opts(key)


   #------------------------------------------------------------------------

   def clear_ivars(self):
      """Clear individual-level variables for every individual in the sample list.

      Returns
      -------
      None
      """
      proj.eng.clear_ivars()

   #------------------------------------------------------------------------

   def get_n(self,id):
      """Return the 0-based internal index for a given individual ID.

      Parameters
      ----------
      id : str
          Individual identifier as it appears in the sample list.

      Returns
      -------
      int
          0-based index of *id* within the sample list, or ``None`` if
          not found.
      """
      return proj.eng.get_n(id)

   #------------------------------------------------------------------------

   def get_id(self,n):
      """Return the individual ID for a given (0-based) sample-list index.

      Parameters
      ----------
      n : int
          0-based position in the sample list.

      Returns
      -------
      str
          Individual identifier at position *n*.
      """
      return proj.eng.get_id(n)

   #------------------------------------------------------------------------

   def get_edf(self,x):
      """Return the EDF file path for an individual.

      Parameters
      ----------
      x : int or str
          Either a 0-based integer index or the individual's string ID.

      Returns
      -------
      str
          Absolute (or sample-list-relative) path to the EDF file.
      """
      if ( isinstance(x,int) ):
         return proj.eng.get_edf(x)
      else:
         return proj.eng.get_edf(proj.eng.get_n(x))


   #------------------------------------------------------------------------

   def get_annots(self,x):
      """Return the annotation file path(s) for an individual.

      Parameters
      ----------
      x : int or str
          Either a 0-based integer index or the individual's string ID.

      Returns
      -------
      str
          Annotation file path(s) as stored in the sample list
          (comma-separated if multiple files are listed).
      """
      if ( isinstance(x,int) ):
         return proj.eng.get_annot(x)
      else:
         return proj.eng.get_annot(proj.eng.get_n(x))


   #------------------------------------------------------------------------

   def import_db(self,f,s=None):
      """Import a Luna *destrat*-style output database into the result store.

      Parameters
      ----------
      f : str
          Path to a Luna output database file (``*.db``).
      s : str or list of str, optional
          If provided, import only the individuals whose IDs match *s*.

      Returns
      -------
      object
          Status value returned by the C++ backend.
      """
      if s is None:
         return proj.eng.import_db(f)
      else:
         return proj.eng.import_db_subset(f,s)

   #------------------------------------------------------------------------

   def desc( self ):
      """Display a summary table of all sample-list individuals.

      Runs the Luna ``DESC`` command silently across the sample list and
      displays a DataFrame with columns:
      ``['ID', 'Gapped', 'Date', 'Start(hms)', 'Stop(hms)', 'Dur(hms)',
      'Dur(s)', '# sigs', '# annots', 'Signals']``.

      Returns
      -------
      None
          Output is displayed via ``IPython.display``.
      """
      silence_mode = self.is_silenced()
      self.silence(True,False)
      t = pd.DataFrame( proj.eng.desc() )
      self.silence( silence_mode , False )
      t.index = t.index + 1
      if len( t ) == 0: return t
      t.columns = ["ID","Gapped","Date","Start(hms)","Stop(hms)","Dur(hms)","Dur(s)","# sigs","# annots","Signals" ]
      with pd.option_context('max_colwidth',None):
         display(t)


   #------------------------------------------------------------------------

   def proc(self, cmdstr ):
      """Evaluate one or more Luna commands across all sample-list individuals.

      Results are stored internally and also returned.  Use :meth:`table` or
      :meth:`strata` to interrogate specific outputs afterwards.

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands, optionally separated by newlines.

      Returns
      -------
      dict
          Mapping of ``"COMMAND: STRATA"`` keys to ``pandas.DataFrame``
          result tables.
      """
      r = proj.eng.eval(cmdstr)
      return tables( r )

   #------------------------------------------------------------------------

   def silent_proc(self, cmdstr ):
      """Evaluate Luna commands across all sample-list individuals without printing log output.

      Identical to :meth:`proc` but suppresses console output for the
      duration of the call, then restores the previous silence state.

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands, optionally separated by newlines.

      Returns
      -------
      dict
          Mapping of ``"COMMAND: STRATA"`` keys to ``pandas.DataFrame``
          result tables.
      """
      silence_mode = self.is_silenced()
      self.silence(True,False)
      r = proj.eng.eval(cmdstr)
      self.silence( silence_mode , False )
      return tables( r )

   #------------------------------------------------------------------------

   def commands( self ):
      """Return a DataFrame listing the commands present in the output store.

      Returns
      -------
      pandas.DataFrame
          Single-column DataFrame with column ``'Command'``.
      """
      t = pd.DataFrame( proj.eng.commands() )
      t.columns = ["Command"]
      return t

   #------------------------------------------------------------------------

   def empty_result_set( self ):
      """Return ``True`` if the result store contains no output tables.

      Returns
      -------
      bool
          ``True`` when no results are stored; ``False`` otherwise.
      """
      return len( proj.eng.strata()  ) == 0

   #------------------------------------------------------------------------

   def strata( self ):
      """Return a DataFrame of command/strata pairs from the output store.

      Returns
      -------
      pandas.DataFrame or None
          DataFrame with columns ``['Command', 'Strata']``, or ``None`` if
          the result store is empty.
      """

      if self.empty_result_set(): return None
      t = pd.DataFrame( proj.eng.strata() )
      t.columns = ["Command","Strata"]
      return t

   #------------------------------------------------------------------------

   def table( self, cmd , strata = 'BL' ):
      """Return a specific output table as a DataFrame.

      Parameters
      ----------
      cmd : str
          Luna command name (e.g. ``'PSD'``, ``'STAGE'``).
      strata : str, optional
          Stratum label for the desired table (e.g. ``'CH_F'``, ``'E'``).
          Defaults to ``'BL'`` (baseline / un-stratified).

      Returns
      -------
      pandas.DataFrame or None
          Result table, or ``None`` if the result store is empty.
      """
      if self.empty_result_set(): return None
      r = proj.eng.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   #------------------------------------------------------------------------

   def variables( self, cmd , strata = 'BL' ):
      """Return the variable names present in a specific output table.

      Parameters
      ----------
      cmd : str
          Luna command name.
      strata : str, optional
          Stratum label.  Defaults to ``'BL'``.

      Returns
      -------
      list of str or None
          Variable (column) names for the requested table, or ``None`` if
          the result store is empty.
      """
      if self.empty_result_set(): return None
      return proj.eng.vars( cmd , strata )


#
# --------------------------------------------------------------------------------
# project level wrapper functions
#

   # --------------------------------------------------------------------------------

   def pops( self, s = None, s1 = None , s2 = None,
             path = None , lib = None ,
             do_edger = True ,
             no_filter = False ,
             do_reref = False ,
             m = None , m1 = None , m2 = None,
             lights_off = '.' , lights_on = '.' ,
             ignore_obs = False,
             args = '' ):
      """Run the POPS automatic sleep stager across the whole sample list.

      POPS (Population-based sleep staging) uses a pre-trained model to
      assign sleep stages to each epoch.  Results are returned as a
      DataFrame from the ``POPS`` command.

      Call this method in **single-channel** mode by setting *s* only, or
      in **two-channel** mode by setting *s1* and *s2*.

      Parameters
      ----------
      s : str, optional
          EEG channel label for single-channel staging.
      s1 : str, optional
          First EEG channel for two-channel staging.
      s2 : str, optional
          Second EEG channel for two-channel staging.
      path : str, optional
          Path to the POPS resource folder.  Defaults to
          ``resources.POPS_PATH``.
      lib : str, optional
          POPS library name (sub-folder within *path*).  Defaults to
          ``resources.POPS_LIB`` (``'s2'``).
      do_edger : bool, optional
          Apply EDGER artifact detection.  Default ``True``.
      no_filter : bool, optional
          Skip bandpass pre-filtering of the EEG.  Default ``False``.
      do_reref : bool, optional
          Re-reference the EEG to a mastoid channel before staging.
          Default ``False``.
      m : str, optional
          Mastoid channel for single-channel re-referencing (required when
          *do_reref* is ``True`` and *s* is set).
      m1 : str, optional
          First mastoid channel for two-channel re-referencing.
      m2 : str, optional
          Second mastoid channel for two-channel re-referencing.
      lights_off : str, optional
          Lights-off time as ``'HH:MM:SS'``.  Use ``'.'`` if unknown.
          Default ``'.'``.
      lights_on : str, optional
          Lights-on time as ``'HH:MM:SS'``.  Use ``'.'`` if unknown.
          Default ``'.'``.
      ignore_obs : bool, optional
          Ignore any observed (manual) staging annotations.
          Default ``False``.
      args : str, optional
          Additional options to append to the ``POPS`` Luna command string.
          Default ``''``.

      Returns
      -------
      pandas.DataFrame or str
          DataFrame of per-epoch staging results from the ``POPS`` command,
          or an error string if the resource path cannot be opened.
      """

      if path is None: path = resources.POPS_PATH
      if lib is None: lib = resources.POPS_LIB

      import os
      if not os.path.isdir( path ):
         return 'could not open POPS resource path ' + path

      if s is None and s1 is None:
         print( 'must set s or s1 and s2 to EEGs' )
         return

      if ( s1 is None ) != ( s2 is None ):
         print( 'must set s or s1 and s2 to EEGs' )
         return

      # POPS templates may reference mastoid vars even when do_reref is false.
      # Provide safe placeholders unless rereferencing is explicitly requested.
      if do_reref:
         if s is not None and m is None:
            print( 'must set m when do_reref is True in single-channel mode' )
            return
         if s1 is not None and ( m1 is None or m2 is None ):
            print( 'must set m1 and m2 when do_reref is True in two-channel mode' )
            return
      else:
         if m is None: m = '.'
         if m1 is None: m1 = '.'
         if m2 is None: m2 = '.'

      # set options
      self.var( 'mpath' , path )
      self.var( 'lib' , lib )
      self.var( 'do_edger' , '1' if do_edger else '0' )
      self.var( 'do_reref' , '1' if do_reref else '0' )
      self.var( 'no_filter' , '1' if no_filter else '0' )
      self.var( 'LOFF' , lights_off )
      self.var( 'LON' , lights_on )

      if s is not None: self.var( 's' , s )
      else: self.clear_vars( 's' )

      if m is not None: self.var( 'm' , m )
      else: self.clear_vars( 'm' )

      if s1 is not None: self.var( 's1' , s1 )
      else: self.clear_vars( 's1' )

      if s2 is not None: self.var( 's2' , s2 )
      else: self.clear_vars( 's2' )

      if m1 is not None: self.var( 'm1' , m1 )
      else: self.clear_vars( 'm1' )

      if m2 is not None: self.var( 'm2' , m2 )
      else: self.clear_vars( 'm2' )

      # get either one- or two-channel mode Luna script from POPS folder
      twoch = s1 is not None and s2 is not None;
      if twoch: cmdstr = cmdfile( path + '/s2.ch2.txt' )
      else: cmdstr = cmdfile( path + '/s2.ch1.txt' )

      # swap in any additional options to POPS
      if ignore_obs is True:
         args = args + ' ignore-obs-staging';
         if do_edger is True:
            cmdstr = cmdstr.replace( 'EDGER' , 'EDGER all' )
      if args != '':
            cmdstr = cmdstr.replace( 'POPS' , 'POPS ' + args + ' ')

      # run the command
      self.proc( cmdstr )

      # return of results
      return self.table( 'POPS' )


   # --------------------------------------------------------------------------------

   def predict_SUN2019( self, cen , th = '3' , path = None ):
      """Run the SUN2019 brain-age prediction model for the whole sample list.

      Applies the SUN2019 EEG-based brain-age prediction model to every
      individual in the sample list.  The individual ``${age}`` variable
      must be set via a vars file before calling this method, e.g.::

          proj.var('vars', 'ages.txt')

      Parameters
      ----------
      cen : str or list of str
          EEG centroid channel label(s).  A list is joined with commas
          before being passed to Luna.
      th : str or int, optional
          Outlier threshold (in standard deviations) for feature exclusion.
          Default ``'3'``.
      path : str, optional
          Path to the Luna models folder.  Defaults to
          ``resources.MODEL_PATH``.

      Returns
      -------
      pandas.DataFrame
          DataFrame of prediction results from the ``PREDICT`` command.
      """
      if path is None: path = resources.MODEL_PATH
      if type( cen ) is list: cen = ','.join( cen )
      self.var( 'cen' , cen )
      self.var( 'mpath' , path )
      self.var( 'th' , str(th) )
      self.proc( cmdfile( resources.MODEL_PATH + '/m1-adult-age-luna.txt' ) )
      return self.table( 'PREDICT' )






# ================================================================================
# --------------------------------------------------------------------------------
#
# inst class
#
# --------------------------------------------------------------------------------
# ================================================================================

__all__ = ["proj"]
