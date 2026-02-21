"""Segment-service API.

Exports:

- :class:`segsrv` for efficient windowed signal/annotation access
- :func:`stgcol` and :func:`stgn` for sleep-stage plotting helpers
"""

import lunapi.lunapi0 as _luna
from scipy.signal import butter

from .instance import inst


def stgcol(ss):
   """Proxy to :func:`lunapi.viz.stgcol`.
      
      Parameters
      ----------
      ss : object\n        Input argument `ss`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   from .viz import stgcol as _stgcol
   return _stgcol(ss)


def stgn(ss):
   """Proxy to :func:`lunapi.viz.stgn`.
      
      Parameters
      ----------
      ss : object\n        Input argument `ss`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   from .viz import stgn as _stgn
   return _stgn(ss)


class segsrv:
   """Segment server instance"""

   def __init__(self,p):
      assert isinstance(p,inst)
      self.p = p
      self.segsrv = _luna.segsrv(p.edf)
      
   def populate(self,chs=None,anns=None,max_sr=None):
      """Populate cached signals/annotations used by interactive viewers.
         
         Parameters
         ----------
         chs : list of str or str, optional
             Channels to load. Defaults to all channels.
         anns : list of str or str, optional
             Annotation classes to load. Defaults to all annotations.
         max_sr : int, optional
             Optional input sample-rate throttle.
         
         Returns
         -------
         None
                 No value is returned.
      """
      if chs is None: chs = self.p.edf.channels()
      if anns is None: anns = self.p.edf.annots()
      if type(chs) is not list: chs = [ chs ]
      if type(anns) is not list: anns = [ anns ]
      if type(max_sr) is int: self.segsrv.input_throttle( max_sr )
      self.segsrv.populate( chs , anns )

   def window(self,a,b):
      """Set the active viewing window in seconds.
         
         Parameters
         ----------
         a : object\n        Input argument `a`.
         b : object\n        Input argument `b`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      assert isinstance(a, (int, float) )
      assert isinstance(b, (int, float) )
      self.segsrv.set_window( a, b )
      
   def get_signal(self,ch):
      """Return raw signal values for a channel in the cached data.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      assert isinstance(ch, str )
      return self.segsrv.get_signal( ch )

   def get_timetrack(self,ch):
      """Return absolute time coordinates for a cached channel.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      assert isinstance(ch, str )
      return self.segsrv.get_timetrack( ch )

   def get_time_scale(self):
      """Return effective time scaling information from the backend.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_time_scale()

   def get_gaps(self):
      """Return gap intervals (if any) in clock-time seconds.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_gaps()


   def apply_filter(self,ch,sos):
      """Apply an SOS filter to a channel in the segment cache.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         sos : object\n        Input argument `sos`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      return self.segsrv.apply_filter(ch,sos)
   
   def clear_filter(self,ch):
      """Clear an active channel filter.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      return self.segsrv.clear_filter(ch)

   def clear_filters(self):
      """Clear all active channel filters.
         
         Returns
         -------
         None
                 No value is returned.
      """
      return self.segsrv.clear_filters()
   
   def set_scaling(self, nchs, nanns = 0 , yscale = 1 , ygroup = 1 , yheader = 0.05 , yfooter = 0.05 , scaling_fixed_annot = 0.1 , clip = True):
      """Configure vertical scaling and layout settings for plotted traces.
         
         Parameters
         ----------
         nchs : object\n        Input argument `nchs`.
         nanns : object\n        Input argument `nanns`.
         yscale : object\n        Input argument `yscale`.
         ygroup : object\n        Input argument `ygroup`.
         yheader : object\n        Input argument `yheader`.
         yfooter : object\n        Input argument `yfooter`.
         scaling_fixed_annot : object\n        Input argument `scaling_fixed_annot`.
         clip : object\n        Input argument `clip`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.set_scaling( nchs, nanns, yscale, ygroup, yheader, yfooter, scaling_fixed_annot , clip )

   def get_scaled_signal(self, ch, n1):
      """Return y-scaled signal samples for display row ``n1``.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         n1 : object\n        Input argument `n1`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_scaled_signal( ch , n1 )

   def get_scaled_y(self, ch, y):
      """Transform a physical y-value into scaled plotting coordinates.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         y : object\n        Input argument `y`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_scaled_y( ch , y)

   def fix_physical_scale(self,ch,lwr,upr):
      """Pin a channel to fixed physical min/max display bounds.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         lwr : object\n        Input argument `lwr`.
         upr : object\n        Input argument `upr`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.fix_physical_scale( ch, lwr, upr )

   def empirical_physical_scale(self,ch):
      """Reset a channel to backend-derived empirical display bounds.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      self.segsrv.empirical_physical_scale( ch )

   def free_physical_scale( self, ch ):
      """Remove fixed physical bounds for a channel.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.free_physical_scale( ch )

   # sigmods

   def make_sigmod( self, mod_label, mod_ch, mod_type, sr, order, lwr, upr ):
      """Create a signal modifier using a Butterworth band filter definition.
         
         Parameters
         ----------
         mod_label : object\n        Input argument `mod_label`.
         mod_ch : object\n        Input argument `mod_ch`.
         mod_type : object\n        Input argument `mod_type`.
         sr : object\n        Input argument `sr`.
         order : object\n        Input argument `order`.
         lwr : object\n        Input argument `lwr`.
         upr : object\n        Input argument `upr`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      sos = butter( order , [ lwr, upr ] , btype='band', fs=sr, output='sos' )
      self.segsrv.make_sigmod( mod_label, mod_ch, mod_type, sos.reshape(-1) )

   def make_sigmod_sos( self, mod_label, mod_ch, mod_type, sos ):
      """Create a signal modifier from an existing SOS vector.
         
         Parameters
         ----------
         mod_label : object\n        Input argument `mod_label`.
         mod_ch : object\n        Input argument `mod_ch`.
         mod_type : object\n        Input argument `mod_type`.
         sos : object\n        Input argument `sos`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.make_sigmod( mod_label, mod_ch, mod_type, sos )

   def make_sigmod_raw( self, mod_label, mod_ch, mod_type  ):
      """Create a pass-through (raw) signal modifier slot.
         
         Parameters
         ----------
         mod_label : object\n        Input argument `mod_label`.
         mod_ch : object\n        Input argument `mod_ch`.
         mod_type : object\n        Input argument `mod_type`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.make_sigmod( mod_label, mod_ch, 'raw' , [ ] )

   def apply_sigmod( self, mod_label, mod_ch, slot ):
      """Apply a previously registered signal modifier to a display slot.
         
         Parameters
         ----------
         mod_label : object\n        Input argument `mod_label`.
         mod_ch : object\n        Input argument `mod_ch`.
         slot : object\n        Input argument `slot`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.apply_sigmod( mod_label, mod_ch, slot )

   def get_sigmod_timetrack( self, bin ):
      """Return the time axis for a signal-modifier output bin.
         
         Parameters
         ----------
         bin : object\n        Input argument `bin`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_sigmod_timetrack( bin )

   def get_sigmod_scaled_signal( self, bin ):
      """Return scaled samples for a signal-modifier output bin.
         
         Parameters
         ----------
         bin : object\n        Input argument `bin`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_sigmod_scaled_signal( bin )

   # epochs
   
   def set_epoch_size( self, s ):
      """Set epoch size (seconds) used by the segment server.
         
         Parameters
         ----------
         s : object\n        Input argument `s`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.set_epoch_size( s )

   def get_epoch_size( self):
      """Return current epoch size (seconds).
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_epoch_size()

#   def get_epoch_timetrack(self):
#      return self.segsrv.get_epoch_timetrack()
      
   def num_epochs( self) :
      """Return total number of epochs at current epoch size.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.nepochs()

