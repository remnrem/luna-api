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
from IPython.core import display as ICD
import plotly.graph_objects as go
import time
import pathlib
import os

from IPython.display import display

from .project import proj
from .results import tables, cmdfile


def hypno(*args, **kwargs):
   """Lazy proxy to avoid import cycles with :mod:`lunapi.viz`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   from .viz import hypno as _hypno
   return _hypno(*args, **kwargs)


def psd(*args, **kwargs):
   """Lazy proxy to avoid import cycles with :mod:`lunapi.viz`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   from .viz import psd as _psd
   return _psd(*args, **kwargs)


def spec(*args, **kwargs):
   """Lazy proxy to avoid import cycles with :mod:`lunapi.viz`.
      
      Returns
      -------
      object
              Result value produced by the Luna backend wrapper.
   """
   from .viz import spec as _spec
   return _spec(*args, **kwargs)


class inst:
   """This class represents a single individual/instance (signals & annotations)"""
   
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
      """Return the current instance identifier.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.edf.get_id()
      
   #------------------------------------------------------------------------

   def attach_edf( self, f ):
      """Attach an EDF from a file
         
         Parameters
         ----------
         f : object\n        Input argument `f`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.edf.attach_edf( f )

   #------------------------------------------------------------------------

   def attach_annot( self, annot ):
      """Attach annotations from a file
         
         Parameters
         ----------
         annot : object\n        Input argument `annot`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.edf.attach_annot( annot )

   #------------------------------------------------------------------------

   def stat( self ):
      """Return a dataframe of basic statistics
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      t = pd.DataFrame( self.edf.stat(), index=[0] ).T
      t.columns = ["Value"]
      return t

   #------------------------------------------------------------------------

   def refresh( self ):
      """Refresh an attached EDF
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      self.edf.refresh()
      # also need to reset Luna problem flag
      # note: current kludge: problem is proj-wide
      #       so this will not play well w/ multiple EDFs
      # todo: implement inst-specific prob flag
      
      _proj = proj(False)
      _proj.reset();


   #------------------------------------------------------------------------

   def clear_vars(self, keys = None ):
      """Clear some or all individual-level variable(s)
         
         Parameters
         ----------
         keys : object\n        Input argument `keys`.
         
         Returns
         -------
         None
                 No value is returned.
      """

      # all
      if keys is None:
         self.edf.clear_ivar()
         return

      # one/some
      if type( keys ) is not set: keys = set( keys )
      self.edf.clear_selected_ivar( keys )
      
   #------------------------------------------------------------------------

   def var( self , key = None , value = None ):
      """Set or get individual-level variable(s)
         
         Parameters
         ----------
         key : object\n        Input argument `key`.
         value : object\n        Input argument `value`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.vars( key , value )
   
   #------------------------------------------------------------------------      

   def vars( self , key = None , value = None ):
      """Set or get individual-level variable(s)
         
         Parameters
         ----------
         key : object\n        Input argument `key`.
         value : object\n        Input argument `value`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Returns of dataframe of current channels"""
      t = pd.DataFrame( self.edf.desc() ).T
      t.index =	t.index	+ 1
      if len( t ) == 0: return t
      t.columns = ["ID","Gapped","Date","Start(hms)","Stop(hms)","Dur(hms)","Dur(s)","# sigs","# annots","Signals" ]
      with pd.option_context('display.max_colwidth',None):
         display(t)
   
   #------------------------------------------------------------------------      

   def channels( self ):
      """Returns of dataframe of current channels"""
      t = pd.DataFrame( self.edf.channels() )
      if len( t ) == 0: return t
      t.columns = ["Channels"]
      return t

   #------------------------------------------------------------------------      

   def chs( self ):
      """Returns of dataframe of current channels"""
      t = pd.DataFrame( self.edf.channels() )
      if len( t ) == 0: return t
      t.columns = ["Channels"]
      return t

   #------------------------------------------------------------------------      

   def headers(self):
      """Return channel header info
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Returns of dataframe of current annotations"""
      t = pd.DataFrame( self.edf.annots() )
      if len( t ) == 0: return t
      t.columns = ["Annotations"]
      return t

   #------------------------------------------------------------------------   

   def fetch_annots( self , anns , interp = -1 ):
      """Returns of dataframe of annotation events
         
         Parameters
         ----------
         anns : object\n        Input argument `anns`.
         interp : object\n        Input argument `interp`.
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
      """Returns of dataframe of annotation events
         
         Parameters
         ----------
         anns : object\n        Input argument `anns`.
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
      """Evaluate one or more Luna commands, storing results internally
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      self.edf.eval( cmdstr )
      return self.strata()
      
   #------------------------------------------------------------------------

   def eval_dummy( self, cmdstr ):      
      """Evaluate commands in dummy mode and return backend status/log text.
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.edf.eval_dummy( cmdstr )

   #------------------------------------------------------------------------

   def eval_lunascope( self, cmdstr ):
      """Evaluate one or more Luna commands, storing results internally, return console log
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.edf.eval_lunascope( cmdstr )

   #------------------------------------------------------------------------

   def proc( self, cmdstr ):
      """Evaluate one or more Luna commands, returning results as an object
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      # < log , tables >
      r = self.edf.proc( cmdstr )
      # extract and return result tables
      return tables( r[1] ) 

   #------------------------------------------------------------------------                                                                           

   def silent_proc( self, cmdstr ):
      """Silently evaluate one or more Luna commands (for internal use)
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Silently evaluate one or more Luna commands (for internal use)
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Return whether the instance result store currently has no tables.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return len( self.edf.strata()  ) == 0

   #------------------------------------------------------------------------

   def strata( self ):
      """Return a dataframe of command/strata pairs from the output set
         
         Returns
         -------
         object
                 See function description for the concrete return type.
      """
      if ( self.empty_result_set() ): return None
      t = pd.DataFrame( self.edf.strata() )
      t.columns = ["Command","Strata"]
      return t

   #------------------------------------------------------------------------

   def table( self, cmd , strata = 'BL' ):
      """Return a dataframe for a given command/strata pair from the output set
         
         Parameters
         ----------
         cmd : object\n        Input argument `cmd`.
         strata : object\n        Input argument `strata`.
         
         Returns
         -------
         object
                 See function description for the concrete return type.
      """
      if ( self.empty_result_set() ): return None
      r = self.edf.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   #------------------------------------------------------------------------

   def variables( self, cmd , strata = 'BL' ):
      """Return a list of all variables for a output set table
         
         Parameters
         ----------
         cmd : object\n        Input argument `cmd`.
         strata : object\n        Input argument `strata`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if ( self.empty_result_set() ): return None
      return self.edf.variables( cmd , strata )


   #------------------------------------------------------------------------

   def e2i( self, epochs ):
      """Helper function to convert epoch (1-based) to intervals
         
         Parameters
         ----------
         epochs : object\n        Input argument `epochs`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if type( epochs ) is not list: epochs = [ epochs ]
      return self.edf.e2i( epochs )
     
   # --------------------------------------------------------------------------------

   def s2i( self, secs ):
      """Helper function to convert seconds to intervals
         
         Parameters
         ----------
         secs : object\n        Input argument `secs`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.edf.s2i( secs )

   # --------------------------------------------------------------------------------

   def data( self, chs , annots = None , time = False ):
      """Returns all data for certain channels and annotations
         
         Parameters
         ----------
         chs : object\n        Input argument `chs`.
         annots : object\n        Input argument `annots`.
         time : object\n        Input argument `time`.
      """
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.data( chs , annots , time )

   # --------------------------------------------------------------------------------

   def slice( self, intervals, chs , annots = None , time = False ):
      """Return signal/annotation data aggregated over a set of intervals
         
         Parameters
         ----------
         intervals : object\n        Input argument `intervals`.
         chs : object\n        Input argument `chs`.
         annots : object\n        Input argument `annots`.
         time : object\n        Input argument `time`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.slice( intervals, chs , annots , time )

   # --------------------------------------------------------------------------------   

   def slices( self, intervals, chs , annots = None , time = False ):
      """Return a series of signal/annotation data objects for each requested interval
         
         Parameters
         ----------
         intervals : object\n        Input argument `intervals`.
         chs : object\n        Input argument `chs`.
         annots : object\n        Input argument `annots`.
         time : object\n        Input argument `time`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.slices( intervals, chs , annots , time )
   
   # --------------------------------------------------------------------------------

   def insert_signal( self, label , data , sr ):
      """Insert a signal into an in-memory EDF
         
         Parameters
         ----------
         label : object\n        Input argument `label`.
         data : object\n        Input argument `data`.
         sr : object\n        Input argument `sr`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      return self.edf.insert_signal( label , data , sr )

   # --------------------------------------------------------------------------------

   def update_signal( self, label , data ):
      """Update an existing signal in an in-memory EDF
         
         Parameters
         ----------
         label : object\n        Input argument `label`.
         data : object\n        Input argument `data`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      return self.edf.update_signal( label , data )

   # --------------------------------------------------------------------------------

   def insert_annot( self, label , intervals, durcol2 = False ):
      """Insert annotations into an in-memory dataset
         
         Parameters
         ----------
         label : object\n        Input argument `label`.
         intervals : object\n        Input argument `intervals`.
         durcol2 : object\n        Input argument `durcol2`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      return self.edf.insert_annot( label , intervals , durcol2 )



   # --------------------------------------------------------------------------------
   #
   # Luna function wrappers
   #
   # --------------------------------------------------------------------------------


   # --------------------------------------------------------------------------------

   def freeze( self , f ):
      """Persist the current timeline mask to a freezer tag.
         
         Parameters
         ----------
         f : str
             Freezer tag name.
         
         Returns
         -------
         None
                 No value is returned.
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
             If ``True``, remove the tag after thawing.
         
         Returns
         -------
         None
                 No value is returned.
      """
      if remove:
         self.eval( 'THAW tag=' + f + 'remove' )
      else:
         self.eval( 'THAW ' + f )

   # --------------------------------------------------------------------------------

   def empty_freezer( self ):
      """Clear all persisted freezer tags for this instance.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      self.eval( 'CLEAN-FREEZER' )
      
   # --------------------------------------------------------------------------------

   def mask( self , f = None ):
      """Apply one or more Luna mask expressions and rebuild epochs.
         
         Parameters
         ----------
         f : str or list of str, optional
             One or more mask expressions/files to apply.
         
         Returns
         -------
         None
                 No value is returned.
      """
      if f is None: return
      if type(f) is not list: f = [ f ]
      [ self.eval( 'MASK ' + _f ) for _f in f ]
      self.eval( 'RE' )   

   
   # --------------------------------------------------------------------------------

   def segments( self ):
      """Run ``SEGMENTS`` and return the ``SEGMENTS: SEG`` table.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      self.eval( 'SEGMENTS' )
      return self.table( 'SEGMENTS' , 'SEG' )
   
   # --------------------------------------------------------------------------------

   def epoch( self , f = '' ):
      """Run the ``EPOCH`` command with optional arguments.
         
         Parameters
         ----------
         f : str, optional
             Additional ``EPOCH`` arguments.
         
         Returns
         -------
         None
                 No value is returned.
      """
      self.eval( 'EPOCH ' + f )


   # --------------------------------------------------------------------------------

   def epochs( self ):
      """Run ``EPOCH table`` and return a compact epoch summary dataframe.
         
         Returns
         -------
         None
                 No value is returned.
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

      """Generates an MTM spectrogram
         
         Main channel
         ------------
         ch   : a single channel --> MTM 
         
         Selection of intervals
         ----------------------
         e    : one or [ start , stop ] epochs (1-based)
         
         Optional views
         --------------
         traces  : T/F show raw signal
         anns : show optional annotations
         
         Misc
         ----
         norm : normalization mode    
         todo: option to specify hms times
         todo: collapse over time-locked values (e.g. TLOCK)
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         e : object\n        Input argument `e`.
         t : object\n        Input argument `t`.
         a : object\n        Input argument `a`.
         tw : object\n        Input argument `tw`.
         sec : object\n        Input argument `sec`.
         inc : object\n        Input argument `inc`.
         f : object\n        Input argument `f`.
         winsor : object\n        Input argument `winsor`.
         anns : object\n        Input argument `anns`.
         norm : object\n        Input argument `norm`.
         traces : object\n        Input argument `traces`.
         xlines : object\n        Input argument `xlines`.
         ylines : object\n        Input argument `ylines`.
         silent : object\n        Input argument `silent`.
         pal : object\n        Input argument `pal`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Run the POPS stager
         
         Parameters
         ----------
         s : object\n        Input argument `s`.
         s1 : object\n        Input argument `s1`.
         s2 : object\n        Input argument `s2`.
         path : object\n        Input argument `path`.
         lib : object\n        Input argument `lib`.
         do_edger : object\n        Input argument `do_edger`.
         no_filter : object\n        Input argument `no_filter`.
         do_reref : object\n        Input argument `do_reref`.
         m : object\n        Input argument `m`.
         m1 : object\n        Input argument `m1`.
         m2 : object\n        Input argument `m2`.
         lights_off : object\n        Input argument `lights_off`.
         lights_on : object\n        Input argument `lights_on`.
         ignore_obs : object\n        Input argument `ignore_obs`.
         args : object\n        Input argument `args`.
         
         Returns
         -------
         object
                 See function description for the concrete return type.
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
         
      # set options
      self.var( 'mpath' , path )
      self.var( 'lib' , lib )
      self.var( 'do_edger' , '1' if do_edger else '0' )
      self.var( 'do_reref' , '1' if do_reref else '0' )
      self.var( 'no_filter' , '1' if no_filter else '0' )
      self.var( 'LOFF' , lights_off )
      self.var( 'LON' , lights_on )

      if s is not None: self.var( 's' , s )
      if m is not None: self.var( 'm' , m )
      if s1 is not None: self.var( 's1' , s1 )
      if s2 is not None: self.var( 's2' , s2 )
      if m1 is not None: self.var( 'm1' , m1 )
      if m2 is not None: self.var( 'm2' , m2 )
      
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
      """Run SUN2019 prediction model for a single individual
         
         Parameters
         ----------
         cen : object\n        Input argument `cen`.
         age : object\n        Input argument `age`.
         th : object\n        Input argument `th`.
         path : object\n        Input argument `path`.
         
         Returns
         -------
         object
                 See function description for the concrete return type.
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
      """Return of a list of stages
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      hyp = self.silent_proc( "STAGE" )
      if type(hyp) is type(None): return
      if 'STAGE: E' in hyp:
         return hyp[ 'STAGE: E' ]
      return

   # --------------------------------------------------------------------------------   

   def hypno(self):
      """Hypnogram of sleep stages
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if self.has_staging() is not True:
         print( "no staging attached" )
         return
      return hypno( self.stages()[ 'STAGE' ] )

   # --------------------------------------------------------------------------------

   def has_staging(self):
      """Returns bool for whether staging is present"""
      _proj = proj(False)
      silence_mode = _proj.is_silenced()
      _proj.silence(True,False)
      res = self.edf.has_staging()
      _proj.silence( silence_mode , False )
      return res

   # --------------------------------------------------------------------------------

   def has_annots(self,anns):
      """Returns bool for which annotations are present
         
         Parameters
         ----------
         anns : object\n        Input argument `anns`.
      """
      if anns is None: return
      if type( anns ) is not list: anns = [ anns ]
      return self.edf.has_annots( anns )

   # --------------------------------------------------------------------------------

   def has_annot(self,anns):
      """Returns bool for which annotations are present
         
         Parameters
         ----------
         anns : object\n        Input argument `anns`.
      """
      return self.has_annots(anns)

   # --------------------------------------------------------------------------------

   def has_channels(self,ch):
      """Return a bool to indicate whether a given channel exists
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if ch is None: return
      if type(ch) is not list: ch = [ ch ]
      return self.edf.has_channels( ch )

   # --------------------------------------------------------------------------------

   def has(self,ch):
      """Return a bool to indicate whether a given channel exists
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Generates a PSD plot (from PSD or MTM) for one or more channel(s)
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         var : object\n        Input argument `var`.
         minf : object\n        Input argument `minf`.
         maxf : object\n        Input argument `maxf`.
         minp : object\n        Input argument `minp`.
         maxp : object\n        Input argument `maxp`.
         xlines : object\n        Input argument `xlines`.
         ylines : object\n        Input argument `ylines`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """PSD given channel 'ch'
         
         Parameters
         ----------
         ch : object\n        Input argument `ch`.
         mine : object\n        Input argument `mine`.
         maxe : object\n        Input argument `maxe`.
         minf : object\n        Input argument `minf`.
         maxf : object\n        Input argument `maxf`.
         w : object\n        Input argument `w`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
