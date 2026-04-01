"""Instance-level Luna API.

This module exports :class:`inst`, the per-record wrapper around EDF data,
annotation access, evaluation, and in-memory signal editing operations.
"""

import lunapi.lunapi0 as _luna

import pandas as pd
import numpy as np
from scipy.stats.mstats import winsorize
from scipy.signal import sosfilt
import matplotlib.pyplot as plt
from matplotlib import cm
try:
    from IPython.core import display as ICD
    from IPython.display import display as _ipy_display
except ImportError:
    ICD = None
    _ipy_display = None
import plotly.graph_objects as go
import time
import pathlib
import os

from .project import proj
from .resources import resources
from .results import tables, cmdfile


def hypno(*args, **kwargs):
   """Lazy proxy to :func:`lunapi.viz.hypno` to avoid circular imports."""
   from .viz import hypno as _hypno
   return _hypno(*args, **kwargs)


def psd(*args, **kwargs):
   """Lazy proxy to :func:`lunapi.viz.psd` to avoid circular imports."""
   from .viz import psd as _psd
   return _psd(*args, **kwargs)


def spec(*args, **kwargs):
   """Lazy proxy to :func:`lunapi.viz.spec` to avoid circular imports."""
   from .viz import spec as _spec
   return _spec(*args, **kwargs)


