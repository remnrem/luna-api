"""Segment-service API.

Exports:

- :class:`segsrv` for efficient windowed signal/annotation access
- :func:`stgcol` and :func:`stgn` for sleep-stage plotting helpers
"""

import lunapi.lunapi0 as _luna

from .instance import inst


def stgcol(ss):
   """Map a sleep stage label to its canonical hex display colour.

   Thin proxy to :func:`lunapi.viz.stgcol`.

   Parameters
   ----------
   ss : str
       Sleep stage label (e.g. ``'N1'``, ``'N2'``, ``'N3'``, ``'R'``,
       ``'W'``).

   Returns
   -------
   str
       Hex colour string (e.g. ``'#0050C8FF'``).
   """
   from .viz import stgcol as _stgcol
   return _stgcol(ss)


def stgn(ss):
   """Map a sleep stage label to its canonical numeric code.

   Thin proxy to :func:`lunapi.viz.stgn`.

   Parameters
   ----------
   ss : str
       Sleep stage label (e.g. ``'N1'``, ``'R'``, ``'W'``).

   Returns
   -------
   int
       Numeric sleep stage code used internally (e.g. for hypnogram
       rendering).
   """
   from .viz import stgn as _stgn
   return _stgn(ss)


class segsrv:
   """Windowed signal and annotation server for interactive EDF viewing.

   :class:`segsrv` wraps the C++ ``segsrv_t`` backend, which pre-caches a
   set of EDF signals and annotations in memory so that interactive viewers
   (e.g. :func:`lunapi.viz.scope`) can read arbitrary windows efficiently
   without re-querying the EDF on every update.

   Typical workflow::

       s = segsrv(individual)          # individual is an inst object
       s.populate(chs=['EEG', 'EOG'])  # load channels into cache
       s.set_epoch_size(30)
       s.window(0, 30)                 # view first epoch
       signal = s.get_signal('EEG')

   Parameters
   ----------
   p : lunapi.instance.inst
       The :class:`~lunapi.instance.inst` whose data will be served.
   """

   def __init__(self,p):
      assert isinstance(p,inst)
      self.p = p
      self.segsrv = _luna.segsrv(p.edf)

   def populate(self,chs=None,anns=None,max_sr=None):
      """Load signals and annotations into the segment cache.

      Must be called before any windowed data retrieval.  Only channels
      and annotation classes listed here will be available for subsequent
      queries.

      Parameters
      ----------
      chs : str or list of str, optional
          Channel labels to load.  Defaults to all channels present in
          the EDF.
      anns : str or list of str, optional
          Annotation class names to load.  Defaults to all annotation
          classes present.
      max_sr : int, optional
          If provided, down-sample any channel whose sample rate exceeds
          *max_sr* Hz before caching.

      Returns
      -------
      None
      """
      if chs is None: chs = self.p.edf.channels()
      if anns is None: anns = self.p.edf.annots()
      if type(chs) is not list: chs = [ chs ]
      if type(anns) is not list: anns = [ anns ]
      if type(max_sr) is int: self.segsrv.input_throttle( max_sr )
      self.segsrv.populate( chs , anns )

   def window(self,a,b):
      """Set the active viewing window.

      Parameters
      ----------
      a : float
          Window start in seconds (elapsed time from EDF start).
      b : float
          Window stop in seconds.

      Returns
      -------
      None
      """
      assert isinstance(a, (int, float) )
      assert isinstance(b, (int, float) )
      self.segsrv.set_window( a, b )

   def get_signal(self,ch):
      """Return raw (possibly filtered) signal values within the current window.

      Parameters
      ----------
      ch : str
          Channel label to retrieve.

      Returns
      -------
      numpy.ndarray
          1-D array of sample values for the current window.
      """
      assert isinstance(ch, str )
      return self.segsrv.get_signal( ch )

   def get_timetrack(self,ch):
      """Return the time axis for a cached channel within the current window.

      Parameters
      ----------
      ch : str
          Channel label.

      Returns
      -------
      numpy.ndarray
          1-D array of time values in seconds corresponding to each
          sample returned by :meth:`get_signal`.
      """
      assert isinstance(ch, str )
      return self.segsrv.get_timetrack( ch )

   def get_time_scale(self):
      """Return the effective time-scaling metadata from the backend.

      Returns
      -------
      object
          Time-scale descriptor returned by the C++ segment server.
      """
      return self.segsrv.get_time_scale()

   def get_gaps(self):
      """Return discontinuity (gap) intervals in clock-time seconds.

      Returns
      -------
      list of tuple
          ``[(start_sec, stop_sec), ...]`` for each gap in the recording,
          or an empty list if the EDF is contiguous.
      """
      return self.segsrv.get_gaps()


   def apply_filter(self,ch,sos):
      """Apply a second-order-sections (SOS) filter to a cached channel.

      The filtered signal replaces the raw cache for that channel until
      :meth:`clear_filter` is called.

      Parameters
      ----------
      ch : str
          Channel label to filter.
      sos : array-like
          SOS filter coefficients as produced by
          ``scipy.signal.butter(..., output='sos')``.

      Returns
      -------
      None
      """
      return self.segsrv.apply_filter(ch,sos)

   def clear_filter(self,ch):
      """Remove an active filter from a channel, restoring the raw cache.

      Parameters
      ----------
      ch : str
          Channel label whose filter should be cleared.

      Returns
      -------
      None
      """
      return self.segsrv.clear_filter(ch)

   def clear_filters(self):
      """Remove all active channel filters, restoring raw cached signals.

      Returns
      -------
      None
      """
      return self.segsrv.clear_filters()

   def set_scaling(self, nchs, nanns = 0 , yscale = 1 , ygroup = 1 , yheader = 0.05 , yfooter = 0.05 , scaling_fixed_annot = 0.1 , clip = True):
      """Configure vertical layout and scaling for the signal display.

      Parameters
      ----------
      nchs : int
          Number of signal channels to lay out.
      nanns : int, optional
          Number of annotation tracks.  Default ``0``.
      yscale : float, optional
          Global y-axis scale multiplier.  Default ``1``.
      ygroup : float, optional
          Fraction of the y-axis height allocated to the signal group.
          Default ``1``.
      yheader : float, optional
          Fraction of the y-axis reserved for the header.  Default
          ``0.05``.
      yfooter : float, optional
          Fraction of the y-axis reserved for the footer.  Default
          ``0.05``.
      scaling_fixed_annot : float, optional
          Fixed height fraction for each annotation track.  Default
          ``0.1``.
      clip : bool, optional
          Whether to clip signal values that exceed the display bounds.
          Default ``True``.

      Returns
      -------
      None
      """
      self.segsrv.set_scaling( nchs, nanns, yscale, ygroup, yheader, yfooter, scaling_fixed_annot , clip )

   def get_scaled_signal(self, ch, n1):
      """Return y-scaled signal samples for display row *n1*.

      Parameters
      ----------
      ch : str
          Channel label.
      n1 : int
          0-based display row index.

      Returns
      -------
      numpy.ndarray
          Scaled sample values mapped into the normalised ``[0, 1]``
          y-axis coordinate for row *n1*.
      """
      return self.segsrv.get_scaled_signal( ch , n1 )

   def get_scaled_y(self, ch, y):
      """Transform a physical amplitude value to a normalised display y-coordinate.

      Parameters
      ----------
      ch : str
          Channel label.
      y : float
          Physical amplitude value (in the channel's native units).

      Returns
      -------
      float
          Corresponding normalised y-coordinate in ``[0, 1]``.
      """
      return self.segsrv.get_scaled_y( ch , y)

   def fix_physical_scale(self,ch,lwr,upr):
      """Pin a channel's display range to fixed physical bounds.

      Overrides the auto-derived empirical scale for *ch* so that the
      viewer always uses [*lwr*, *upr*] regardless of the signal content.

      Parameters
      ----------
      ch : str
          Channel label.
      lwr : float
          Lower bound in the channel's physical units.
      upr : float
          Upper bound in the channel's physical units.

      Returns
      -------
      None
      """
      self.segsrv.fix_physical_scale( ch, lwr, upr )

   def empirical_physical_scale(self,ch):
      """Reset a channel to its backend-derived empirical display bounds.

      Parameters
      ----------
      ch : str
          Channel label.

      Returns
      -------
      object
          Updated scale descriptor returned by the C++ backend.
      """
      self.segsrv.empirical_physical_scale( ch )

   def free_physical_scale( self, ch ):
      """Remove any fixed physical scale bounds for a channel.

      After calling this, the display range reverts to auto-scaling based
      on the current window contents.

      Parameters
      ----------
      ch : str
          Channel label.

      Returns
      -------
      None
      """
      self.segsrv.free_physical_scale( ch )

   # sigmods

   def make_sigmod( self, mod_label, mod_ch, mod_type, sr, order, lwr, upr ):
      """Create a signal modifier using a Butterworth band-pass filter.

      Computes SOS coefficients via ``scipy.signal.butter`` and registers
      the modifier with the backend.

      Parameters
      ----------
      mod_label : str
          Unique name for this modifier (used to reference it later).
      mod_ch : str
          Source channel label to apply the filter to.
      mod_type : str
          Modifier type string passed to the backend (e.g. ``'bandpass'``).
      sr : float
          Sample rate of *mod_ch* in Hz (used by the filter design).
      order : int
          Butterworth filter order.
      lwr : float
          Lower cutoff frequency in Hz.
      upr : float
          Upper cutoff frequency in Hz.

      Returns
      -------
      None
      """
      from scipy.signal import butter
      sos = butter( order , [ lwr, upr ] , btype='band', fs=sr, output='sos' )
      self.segsrv.make_sigmod( mod_label, mod_ch, mod_type, sos.reshape(-1) )

   def make_sigmod_sos( self, mod_label, mod_ch, mod_type, sos ):
      """Create a signal modifier from an existing SOS coefficient vector.

      Parameters
      ----------
      mod_label : str
          Unique modifier name.
      mod_ch : str
          Source channel label.
      mod_type : str
          Modifier type string.
      sos : array-like
          Pre-computed SOS filter coefficients (flattened to 1-D).

      Returns
      -------
      None
      """
      self.segsrv.make_sigmod( mod_label, mod_ch, mod_type, sos )

   def make_sigmod_raw( self, mod_label, mod_ch, mod_type  ):
      """Create a pass-through (unfiltered) signal modifier slot.

      Parameters
      ----------
      mod_label : str
          Unique modifier name.
      mod_ch : str
          Source channel label.
      mod_type : str
          Modifier type string (stored for reference; signal is passed
          through unchanged).

      Returns
      -------
      None
      """
      self.segsrv.make_sigmod( mod_label, mod_ch, mod_type , [ ] )

   def apply_sigmod( self, mod_label, mod_ch, slot ):
      """Apply a registered signal modifier to a display slot.

      Parameters
      ----------
      mod_label : str
          Name of a modifier previously created with :meth:`make_sigmod`,
          :meth:`make_sigmod_sos`, or :meth:`make_sigmod_raw`.
      mod_ch : str
          Source channel label.
      slot : int
          Display slot index to which the modifier output will be
          assigned.

      Returns
      -------
      None
      """
      self.segsrv.apply_sigmod( mod_label, mod_ch, slot )

   def get_sigmod_timetrack( self, bin ):
      """Return the time axis for a signal-modifier output bin.

      Parameters
      ----------
      bin : int
          Bin (output slot) index.

      Returns
      -------
      numpy.ndarray
          Time values in seconds for the modifier output samples.
      """
      return self.segsrv.get_sigmod_timetrack( bin )

   def get_sigmod_scaled_signal( self, bin ):
      """Return scaled samples for a signal-modifier output bin.

      Parameters
      ----------
      bin : int
          Bin (output slot) index.

      Returns
      -------
      numpy.ndarray
          Scaled amplitude values for the current window.
      """
      return self.segsrv.get_sigmod_scaled_signal( bin )

   # epochs

   def set_epoch_size( self, s ):
      """Set the epoch duration used by the segment server.

      Parameters
      ----------
      s : float
          Epoch length in seconds (e.g. ``30``).

      Returns
      -------
      None
      """
      self.segsrv.set_epoch_size( s )

   def get_epoch_size( self):
      """Return the current epoch duration in seconds.

      Returns
      -------
      float
          Epoch length in seconds.
      """
      return self.segsrv.get_epoch_size()