#   def num_seconds( self ):
#      return self.segsrv.get_ungapped_total_sec()
   
   def num_seconds_clocktime( self ):
      """Return total clock-time duration in seconds (post-processing).
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_total_sec()
   
   def num_seconds_clocktime_original( self ):
      """Return original clock-time duration in seconds.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_total_sec_original()

   def calc_bands( self, chs ):
      """Precompute spectral band summaries for one or more channels.
         
         Parameters
         ----------
         chs : object\n        Input argument `chs`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      if type( chs ) is not list: chs = [ chs ]
      self.segsrv.calc_bands( chs );

   def calc_hjorths( self, chs ):
      """Precompute Hjorth summary features for one or more channels.
         
         Parameters
         ----------
         chs : object\n        Input argument `chs`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      if type( chs ) is not list: chs = [ chs ]
      self.segsrv.calc_hjorths( chs );

   def get_bands( self, ch ):
      """Return precomputed band-summary matrix for a channel.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_bands( ch )

   def get_hjorths( self, ch ):
      """Return precomputed Hjorth-summary matrix for a channel.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_hjorths( ch )
   
   def valid_window( self ):
      """Return whether the current window is valid for rendering.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.is_window_valid()

   def is_clocktime( self ):
      """Return whether this instance uses absolute clock-time semantics.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.is_clocktime()

   def get_window_left( self ):
      """Return left edge of current viewing window (seconds).
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_window_left()

   def get_window_right( self ):
      """Return right edge of current viewing window (seconds).
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_window_right()
   
   def get_window_left_hms( self ):
      """Return left edge of current viewing window as ``HH:MM:SS``.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_window_left_hms()

   def get_window_right_hms( self ):
      """Return right edge of current viewing window as ``HH:MM:SS``.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_window_right_hms()

   def get_clock_ticks( self , n = 6 ):
      """Return up to ``n`` formatted clock-time tick labels for the window.
         
         Parameters
         ----------
         n : object\n        Input argument `n`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      assert type( n ) is int
      return self.segsrv.get_clock_ticks( n )

   def get_hour_ticks( self ):
      """Return hour-level clock ticks for the current timeline.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_hour_ticks()

   def get_window_phys_range( self , ch ):
      """Return physical min/max of channel data within current window.
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      assert type(ch) is str
      return self.segsrv.get_window_phys_range( ch )
   
   def get_ylabel( self , n ):
      """Return normalized y-axis anchor location for display row ``n``.
         
         Parameters
         ----------
         n : object\n        Input argument `n`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      assert type(n) is int
      return self.segsrv.get_ylabel( n )

   def throttle(self,n):
      """Set output-point throttle for rendering-heavy operations.
         
         Parameters
         ----------
         n : object\n        Input argument `n`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      assert type(n) is int
      self.segsrv.throttle(n)

   def input_throttle(self,n):
      """Set input sample-rate throttle before cache population.
         
         Parameters
         ----------
         n : object\n        Input argument `n`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      assert type(n) is int
      self.segsrv.input_throttle(n)

   def summary_threshold_mins(self,m):
      """Set summary threshold (minutes) used by backend aggregation.
         
         Parameters
         ----------
         m : object\n        Input argument `m`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      assert type(m) is int or type(m) is float
      self.segsrv.summary_threshold_mins(m)

   def get_annots(self):
      """Return currently cached annotation rows.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.fetch_annots()

   def get_all_annots(self,anns,hms = False ):
      """Return all events for selected annotation classes.
         
         Parameters
         ----------
         anns : object\n        Input argument `anns`.
         hms : object\n        Input argument `hms`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.fetch_all_annots(anns, hms )

   def get_all_annots_with_inst_ids(self,anns,hms = True ):
      """Return all events for selected classes, including instance IDs.
         
         Parameters
         ----------
         anns : object\n        Input argument `anns`.
         hms : object\n        Input argument `hms`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.fetch_all_annots_with_inst_ids(anns, hms )
   
   def compile_windowed_annots(self,anns):
      """Compile selected annotation classes into window-ready caches.
         
         Parameters
         ----------
         anns : object\n        Input argument `anns`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.compile_evts( anns )

   def set_clip_xaxes(self,clip):
      """Enable or disable x-axis clipping for annotation drawing.
         
         Parameters
         ----------
         clip : object\n        Input argument `clip`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.set_clip_xaxes( clip )
      
   def get_annots_xaxes(self,ann):
      """Return x-axis polygon coordinates for annotation ``ann``.
         
         Parameters
         ----------
         ann : object\n        Input argument `ann`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_evnts_xaxes( ann )

   def get_annots_yaxes(self,ann):
      """Return y-axis polygon coordinates for annotation ``ann``.
         
         Parameters
         ----------
         ann : object\n        Input argument `ann`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_evnts_yaxes( ann )

   def set_annot_format6(self,b):
      """Toggle 6-point polygon format for annotation rendering.
         
         Parameters
         ----------
         b : object\n        Input argument `b`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.segsrv.set_evnt_format6(b)
      
   def get_annots_xaxes_ends(self,ann):
      """Return end-cap x-coordinates for annotation ``ann`` polygons.
         
         Parameters
         ----------
         ann : object\n        Input argument `ann`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_evnts_xaxes_ends( ann )

   def get_annots_yaxes_ends(self,ann):
      """Return end-cap y-coordinates for annotation ``ann`` polygons.
         
         Parameters
         ----------
         ann : object\n        Input argument `ann`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.segsrv.get_evnts_yaxes_ends( ann )

__all__ = ["segsrv", "stgcol", "stgn"]