class inst:
   """Wrapper around a single EDF record (signals, annotations, and results).

   An :class:`inst` object represents one individual/study and provides
   methods to:

   - attach EDF and annotation files
   - inspect channel headers and annotation classes
   - set individual-level variables
   - run Luna commands and retrieve the resulting tables
   - extract raw signal data and annotation events
   - insert or update in-memory signals and annotations
   - produce quick visualisations (hypnogram, PSD, spectrogram)

   Instances are normally obtained through :meth:`proj.inst` or created
   directly for stand-alone EDF access::

       p = proj()
       individual = p.inst(1)          # from a sample list
       individual = inst('path/to.edf')  # direct file path
   """

   def __init__(self,p=None):
      if ( isinstance(p,str) ):
         self.edf = _luna.inst(p)
      elif (isinstance(p,_luna.inst)):
         self.edf = p
      else:
         self.edf = _luna.inst()

   def __repr__(self):
      return f'{self.edf}'

   #------------------------------------------------------------------------

   def id(self):
      """Return the identifier for this instance.

      Returns
      -------
      str
          The individual ID string as set in the sample list or EDF header.
      """
      return self.edf.get_id()

   #------------------------------------------------------------------------

   def attach_edf( self, f ):
      """Attach an EDF file to this instance.

      Parameters
      ----------
      f : str or path-like
          Path to the EDF (or EDF+/EDF.gz) file to load.

      Returns
      -------
      object
          Status value returned by the C++ backend.
      """
      return self.edf.attach_edf( f )

   #------------------------------------------------------------------------

   def attach_annot( self, annot ):
      """Attach an annotation file to this instance.

      Parameters
      ----------
      annot : str or path-like
          Path to an annotation file (e.g. ``.xml``, ``.annot``, ``.eannot``).

      Returns
      -------
      object
          Status value returned by the C++ backend.
      """
      return self.edf.attach_annot( annot )

   #------------------------------------------------------------------------

   def stat( self ):
      """Return a DataFrame of basic EDF statistics.

      Returns
      -------
      pandas.DataFrame
          Single-column DataFrame (index = statistic name, values in
          ``'Value'`` column) including record count, sample rates,
          duration, etc.
      """
      t = pd.DataFrame( self.edf.stat(), index=[0] ).T
      t.columns = ["Value"]
      return t

   #------------------------------------------------------------------------

   def refresh( self ):
      """Reload the attached EDF from disk and reset the problem flag.

      Returns
      -------
      None
      """
      self.edf.refresh()
      # also need to reset Luna problem flag
      # note: current kludge: problem is proj-wide
      #       so this will not play well w/ multiple EDFs
      # todo: implement inst-specific prob flag

      _proj = proj(False)
      _proj.reset();

   #------------------------------------------------------------------------

   def refresh_channel_vars( self ):
      """Re-populate channel-type variables (e.g. ${eeg}, ${ecg}) without
      re-reading the EDF from disk.  Call this after proj.reinit() to restore
      the channel-type variables that reinit() clears.

      Returns
      -------
      None
      """
      self.edf.refresh_channel_vars()


   #------------------------------------------------------------------------

   def clear_vars(self, keys = None ):
      """Clear individual-level variable(s) for this instance.

      Parameters
      ----------
      keys : str, list of str, or set of str, optional
          Name(s) of the variable(s) to remove.  If omitted, **all**
          individual-level variables are cleared.

      Returns
      -------
      None
      """

      # all
      if keys is None:
         self.edf.clear_ivar()
         return

      # one/some
      if isinstance(keys, str):
         keys = { keys }
      elif type( keys ) is not set:
         keys = set( keys )
      self.edf.clear_selected_ivar( keys )

   #------------------------------------------------------------------------

   def var( self , key = None , value = None ):
      """Get or set one or more individual-level variables.

      Thin alias for :meth:`vars`.

      Parameters
      ----------
      key : str, dict, or None, optional
          Variable name to get/set, or a ``{name: value}`` dict.
      value : str, optional
          Value to assign when *key* is a single name.

      Returns
      -------
      str, dict, or None
          The variable value(s) when getting; ``None`` when setting.
      """
      return self.vars( key , value )

   #------------------------------------------------------------------------

   def vars( self , key = None , value = None ):
      """Get or set one or more individual-level variables.

      Individual-level variables (i-vars) are scoped to this instance and
      override any project-level variable of the same name.

      Parameters
      ----------
      key : str, dict, or None, optional
          - ``None``: return all i-vars as a dict.
          - ``str``: return the value for that variable (if *value* is
            omitted), or set it to *value*.
          - ``dict``: set multiple variables from a ``{name: value}`` dict.
      value : str, optional
          Value to assign when *key* is a single variable name.

      Returns
      -------
      str, dict, or None
          The variable value(s) when getting; ``None`` when setting.
      """

      # return all i-vars
      if key is None:
         return self.edf.ivars()

      # return one i-var
      if value is None and type( key ) is str:
         return self.edf.get_ivar( key )

      # set from a dict of key-value pairs
      if isinstance(key, dict):
         for k, v in key.items():
            self.vars(k,v)
         return

      # set a single pair
      self.edf.ivar( key , str(value) )


   #------------------------------------------------------------------------

   def desc( self ):
      """Display a one-row summary of this instance's EDF.

      Prints a DataFrame with columns:
      ``['ID', 'Gapped', 'Date', 'Start(hms)', 'Stop(hms)', 'Dur(hms)',
      'Dur(s)', '# sigs', '# annots', 'Signals']``.

      Returns
      -------
      None
          Output is rendered via ``IPython.display``.
      """
      t = pd.DataFrame( self.edf.desc() ).T
      t.index =	t.index	+ 1
      if len( t ) == 0: return t
      t.columns = ["ID","Gapped","Date","Start(hms)","Stop(hms)","Dur(hms)","Dur(s)","# sigs","# annots","Signals" ]
      with pd.option_context('display.max_colwidth',None):
         if _ipy_display is not None:
            _ipy_display(t)

   #------------------------------------------------------------------------

   def channels( self ):
      """Return a DataFrame listing the channels in this EDF.

      Returns
      -------
      pandas.DataFrame
          Single-column DataFrame with column ``'Channels'``.
      """
      t = pd.DataFrame( self.edf.channels() )
      if len( t ) == 0: return t
      t.columns = ["Channels"]
      return t

   #------------------------------------------------------------------------

   def chs( self ):
      """Return a DataFrame listing the channels in this EDF.

      Alias for :meth:`channels`.

      Returns
      -------
      pandas.DataFrame
          Single-column DataFrame with column ``'Channels'``.
      """
      t = pd.DataFrame( self.edf.channels() )
      if len( t ) == 0: return t
      t.columns = ["Channels"]
      return t

   #------------------------------------------------------------------------

   def headers(self):
      """Return EDF channel header information.

      Runs the Luna ``HEADERS`` command silently and returns the
      ``HEADERS: CH`` table.

      Returns
      -------
      pandas.DataFrame or None
          DataFrame with one row per channel and columns including
          ``CH``, ``SR``, ``PDIM``, ``PMIN``, ``PMAX``, etc., or
          ``None`` if the command produced no output.
      """
      _proj = proj(False)
      silence_mode = _proj.is_silenced()
      _proj.silence(True,False)

      res = self.proc( "HEADERS" )

      if "HEADERS: CH" in res:
         df = res["HEADERS: CH"]
      else:
         df = None

      _proj.silence( silence_mode , False )
      return df

   #------------------------------------------------------------------------

   def annots( self ):
      """Return a DataFrame listing the annotation classes in this dataset.

      Returns
      -------
      pandas.DataFrame
          Single-column DataFrame with column ``'Annotations'``.
      """
      t = pd.DataFrame( self.edf.annots() )
      if len( t ) == 0: return t
      t.columns = ["Annotations"]
      return t

   #------------------------------------------------------------------------

   def fetch_annots( self , anns , interp = -1 ):
      """Return annotation events for one or more classes.

      Parameters
      ----------
      anns : str or list of str
          Annotation class name(s) to retrieve.
      interp : int, optional
          Interpolation mode passed to the backend.  Default ``-1``
          (no interpolation).

      Returns
      -------
      pandas.DataFrame
          DataFrame with columns ``['Class', 'Start', 'Stop']`` sorted by
          start time.  Times are in seconds (rounded to 3 decimal places).
      """
      if type( anns ) is not list: anns = [ anns ]
      t = pd.DataFrame( self.edf.fetch_annots( anns , interp ) )
      if len( t ) == 0: return t
      t.columns = ['Class', 'Start', 'Stop' ]
      t = t.sort_values(by=['Start', 'Stop', 'Class'])
      t['Start'] = t['Start'].round(decimals=3)
      t['Stop'] = t['Stop'].round(decimals=3)
      return t

   #------------------------------------------------------------------------

   def fetch_fulls_annots( self , anns ):
      """Return annotation events including instance ID, channel, and metadata.

      Parameters
      ----------
      anns : str or list of str
          Annotation class name(s) to retrieve.

      Returns
      -------
      pandas.DataFrame
          DataFrame with columns
          ``['Class', 'Instance', 'Channel', 'Meta', 'Start', 'Stop']``
          sorted by start time.  Times are in seconds.
      """
      if type( anns ) is not list: anns = [ anns ]
      t = pd.DataFrame( self.edf.fetch_full_annots( anns ) )
      if len( t ) == 0: return t
      t.columns = ['Class', 'Instance','Channel','Meta','Start', 'Stop' ]
      t = t.sort_values(by=['Start', 'Stop', 'Class','Instance'])
      t['Start'] = t['Start'].round(decimals=3)
      t['Stop'] = t['Stop'].round(decimals=3)
      return t

   #------------------------------------------------------------------------

   def eval( self, cmdstr ):
      """Evaluate one or more Luna commands and store results internally.

      Results are accumulated in the instance result store and can be
      retrieved with :meth:`strata` and :meth:`table`.

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands, optionally separated by newlines.

      Returns
      -------
      pandas.DataFrame or None
          DataFrame of command/strata pairs from the result store after
          evaluation (i.e. the result of :meth:`strata`).
      """
      self.edf.eval( cmdstr )
      return self.strata()

   #------------------------------------------------------------------------

   def eval_dummy( self, cmdstr ):
      """Evaluate commands in dummy (dry-run) mode and return the log text.

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands.

      Returns
      -------
      str
          Console/log text produced by the backend during dry-run
          evaluation.
      """
      return self.edf.eval_dummy( cmdstr )

   #------------------------------------------------------------------------

   def eval_lunascope( self, cmdstr ):
      """Evaluate commands and return the console log along with results.

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands.

      Returns
      -------
      object
          Console log text returned by the LunaScope backend.
      """
      return self.edf.eval_lunascope( cmdstr )

   #------------------------------------------------------------------------

   def proc( self, cmdstr ):
      """Evaluate one or more Luna commands and return results as a dict.

      Unlike :meth:`eval`, this method returns the result tables directly
      as a dict rather than storing them internally.

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands, optionally separated by newlines.

      Returns
      -------
      dict
          Mapping of ``"COMMAND: STRATA"`` string keys to
          ``pandas.DataFrame`` result tables.
      """
      # < log , tables >
      r = self.edf.proc( cmdstr )
      # extract and return result tables
      return tables( r[1] )

   #------------------------------------------------------------------------

   def silent_proc( self, cmdstr ):
      """Evaluate Luna commands silently and return results as a dict.

      Suppresses log output for the duration of the call, then restores
      the previous silence state.  Primarily used by internal helper
      methods (e.g. :meth:`stages`, :meth:`has_staging`).

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands.

      Returns
      -------
      dict
          Mapping of ``"COMMAND: STRATA"`` keys to ``pandas.DataFrame``
          result tables.
      """

      _proj = proj(False)
      silence_mode = _proj.is_silenced()
      _proj.silence(True,False)

      r = self.edf.proc( cmdstr )

      _proj.silence( silence_mode , False )

      # extract and return result tables
      return tables( r[1] )

   #------------------------------------------------------------------------

   def silent_proc_lunascope( self, cmdstr ):
      """Evaluate Luna commands silently via LunaScope and return results.

      Parameters
      ----------
      cmdstr : str
          One or more Luna commands.

      Returns
      -------
      dict
          Mapping of ``"COMMAND: STRATA"`` keys to ``pandas.DataFrame``
          result tables.
      """

      _proj = proj(False)
      silence_mode = _proj.is_silenced()
      _proj.silence(True,False)

      r = self.edf.proc_lunascope( cmdstr )

      _proj.silence( silence_mode , False )

      # extract and return result tables
      return tables( r[1] )

   #------------------------------------------------------------------------

   def empty_result_set( self ):
      """Return ``True`` if the instance result store contains no tables.

      Returns
      -------
      bool
          ``True`` when no results are stored; ``False`` otherwise.
      """
      return len( self.edf.strata()  ) == 0

   #------------------------------------------------------------------------

   def strata( self ):
      """Return a DataFrame of command/strata pairs from the result store.

      Returns
      -------
      pandas.DataFrame or None
          DataFrame with columns ``['Command', 'Strata']``, or ``None``
          if the result store is empty.
      """
      if ( self.empty_result_set() ): return None
      t = pd.DataFrame( self.edf.strata() )
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
          Stratum label (e.g. ``'CH_F'``, ``'E'``).  Default ``'BL'``.

      Returns
      -------
      pandas.DataFrame or None
          Result table, or ``None`` if the result store is empty.
      """
      if ( self.empty_result_set() ): return None
      r = self.edf.table( cmd , strata )
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
          Stratum label.  Default ``'BL'``.

      Returns
      -------
      list of str or None
          Variable (column) names, or ``None`` if the result store is
          empty.
      """
      if ( self.empty_result_set() ): return None
      return self.edf.variables( cmd , strata )


   #------------------------------------------------------------------------

   def e2i( self, epochs ):
      """Convert 1-based epoch numbers to time intervals (nanoseconds).

      Parameters
      ----------
      epochs : int or list of int
          One or more 1-based epoch indices.

      Returns
      -------
      list of tuple
          List of ``(start_ns, stop_ns)`` tuples in internal nanosecond
          time units.
      """
      if type( epochs ) is not list: epochs = [ epochs ]
      return self.edf.e2i( epochs )

   # --------------------------------------------------------------------------------

   def s2i( self, secs ):
      """Convert a duration in seconds to an internal time interval.

      Parameters
      ----------
      secs : float
          Duration in seconds.

      Returns
      -------
      tuple
          ``(start_ns, stop_ns)`` interval tuple in nanosecond time units.
      """
      return self.edf.s2i( secs )

   # --------------------------------------------------------------------------------

   def data( self, chs , annots = None , time = False ):
      """Return all signal and annotation data for the specified channels.

      Parameters
      ----------
      chs : str or list of str
          Channel label(s) to extract.
      annots : str or list of str, optional
          Annotation class(es) to include as binary indicator columns.
      time : bool, optional
          If ``True``, prepend a time-in-seconds column to the returned
          matrix.  Default ``False``.

      Returns
      -------
      tuple
          ``(column_names, data_matrix)`` where *data_matrix* is a
          NumPy array with one row per sample.
      """
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.data( chs , annots , time )

   # --------------------------------------------------------------------------------

   def slice( self, intervals, chs , annots = None , time = False ):
      """Return signal/annotation data aggregated over a set of intervals.

      Concatenates all samples that fall within any of the supplied
      intervals into a single matrix.

      Parameters
      ----------
      intervals : list of tuple
          List of ``(start_ns, stop_ns)`` interval tuples (as returned by
          :meth:`e2i` or :meth:`s2i`).
      chs : str or list of str
          Channel label(s) to extract.
      annots : str or list of str, optional
          Annotation class(es) to include as indicator columns.
      time : bool, optional
          If ``True``, prepend a time column.  Default ``False``.

      Returns
      -------
      tuple
          ``(column_names, data_matrix)`` NumPy array for the concatenated
          intervals.
      """
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.slice( intervals, chs , annots , time )

   # --------------------------------------------------------------------------------

   def slices( self, intervals, chs , annots = None , time = False ):
      """Return separate signal/annotation matrices for each interval.

      Unlike :meth:`slice`, each interval produces its own matrix rather
      than being concatenated together.

      Parameters
      ----------
      intervals : list of tuple
          List of ``(start_ns, stop_ns)`` interval tuples.
      chs : str or list of str
          Channel label(s) to extract.
      annots : str or list of str, optional
          Annotation class(es) to include as indicator columns.
      time : bool, optional
          If ``True``, prepend a time column to each matrix.  Default
          ``False``.

      Returns
      -------
      list of tuple
          One ``(column_names, data_matrix)`` tuple per interval.
      """
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.slices( intervals, chs , annots , time )

   # --------------------------------------------------------------------------------

   def insert_signal( self, label , data , sr ):
      """Insert a new signal into the in-memory EDF.

      Parameters
      ----------
      label : str
          Channel label for the new signal.
      data : array-like
          Signal samples as a 1-D sequence.
      sr : int
          Sample rate in Hz.

      Returns
      -------
      None
      """
      return self.edf.insert_signal( label , data , sr )

   # --------------------------------------------------------------------------------

   def update_signal( self, label , data ):
      """Overwrite an existing in-memory signal's sample values.

      Parameters
      ----------
      label : str
          Channel label of the signal to update.
      data : array-like
          New sample values (must match the existing channel length).

      Returns
      -------
      None
      """
      return self.edf.update_signal( label , data )

   # --------------------------------------------------------------------------------

   def insert_annot( self, label , intervals, durcol2 = False ):
      """Insert annotation events into the in-memory dataset.

      Parameters
      ----------
      label : str
          Annotation class label.
      intervals : list of tuple
          List of ``(start, stop)`` or ``(start, duration)`` tuples
          depending on *durcol2*.
      durcol2 : bool, optional
          If ``True``, the second element of each tuple is interpreted as
          a duration rather than a stop time.  Default ``False``.

      Returns
      -------
      None
      """
      return self.edf.insert_annot( label , intervals , durcol2 )



   # --------------------------------------------------------------------------------
   #
   # Luna function wrappers
   #
   # --------------------------------------------------------------------------------


   # --------------------------------------------------------------------------------

   def freeze( self , f ):
      """Persist the current timeline mask to a named freezer tag.

      Parameters
      ----------
      f : str
          Freezer tag name.

      Returns
      -------
      None
      """
      self.eval( 'FREEZE ' + f )

   # --------------------------------------------------------------------------------

   def thaw( self , f , remove = False ):
      """Restore a previously saved freezer tag.

      Parameters
      ----------
      f : str
          Freezer tag name.
      remove : bool, optional
          If ``True``, remove the tag after thawing.  Default ``False``.

      Returns
      -------
      None
      """
      if remove:
         self.eval( 'THAW tag=' + f + ' remove' )
      else:
         self.eval( 'THAW ' + f )

   # --------------------------------------------------------------------------------

   def empty_freezer( self ):
      """Clear all persisted freezer tags for this instance.

      Returns
      -------
      object
          Result of the ``CLEAN-FREEZER`` command evaluation.
      """
      self.eval( 'CLEAN-FREEZER' )

   # --------------------------------------------------------------------------------

   def mask( self , f = None ):
      """Apply one or more Luna mask expressions and rebuild epochs.

      Parameters
      ----------
      f : str or list of str, optional
          One or more Luna ``MASK`` expressions or files to apply.
          Epochs are rebuilt (``RE``) after all masks are applied.

      Returns
      -------
      None
      """
      if f is None: return
      if type(f) is not list: f = [ f ]
      [ self.eval( 'MASK ' + _f ) for _f in f ]
      self.eval( 'RE' )


   # --------------------------------------------------------------------------------

   def segments( self ):
      """Run ``SEGMENTS`` and return the contiguous segment table.

      Returns
      -------
      pandas.DataFrame
          ``SEGMENTS: SEG`` table with segment start/stop times.
      """
      self.eval( 'SEGMENTS' )
      return self.table( 'SEGMENTS' , 'SEG' )

   # --------------------------------------------------------------------------------

   def epoch( self , f = '' ):
      """Run the ``EPOCH`` command with optional arguments.

      Parameters
      ----------
      f : str, optional
          Additional ``EPOCH`` arguments (e.g. ``'dur=30'``).

      Returns
      -------
      None
      """
      self.eval( 'EPOCH ' + f )


   # --------------------------------------------------------------------------------

   def epochs( self ):
      """Run ``EPOCH table`` and return a compact epoch summary DataFrame.

      Returns
      -------
      pandas.DataFrame
          Columns ``['E', 'E1', 'LABEL', 'HMS', 'START', 'STOP', 'DUR']``
          with one row per epoch.
      """
      self.eval( 'EPOCH table' )
      df = self.table( 'EPOCH' , 'E' )
      df = df[[ 'E', 'E1', 'LABEL', 'HMS', 'START','STOP','DUR' ]]
      #df = df.drop(columns = ['ID','TP','MID','INTERVAL'] )
      return df


   # --------------------------------------------------------------------------------
   #  tfview : spectral regional viewer

   # for high-def plots:
   # import matplotlib as mpl
   # mpl.rcParams['figure.dpi'] = 300

   def tfview( self , ch,
               e = None , t = None , a = None,
               tw = 2, sec = 2 , inc = 0.1 ,
               f = ( 0.5 , 30 ) , winsor = 0.025 ,
               anns = None , norm = None ,
               traces = True,
               xlines = None , ylines = None , silent = True , pal = 'turbo' ):

      """Generate an MTM time-frequency spectrogram for a single channel.

      Runs the Luna ``MTM`` command over the requested time window and
      renders a Matplotlib spectrogram, optionally with the raw signal
      trace above it.

      Parameters
      ----------
      ch : str
          Channel label (single channel only).

      Selection of intervals
      ~~~~~~~~~~~~~~~~~~~~~~
      e : int or list of two ints, optional
          Epoch range: a single epoch number or ``[start_epoch, stop_epoch]``
          (both 1-based).
      t : list of two floats, optional
          Explicit time window ``[start_sec, stop_sec]``.  Used when *e*
          is not provided.
      a : object, optional
          Reserved for future use (annotation-based selection).

      Spectrogram parameters
      ~~~~~~~~~~~~~~~~~~~~~~
      tw : float, optional
          MTM half-bandwidth parameter.  Default ``2``.
      sec : float, optional
          Segment length in seconds for MTM sliding window.  Default ``2``.
      inc : float, optional
          Increment between segment centres in seconds.  Default ``0.1``.
      f : tuple of (float, float), optional
          Frequency range ``(min_hz, max_hz)``.  Default ``(0.5, 30)``.
      winsor : float, optional
          Winsorisation proportion applied to the power values before
          colour-mapping.  Default ``0.025``.
      norm : str, optional
          Normalisation mode.  Use ``'t'`` for time-wise z-scoring.
          Default ``None`` (no normalisation).

      Display options
      ~~~~~~~~~~~~~~~
      traces : bool, optional
          If ``True`` (default), show the raw signal trace above the
          spectrogram.
      anns : str or list of str, optional
          Annotation class(es) to overlay on the trace panel.
      xlines : object, optional
          Reserved for future use.
      ylines : object, optional
          Reserved for future use.
      silent : bool, optional
          Run the MTM command silently.  Default ``True``.
      pal : str, optional
          Matplotlib colour map name for the spectrogram.  Default
          ``'turbo'``.

      Returns
      -------
      None
          The plot is rendered inline.
      """

      # for now, accept only a single channel
      assert type(ch) is str

      # units
      hdr = self.headers()
      units = dict( zip( hdr.CH , hdr.PDIM ) )

      # define window
      w = None
      if type(e) is list and len(e) == 2 :
         w = self.e2i( e )
         w = [ i for tuple in w for i in tuple ]
         w = [ min(w) , max(w) ]
      elif type(e) is int:
         w = self.e2i( e )
         w = [ i for tuple in w for i in tuple ]
      elif type( t ) is list and len( t ) == 2:
         w = t

      if w is None: return

      # window in seconds
      ws = [ x * 1e-9 for x in w ]
      ls = ws[1] - ws[0]

      # build command
      cstr = 'MTM dB  segment-sec=' + str(sec) + ' segment-inc=' + str(inc) + ' tw=' + str(tw)
      cstr += ' segment-spectra segment-output sig=' + ','.join( [ ch ] )
      cstr += ' start=' + str(ws[0]) + ' stop=' + str(ws[1])
      if f is not None: cstr += ' min=' + str(f[0]) + ' max=' + str(f[1])

      # run MTM
      if silent is True: self.silent_proc( cstr )
      else: self.proc( cstr )

      if self.empty_result_set(): return

      # extract
      tf = self.table( 'MTM' , 'CH_F_SEG' )
      tf = tf.astype({'SEG': int })
      tf.drop( 'ID' , axis=1, inplace=True)

      tt = self.table('MTM','CH_SEG')
      tt = tt.astype({'SEG': int })
      tt['T'] = tt[['START', 'STOP']].mean(axis=1)
      tt.drop( ['ID','DISC','START','STOP'] , axis=1, inplace=True)

      m = pd.merge( tt ,tf , on= ['CH','SEG'] )

      x = m['T'].to_numpy(dtype=float)
      y = m['F'].to_numpy(dtype=float)
      z = m['MTM'].to_numpy(dtype=float)
      u = m['T'].unique()

      # normalize?
      if norm == 't':
         groups = m.groupby(['CH','F'])[['MTM']]
         mean, std = groups.transform("mean"), groups.transform("std")
         mz = (m[mean.columns] - mean) / std
         z = mz['MTM'].to_numpy(dtype=float)


      # clip y-axes to observed
      if max(y) < f[1]: f = (f[0] , max(y))
      if min(y) > f[0]: f = (min(y) , f[1])

      # get time domain signal/annotations
      d = self.slices( [ (w[0] , w[1] )] , chs = ch , annots = anns , time = True )
      dt = d[1][0]
      tx = dt[:,0]
      dvs = d[0][1:]

      # make spectrogram
      xn = np.unique(x).size
      yn = np.unique(y).size

      # winsorize power
      z = winsorize( z , limits=[winsor, winsor] )

      zi, yi, xi = np.histogram2d(y, x, bins=(yn,xn), weights=z, density=False )
      counts, _, _ = np.histogram2d(y, x, bins=(yn,xn))
      with np.errstate(divide='ignore', invalid='ignore'): zi = zi / counts
      zi = np.ma.masked_invalid(zi)

      # do plot

      if traces is True:
         fig, axs = plt.subplots( nrows = 2 , ncols = 1 , sharex=True,  height_ratios=[1, 2] )
         axs[0].set_title( self.id() )
         fig.set_figheight(5)
         fig.set_figwidth(15)
         axs[0].set_ylabel( ch + ' (' + units[ch] + ')' )
         axs[0].set(xlim=ws)
         axs[1].set(xlim=ws, ylim=f)
         axs[1].set_xlabel('Time (secs)')
         axs[1].set_ylabel('Frequency (Hz)')
         p1 = axs[1].pcolormesh(xi, yi, zi, cmap = pal )
         fig.colorbar(p1, orientation="horizontal", drawedges = False, shrink = 0.2 , pad = 0.3)
         [ axs[0].plot( tx , dt[:,di+1] , label = dvs[di] , linewidth=0.5 ) for di in range(0,len(dvs)) if dvs[di] in [ ch ] ]

      if traces is False:
         fig, ax = plt.subplots( nrows = 1 , ncols = 1 , sharex=True  )
         ax.set_title( self.id() )
         fig.set_figheight(5)
         fig.set_figwidth(15)
         ax.set(xlim=ws, ylim=f)
         ax.set_xlabel('Time (secs)')
         ax.set_ylabel('Frequency (Hz)')
         p1 = ax.pcolormesh(xi, yi, zi, cmap = pal )
         fig.colorbar(p1, orientation="horizontal", drawedges = False, shrink = 0.2 , pad = 0.3)

      return


   # --------------------------------------------------------------------------------

   def pops( self, s = None, s1 = None , s2 = None,
             path = None , lib = None ,
             do_edger = True ,
             no_filter = False ,
             do_reref = False ,
             m = None , m1 = None , m2 = None ,
             lights_off = '.' , lights_on = '.' ,
             ignore_obs = False,
             args = '' ):
      """Run the POPS automatic sleep stager on this individual.

      POPS (Population-based sleep staging) assigns sleep stages to each
      epoch using a pre-trained model.  Use *s* alone for single-channel
      mode, or *s1*/*s2* together for two-channel mode.

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
          POPS library name.  Defaults to ``resources.POPS_LIB`` (``'s2'``).
      do_edger : bool, optional
          Apply EDGER artifact detection.  Default ``True``.
      no_filter : bool, optional
          Skip bandpass pre-filtering.  Default ``False``.
      do_reref : bool, optional
          Re-reference the EEG to a mastoid channel.  Default ``False``.
      m : str, optional
          Mastoid channel for single-channel re-referencing (required when
          *do_reref* is ``True`` and *s* is set).
      m1 : str, optional
          First mastoid for two-channel re-referencing.
      m2 : str, optional
          Second mastoid for two-channel re-referencing.
      lights_off : str, optional
          Lights-off time ``'HH:MM:SS'`` or ``'.'`` if unknown.
          Default ``'.'``.
      lights_on : str, optional
          Lights-on time ``'HH:MM:SS'`` or ``'.'`` if unknown.
          Default ``'.'``.
      ignore_obs : bool, optional
          Ignore observed (manual) staging annotations.  Default ``False``.
      args : str, optional
          Additional options to append to the ``POPS`` command.
          Default ``''``.

      Returns
      -------
      pandas.DataFrame or str
          Per-epoch staging results from the ``POPS: E`` table, or an
          error string if the resource path cannot be opened.
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
      return self.table( 'POPS' , 'E' )


   # --------------------------------------------------------------------------------

   def predict_SUN2019( self, cen , age = None , th = '3' , path = None ):
      """Run the SUN2019 EEG-based brain-age prediction model for this individual.

      Parameters
      ----------
      cen : str or list of str
          EEG centroid channel label(s).  A list is joined with commas.
      age : float or str
          Chronological age (years) for this individual.  Required.
      th : str or int, optional
          Outlier threshold in standard deviations.  Default ``'3'``.
      path : str, optional
          Path to the Luna models folder.  Defaults to
          ``resources.MODEL_PATH``.

      Returns
      -------
      pandas.DataFrame
          Prediction results from the ``PREDICT`` command.
      """
      if path is None: path = resources.MODEL_PATH
      if type( cen ) is list : cen = ','.join( cen )

      # set i-vars
      if age is None:
         print( 'need to set age indiv-var' )
         return
      self.var( 'age' , str(age) )
      self.var( 'cen' , cen )
      self.var( 'mpath' , path )
      self.var( 'th' , str(th) )
      self.eval( cmdfile( resources.MODEL_PATH + '/m1-adult-age-luna.txt' ) )
      return self.table( 'PREDICT' )

   # --------------------------------------------------------------------------------

   def stages(self):
      """Return a DataFrame of per-epoch sleep stage assignments.

      Runs the Luna ``STAGE`` command silently and extracts the
      ``STAGE: E`` result table.

      Returns
      -------
      pandas.DataFrame or None
          Table with one row per epoch and a ``STAGE`` column, or
          ``None`` if no staging annotations are present.
      """
      hyp = self.silent_proc( "STAGE" )
      if type(hyp) is type(None): return
      if 'STAGE: E' in hyp:
         return hyp[ 'STAGE: E' ]
      return

   # --------------------------------------------------------------------------------

   def hypno(self):
      """Plot a hypnogram of the sleep stages for this individual.

      Requires that staging annotations are already attached.

      Returns
      -------
      object
          Return value from :func:`lunapi.viz.hypno` (typically a
          Plotly figure).
      """
      if self.has_staging() is not True:
         print( "no staging attached" )
         return
      return hypno( self.stages()[ 'STAGE' ] )

   # --------------------------------------------------------------------------------

   def has_staging(self):
      """Return whether sleep staging annotations are present for this instance.

      Returns
      -------
      bool
          ``True`` if staging annotations are attached; ``False`` otherwise.
      """
      _proj = proj(False)
      silence_mode = _proj.is_silenced()
      _proj.silence(True,False)
      res = self.edf.has_staging()
      _proj.silence( silence_mode , False )
      return res

   # --------------------------------------------------------------------------------

   def has_annots(self,anns):
      """Return a boolean vector indicating which annotation classes are present.

      Parameters
      ----------
      anns : str or list of str
          One or more annotation class names to check.

      Returns
      -------
      list of bool
          One element per entry in *anns*: ``True`` if that class exists.
      """
      if anns is None: return
      if type( anns ) is not list: anns = [ anns ]
      return self.edf.has_annots( anns )

   # --------------------------------------------------------------------------------

   def has_annot(self,anns):
      """Return a boolean vector indicating which annotation classes are present.

      Alias for :meth:`has_annots`.

      Parameters
      ----------
      anns : str or list of str
          One or more annotation class names to check.

      Returns
      -------
      list of bool
          One element per entry in *anns*: ``True`` if that class exists.
      """
      return self.has_annots(anns)

   # --------------------------------------------------------------------------------

   def has_channels(self,ch):
      """Return a boolean vector indicating which channels are present.

      Parameters
      ----------
      ch : str or list of str
          One or more channel labels to check.

      Returns
      -------
      list of bool
          One element per entry in *ch*: ``True`` if that channel exists.
      """
      if ch is None: return
      if type(ch) is not list: ch = [ ch ]
      return self.edf.has_channels( ch )

   # --------------------------------------------------------------------------------

   def has(self,ch):
      """Return a boolean vector indicating which channels are present.

      Alias for :meth:`has_channels`.

      Parameters
      ----------
      ch : str or list of str
          One or more channel labels to check.

      Returns
      -------
      list of bool
          One element per entry in *ch*: ``True`` if that channel exists.
      """
      if ch is None: return
      if type(ch) is not list: ch = [ ch ]
      return self.edf.has_channels( ch )

   # --------------------------------------------------------------------------------
#   def psd(self, ch, minf = None, maxf = 25, minp = None, maxp = None , xlines = None , ylines = None ):
#      """Spectrogram plot for a given channel 'ch'"""
#      if type( ch ) is not str: return
#      if all( self.has( ch ) ) is not True: return
#      res = self.silent_proc( 'PSD spectrum dB max=' + str(maxf) + ' sig=' + ','.join(ch) )[ 'PSD: CH_F' ]
#      return psd( res , ch, minf = minf, maxf = maxf, minp = minp, maxp = maxp , xlines = xlines , ylines = ylines )

   # --------------------------------------------------------------------------------

   def psd( self, ch, var = 'PSD' , minf = None, maxf = 25, minp = None, maxp = None , xlines = None , ylines = None ):
      """Plot the power spectral density for one or more channels.

      Runs the Luna ``PSD`` (default) or ``MTM`` command and renders the
      result via :func:`lunapi.viz.psd`.

      Parameters
      ----------
      ch : str or list of str
          Channel label(s) to plot.
      var : str, optional
          Spectral estimator to use: ``'PSD'`` (Welch) or ``'MTM'``
          (multitaper).  Default ``'PSD'``.
      minf : float, optional
          Minimum frequency (Hz) for the x-axis.  Default ``None``
          (use estimator minimum).
      maxf : float, optional
          Maximum frequency (Hz) for the x-axis and Luna command.
          Default ``25``.
      minp : float, optional
          Minimum power for the y-axis.  Default ``None`` (auto-scale).
      maxp : float, optional
          Maximum power for the y-axis.  Default ``None`` (auto-scale).
      xlines : list of float, optional
          Vertical reference lines at these frequencies.
      ylines : list of float, optional
          Horizontal reference lines at these power values.

      Returns
      -------
      None
          The plot is rendered inline.
      """
      if ch is None: return
      if type(ch) is not list: ch = [ ch ]

      if var == 'PSD':
         res = self.silent_proc( 'PSD spectrum dB max=' + str(maxf) + ' sig=' + ','.join(ch) )
         df = res[ 'PSD: CH_F' ]
      else:
         res = self.silent_proc( 'MTM tw=15 dB max=' + str(maxf) + ' sig=' + ','.join(ch) )
         df = res[ 'MTM: CH_F' ]

      psd( df = df , ch = ch , var = var ,
           minf = minf , maxf = maxf , minp = minp , maxp = maxp ,
           xlines = xlines , ylines = ylines )


   # --------------------------------------------------------------------------------
#   def spec( self, ch, var = 'PSD' , mine = None, maxe = None, minf = None, maxf = 25 , w = 0.025 ):
#      """Generates an epoch-level PSD spectrogram (from PSD or MTM)"""
#      if ch is None: return
#      if type(ch) is not list: ch = [ ch ]
#
#      if var == 'PSD':
#         self.eval( 'PSD epoch-spectrum dB max=' + str(maxf) + ' sig=' + ','.join(ch) )
#         df = self.table( 'PSD' , 'CH_E_F' )
#      else:
#         self.eval( 'MTM epoch-spectra epoch epoch-output dB tw=15 max=' + str(maxf) + ' sig=' + ','.join(ch) )
#         df = self.table( 'MTM' , 'CH_E_F' )
#
#      spec( df = df , ch = None , var = var ,
#            mine = mine , maxe = maxe , minf = minf , maxf = maxf , w = w )

   # --------------------------------------------------------------------------------

   def spec(self,ch,mine = None , maxe = None , minf = None, maxf = None, w = 0.025 ):
      """Plot an epoch-by-frequency PSD spectrogram for a single channel.

      Runs Luna ``PSD epoch-spectrum`` silently and renders the result via
      :func:`lunapi.viz.spec`.

      Parameters
      ----------
      ch : str
          Channel label (single channel).
      mine : int, optional
          First epoch to include.  Default ``None`` (all epochs).
      maxe : int, optional
          Last epoch to include.  Default ``None`` (all epochs).
      minf : float, optional
          Minimum frequency (Hz).  Default ``0.5``.
      maxf : float, optional
          Maximum frequency (Hz).  Default ``25``.
      w : float, optional
          Winsorisation proportion applied to power values.
          Default ``0.025``.

      Returns
      -------
      object
          Return value from :func:`lunapi.viz.spec`.
      """
      if type( ch ) is not str:
         return
      if all( self.has( ch ) ) is not True:
         return
      if minf is None:
         minf=0.5
      if maxf is None:
         maxf=25
      res = self.silent_proc( "PSD epoch-spectrum dB sig="+ch+" min="+str(minf)+" max="+str(maxf) )[ 'PSD: CH_E_F' ]
      return spec( res , ch=ch, var='PSD', mine=mine,maxe=maxe,minf=minf,maxf=maxf,w=w)


__all__ = ["inst"]