#   def get_epoch_timetrack(self):
#      return self.segsrv.get_epoch_timetrack()

   def num_epochs( self) :
      """Return the total number of epochs at the current epoch size.

      Returns
      -------
      int
          Number of complete epochs in the recording.
      """
      return self.segsrv.nepochs()

#   def num_seconds( self ):
#      return self.segsrv.get_ungapped_total_sec()

   def num_seconds_clocktime( self ):
      """Return the clock-time duration of the recording in seconds.

      Returns
      -------
      float
          Total clock-time duration in seconds (after any internal
          resampling or masking).
      """
      return self.segsrv.get_total_sec()

   def num_seconds_clocktime_original( self ):
      """Return the original (unmodified) clock-time duration in seconds.

      Returns
      -------
      float
          Total clock-time duration of the EDF as originally loaded.
      """
      return self.segsrv.get_total_sec_original()

   def calc_bands( self, chs ):
      """Pre-compute spectral band summaries for one or more channels.

      Results are stored internally and retrieved with :meth:`get_bands`.

      Parameters
      ----------
      chs : str or list of str
          Channel label(s) for which to compute band power.

      Returns
      -------
      None
      """
      if type( chs ) is not list: chs = [ chs ]
      self.segsrv.calc_bands( chs );

   def calc_hjorths( self, chs ):
      """Pre-compute Hjorth parameters for one or more channels.

      Hjorth parameters (activity, mobility, complexity) are computed
      per epoch and stored internally.  Retrieve with :meth:`get_hjorths`.

      Parameters
      ----------
      chs : str or list of str
          Channel label(s) for which to compute Hjorth parameters.

      Returns
      -------
      None
      """
      if type( chs ) is not list: chs = [ chs ]
      self.segsrv.calc_hjorths( chs );

   def get_bands( self, ch ):
      """Return the pre-computed band-power matrix for a channel.

      Requires a prior call to :meth:`calc_bands` for *ch*.

      Parameters
      ----------
      ch : str
          Channel label.

      Returns
      -------
      numpy.ndarray
          2-D matrix with one row per epoch and columns for each spectral
          band.
      """
      return self.segsrv.get_bands( ch )

   def get_hjorths( self, ch ):
      """Return the pre-computed Hjorth parameter matrix for a channel.

      Requires a prior call to :meth:`calc_hjorths` for *ch*.

      Parameters
      ----------
      ch : str
          Channel label.

      Returns
      -------
      numpy.ndarray
          2-D matrix with one row per epoch and three columns
          (activity, mobility, complexity).
      """
      return self.segsrv.get_hjorths( ch )

   def valid_window( self ):
      """Return whether the current window overlaps valid (non-gap) data.

      Returns
      -------
      bool
          ``True`` if the window is valid for rendering; ``False``
          otherwise.
      """
      return self.segsrv.is_window_valid()

   def is_clocktime( self ):
      """Return whether this instance uses absolute clock-time semantics.

      Returns
      -------
      bool
          ``True`` if the EDF uses absolute clock time (real wall-clock
          start time); ``False`` for relative time.
      """
      return self.segsrv.is_clocktime()

   def get_window_left( self ):
      """Return the left edge of the current viewing window in seconds.

      Returns
      -------
      float
          Window start in elapsed seconds from the EDF start.
      """
      return self.segsrv.get_window_left()

   def get_window_right( self ):
      """Return the right edge of the current viewing window in seconds.

      Returns
      -------
      float
          Window stop in elapsed seconds from the EDF start.
      """
      return self.segsrv.get_window_right()

   def get_window_left_hms( self ):
      """Return the left edge of the current window as a clock-time string.

      Returns
      -------
      str
          Window start as ``'HH:MM:SS'``.
      """
      return self.segsrv.get_window_left_hms()

   def get_window_right_hms( self ):
      """Return the right edge of the current window as a clock-time string.

      Returns
      -------
      str
          Window stop as ``'HH:MM:SS'``.
      """
      return self.segsrv.get_window_right_hms()

   def get_clock_ticks( self , n = 6 , multiday = False ):
      """Return formatted clock-time tick labels for the current window.

      Parameters
      ----------
      n : int, optional
          Maximum number of ticks to return.  Default ``6``.
      multiday : bool, optional
          If ``True``, include day information in the tick labels.
          Default ``False``.

      Returns
      -------
      list
          Up to *n* ``(position_sec, label_str)`` pairs suitable for
          axis tick placement.
      """
      assert type( n ) is int
      return self.segsrv.get_clock_ticks( n , multiday )

   def get_hour_ticks( self ):
      """Return hour-boundary tick positions for the full recording timeline.

      Returns
      -------
      list
          ``(position_sec, label_str)`` pairs at each whole-hour boundary.
      """
      return self.segsrv.get_hour_ticks()

   def get_window_phys_range( self , ch ):
      """Return the physical min/max of a channel within the current window.

      Parameters
      ----------
      ch : str
          Channel label.

      Returns
      -------
      tuple
          ``(min_value, max_value)`` in the channel's physical units.
      """
      assert type(ch) is str
      return self.segsrv.get_window_phys_range( ch )

   def get_ylabel( self , n ):
      """Return the normalised y-axis anchor position for display row *n*.

      Parameters
      ----------
      n : int
          0-based display row index.

      Returns
      -------
      float
          Normalised y-coordinate in ``[0, 1]`` for the centre of row *n*.
      """
      assert type(n) is int
      return self.segsrv.get_ylabel( n )

   def throttle(self,n):
      """Limit the number of output samples returned per window (for rendering).

      Parameters
      ----------
      n : int
          Maximum number of samples to return per channel per window
          query.

      Returns
      -------
      None
      """
      assert type(n) is int
      self.segsrv.throttle(n)

   def input_throttle(self,n):
      """Set a sample-rate cap applied when populating the cache.

      Must be called before :meth:`populate`.

      Parameters
      ----------
      n : int
          Maximum sample rate (Hz) to accept when loading channels.
          Channels above this rate will be down-sampled.

      Returns
      -------
      None
      """
      assert type(n) is int
      self.segsrv.input_throttle(n)

   def summary_threshold_mins(self,m):
      """Set the summary aggregation threshold in minutes.

      Parameters
      ----------
      m : int or float
          Threshold in minutes used by the backend's epoch-level
          summary aggregation.

      Returns
      -------
      None
      """
      assert type(m) is int or type(m) is float
      self.segsrv.summary_threshold_mins(m)

   def get_annots(self):
      """Return the annotation events within the current window.

      Returns
      -------
      list
          List of ``(class, start_sec, stop_sec)`` tuples for all
          annotation events that overlap the current viewing window.
      """
      return self.segsrv.fetch_annots()

   def get_all_annots(self,anns,hms = False ):
      """Return all events for the specified annotation classes.

      Parameters
      ----------
      anns : str or list of str
          Annotation class name(s) to retrieve.
      hms : bool, optional
          If ``True``, return times as ``'HH:MM:SS'`` strings rather than
          floats.  Default ``False``.

      Returns
      -------
      list
          All events for the requested classes across the full recording.
      """
      return self.segsrv.fetch_all_annots(anns, hms )

   def get_all_annots_with_inst_ids(self, anns, hms=False):
      """Return all annotation events with instance IDs and exact timepoints.

      Parameters
      ----------
      anns : str or list of str
          Annotation class name(s) to retrieve.
      hms : bool, optional
          If ``True``, include an ``'HH:MM:SS'`` clock-time column.
          Default ``False``.

      Returns
      -------
      list of list of str
          Each row contains (hms=False)::

              [class, meta, start_sec, stop_sec, start_tp, stop_tp, inst_id, ch_str]
                 0      1      2          3          4          5       6        7

          or (hms=True)::

              [class, meta, hms, start_sec, duration, start_tp, stop_tp, inst_id, ch_str]
                 0      1    2      3          4         5          6       7        8

          ``start_tp`` and ``stop_tp`` are exact uint64_t timepoint values
          as strings; pass them (as ``int(row[4])``, ``int(row[5])``) to
          :meth:`delete_annot` or :meth:`edit_annot` for lossless round-trips.
      """
      if type(anns) is not list: anns = [anns]
      return self.segsrv.fetch_all_annots_with_inst_ids(anns, hms)

   def compile_windowed_annots(self,anns):
      """Pre-compile annotation classes into window-ready polygon caches.

      Must be called before using :meth:`get_annots_xaxes` or
      :meth:`get_annots_yaxes`.  Only the classes listed here will be
      available for polygon-based rendering.

      Parameters
      ----------
      anns : str or list of str
          Annotation class name(s) to compile.

      Returns
      -------
      None
      """
      self.segsrv.compile_evts( anns )

   def set_clip_xaxes(self,clip):
      """Enable or disable x-axis clipping when drawing annotation polygons.

      Parameters
      ----------
      clip : bool
          If ``True``, annotation polygons are clipped to the current
          window boundaries.

      Returns
      -------
      None
      """
      self.segsrv.set_clip_xaxes( clip )

   def get_annots_xaxes(self,ann):
      """Return x-axis polygon coordinates for annotation class *ann*.

      Requires a prior call to :meth:`compile_windowed_annots`.

      Parameters
      ----------
      ann : str
          Annotation class name.

      Returns
      -------
      list
          X-coordinate arrays for each annotation polygon in the current
          window.
      """
      return self.segsrv.get_evnts_xaxes( ann )

   def get_annots_yaxes(self,ann):
      """Return y-axis polygon coordinates for annotation class *ann*.

      Requires a prior call to :meth:`compile_windowed_annots`.

      Parameters
      ----------
      ann : str
          Annotation class name.

      Returns
      -------
      list
          Y-coordinate arrays for each annotation polygon in the current
          window.
      """
      return self.segsrv.get_evnts_yaxes( ann )

   def set_annot_format6(self,b):
      """Toggle 6-point polygon format for annotation rendering.

      Parameters
      ----------
      b : bool
          If ``True``, use the 6-point (trapezoid) format; otherwise use
          the default rectangle format.

      Returns
      -------
      None
      """
      self.segsrv.set_evnt_format6(b)

   def get_annots_xaxes_ends(self,ann):
      """Return end-cap x-coordinates for annotation polygons.

      Parameters
      ----------
      ann : str
          Annotation class name.

      Returns
      -------
      list
          End-cap x-coordinate arrays for the current window.
      """
      return self.segsrv.get_evnts_xaxes_ends( ann )

   def get_annots_yaxes_ends(self,ann):
      """Return end-cap y-coordinates for annotation polygons.

      Parameters
      ----------
      ann : str
          Annotation class name.

      Returns
      -------
      list
          End-cap y-coordinate arrays for the current window.
      """
      return self.segsrv.get_evnts_yaxes_ends( ann )

   # -----------------------------------------------------------------------
   # Annotation editing
   # -----------------------------------------------------------------------

   def delete_annot(self, aclass, inst_id, start_tp, stop_tp, ch_str=""):
      """Queue deletion of a single annotation instance.

      The deletion is not applied until :meth:`apply_annot_edits` is called.

      Parameters
      ----------
      aclass : str
          Annotation class name (col 0 from :meth:`get_all_annots_with_inst_ids`).
      inst_id : str
          Instance ID string (col 6).
      start_tp : int
          Exact start timepoint in tp units (col 4, cast to ``int``).
      stop_tp : int
          Exact stop timepoint in tp units (col 5, cast to ``int``).
      ch_str : str, optional
          Channel string (col 7).  Default ``""``.
      """
      e = _luna.annot_edit()
      e.aclass    = aclass
      e.inst_id   = inst_id
      e.start_tp  = int(start_tp)
      e.stop_tp   = int(stop_tp)
      e.ch_str    = ch_str
      e.del_      = True
      self.segsrv.queue_edit(e)

   def edit_annot(self, aclass, inst_id, start_tp, stop_tp, ch_str="",
                  new_start=None, new_stop=None, new_ch=None, new_inst_id=None,
                  clear_meta=False, meta=None):
      """Queue a modification of a single annotation instance.

      Any combination of action parameters may be supplied; unset ones
      leave the original value unchanged.  The edit is not applied until
      :meth:`apply_annot_edits` is called.  *aclass* is the only immutable
      field; all others including *inst_id* can be changed.

      Parameters
      ----------
      aclass : str
          Annotation class name (immutable).
      inst_id : str
          Instance ID string (current value, used to locate the instance).
      start_tp : int
          Exact start timepoint in tp units (from :meth:`get_all_annots_with_inst_ids`).
      stop_tp : int
          Exact stop timepoint in tp units.
      ch_str : str, optional
          Channel string.  Default ``""``.
      new_start : int, optional
          New start timepoint (tp units).  If set without *new_stop*, the
          interval is shifted preserving its original duration.
      new_stop : int, optional
          New stop timepoint (tp units).
      new_ch : str, optional
          New channel string.
      new_inst_id : str, optional
          New instance ID.
      clear_meta : bool, optional
          If ``True``, wipe all existing metadata before applying *meta*
          updates.  Default ``False``.
      meta : dict, optional
          ``{key: value}`` string pairs to set or override on the instance.
      """
      e = _luna.annot_edit()
      e.aclass     = aclass
      e.inst_id    = inst_id
      e.start_tp   = int(start_tp)
      e.stop_tp    = int(stop_tp)
      e.ch_str     = ch_str
      if new_start   is not None: e.new_start   = int(new_start)
      if new_stop    is not None: e.new_stop    = int(new_stop)
      if new_ch      is not None: e.new_ch      = str(new_ch)
      if new_inst_id is not None: e.new_inst_id = str(new_inst_id)
      e.clear_meta = clear_meta
      if meta        is not None: e.meta        = {str(k): str(v) for k, v in meta.items()}
      self.segsrv.queue_edit(e)

   def apply_annot_edits(self, classes=None):
      """Apply all queued annotation edits and refresh the display cache.

      After applying, the queue is cleared automatically.

      Parameters
      ----------
      classes : str or list of str, optional
          Restrict application to these annotation class names.  Pass
          ``None`` (default) to apply to all classes that have queued edits.

      Returns
      -------
      int
          Number of instances changed or deleted.
      """
      if classes is None:
         classes = []
      elif type(classes) is str:
         classes = [classes]
      return self.segsrv.apply_annot_edits(classes)

   def clear_annot_edits(self):
      """Discard all queued annotation edits without applying them.

      Returns
      -------
      None
      """
      self.segsrv.clear_edits()

   def set_psd_mode(self, on):
      """Enable or disable on-the-fly PSD computation inside get_scaled_signal().

      When enabled, each call to get_scaled_signal() also computes and caches
      a Welch PSD for that channel at native sample rate.

      Parameters
      ----------
      on : bool
          True to enable PSD computation, False to disable.
      """
      self.segsrv.set_psd_mode(on)

   def get_psd_mode(self):
      """Return True if PSD mode is currently enabled."""
      return self.segsrv.get_psd_mode()

   def get_psd_freqs(self, ch):
      """Return the cached PSD frequency axis (Hz) for channel ch.

      Must call get_scaled_signal() with PSD mode on first.

      Parameters
      ----------
      ch : str
          Channel name.

      Returns
      -------
      array-like
          Frequency values in Hz.
      """
      return self.segsrv.get_psd_freqs(ch)

   def get_psd_power(self, ch):
      """Return the cached PSD power values for channel ch.

      Must call get_scaled_signal() with PSD mode on first.

      Parameters
      ----------
      ch : str
          Channel name.

      Returns
      -------
      array-like
          Power spectral density values.
      """
      return self.segsrv.get_psd_power(ch)

__all__ = ["segsrv", "stgcol", "stgn"]
