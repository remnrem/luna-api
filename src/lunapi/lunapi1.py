"""lunapi1 module: a high-level wrapper around lunapi0 module functions"""

# Luna Python interface (lunapi)
# v1.3.4, 16-Oct-2025

import lunapi.lunapi0 as _luna

import pandas as pd
import numpy as np
from scipy.stats.mstats import winsorize
import matplotlib.pyplot as plt
from matplotlib import cm
from IPython.core import display as ICD
import plotly.graph_objects as go
import plotly.express as px
from ipywidgets import widgets, AppLayout
from itertools import cycle
import re
import requests
import io
import tempfile
import os
import tempfile
from ipywidgets import IntProgress
from IPython.display import display
import time
import pathlib


# resource set for Docker container version
class resources:
   POPS_PATH = '/build/nsrr/common/resources/pops/'
   POPS_LIB = 's2'
   MODEL_PATH = '/build/luna-models/'

lp_version = "v1.3.4"
   
# C++ singleton class (engine & sample list)
# lunapi_t      --> luna

# one observation
# lunapi_inst_T --> inst

# --------------------------------------------------------------------------------
# luna class 

class proj:
   """Instance of the underlying Luna engine

   Only a single instance of this will be generated per session, via proj().

   This class also contains a sample-list and utility functions for importing
   Luna output databases.
   """
   
   # single static engine class
   eng = _luna.inaugurate()
   
   def __init__(self, verbose = True ):
      self.n = 0
      if verbose: print( "initiated lunapi",lp_version,proj.eng ,"\n" )
      self.silence( False )
      self.eng = _luna.inaugurate()
      
   def retire(self):
      """Retires an existing Luna engine generated via proj()"""
      return _luna.retire()
   
   def build( self, args ):
      """Builds an internal sample-list object given a set of folders
      
      This generates an internal sample-list by finding EDF and annotation
      files across one or more folders.  This provides the same functionality
      as the `--build` option of Luna, which is described here:

      https://zzz.bwh.harvard.edu/luna/ref/helpers/#-build

      After building, a call to sample_list() will return the number of individuals
      
      Parameters
      ----------
      args : [ str ] 
          a list of folder names and optional arguments to be passed to build

      """

      # first clear any existing sample list
      proj.eng.clear()

      # then try to build a new one
      if type( args ) is not list: args = [ args ]
      return proj.eng.build_sample_list( args )

   
   def sample_list(self, filename = None , path = None , df = True ):
      """Reads a sample-list 'filenamne', optionally setting 'path' and returns the number of observations

      If filename is not defined, this returns the internal sample list
      as an object

      Parameters
      ----------
      filename : str
          optional filename of a sample-list to read

      path : str
          optional path to preprend to the sample-list when reading (sets the 'path' variable)

      df : bool
          if returning a sample-list, return as a Pandas dataframe
      
      Returns
      -------
      list
          a list of strings representing the sample-list (IDs, EDFs, annotations for each individual)
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
      """The number of observations in the internal sample list

      Returns                                                                                                                                                                         
      -------
      int
          the number of observations in the sample-list
      """

      return proj.eng.nobs()

   #------------------------------------------------------------------------
      
   def validate( self ):
      """Validates an internal sample-list 
      
      This provides the same functionality
      as the `--validate` option of Luna, which is described here:

      https://zzz.bwh.harvard.edu/luna/ref/helpers/#-validate

      Parameters
      ----------
      none

      """

      tbl = proj.eng.validate_sample_list()
      tbl = pd.DataFrame( tbl )
      tbl.columns = [ 'ID' , 'Filename', 'Valid' ]
      tbl.index += 1
      return tbl


   #------------------------------------------------------------------------
      
   def reset(self):
      """ Drop Luna problem flag """
      proj.eng.reset()

   def reinit(self):
      """ Re-initialize project """
      proj.eng.reinit()

   #------------------------------------------------------------------------
   
   def inst( self, n ):
      """Generates a new instance"""

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
         
      # return based on n (from sample-list) or string/empty (new instance)
      return inst(proj.eng.inst( n ))
      

   #------------------------------------------------------------------------
   
   def empty_inst( self, id, nr, rs, startdate = '01.01.00', starttime = '00.00.00' ):
      """Generates a new instance with empty fixed-size EDF"""

      # check inputs
      nr = int( nr )
      rs = int( rs )
      if nr < 0:
         print( "expecting nr (number of records) to be a positive integer" )
         return      
      if rs < 0:
         print( "expecting rs (record duration, secs) to be a positive integer" )
         return
      
      # return instance of fixed size
      return inst(proj.eng.empty_inst(id, nr, rs, startdate, starttime ))

   #------------------------------------------------------------------------
   def clear(self):
      """Clears any existing project sample-list"""
      proj.eng.clear()


   #------------------------------------------------------------------------
   def silence(self, b = True , verbose = False ):
      """Toggles the output mode on/off"""
      if verbose:
         if b: print( 'silencing console outputs' )
         else: print( 'enabling console outputs' )
      proj.eng.silence(b)

   #------------------------------------------------------------------------
   def is_silenced(self, b = True ):
      """Reports on whether log is silenced"""
      return proj.eng.is_silenced()
      
      
   #------------------------------------------------------------------------
   def flush(self):
      """Internal command, to flush the output buffer"""
      proj.eng.flush()

   # --------------------------------------------------------------------------------
   def include( self, f ):
      """Include options/variables from a @parameter-file"""
      return proj.eng.include( f )


   #------------------------------------------------------------------------
   def aliases( self ):
      """Return a table of signal/annotation aliases"""
      t = pd.DataFrame( proj.eng.aliases() )      
      t.index = t.index + 1
      if len( t ) == 0: return t
      t.columns = ["Type", "Preferred", "Case-insensitive, sanitized alias" ]
      with pd.option_context('display.max_rows', None,):   
         display(t)

   #------------------------------------------------------------------------
   def var(self , key=None , value=None):
      """Set or get project-level options(s)/variables(s)"""
      return self.vars( key, value )

   #------------------------------------------------------------------------
   def vars(self , key=None , value=None):
      """Set or get project-level options(s)/variables(s)"""

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
      """Clear project-level option(s)/variable(s)"""

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
      """Clear individual-level variables for all individuals"""
      proj.eng.clear_ivars()

   #------------------------------------------------------------------------
   def get_n(self,id):
      """Return the number of individuals in the sample-list"""
      return proj.eng.get_n(id)

   #------------------------------------------------------------------------   
   def get_id(self,n):
      """Return the ID of an individual from the sample-list"""
      return proj.eng.get_id(n)

   #------------------------------------------------------------------------
   def get_edf(self,x):
      """Return the EDF filename for an individual from the sample-list"""
      if ( isinstance(x,int) ):
         return proj.eng.get_edf(x)
      else:
         return proj.eng.get_edf(proj.eng.get_n(x))


   #------------------------------------------------------------------------      
   def get_annots(self,x):
      """Return the annotation filenames for an individual from the sample-list"""
      if ( isinstance(x,int) ):
         return proj.eng.get_annot(x)
      else:
         return proj.eng.get_annot(proj.eng.get_n(x))


   #------------------------------------------------------------------------      
   def import_db(self,f,s=None):
      """Import a destrat-style Luna output database"""
      if s is None:
         return proj.eng.import_db(f)
      else:
         return proj.eng.import_db_subset(f,s)

   #------------------------------------------------------------------------      
   def desc( self ):
      """Returns table of descriptives for all sample-list individuals"""
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
      """Evaluates one or more Luna commands for all sample-list individuals"""
      r = proj.eng.eval(cmdstr)
      return tables( r )

   #------------------------------------------------------------------------ 
   def silent_proc(self, cmdstr ):
      """Silently evaluates one or more Luna commands for all sample-list individuals"""
      silence_mode = self.is_silenced()
      self.silence(True,False)
      r = proj.eng.eval(cmdstr)
      self.silence( silence_mode , False )
      return tables( r )
      
   #------------------------------------------------------------------------   
   def commands( self ):
      """Return a list of commands in the output set (following proc()"""
      t = pd.DataFrame( proj.eng.commands() )
      t.columns = ["Command"]
      return t

   #------------------------------------------------------------------------
   def empty_result_set( self ):
      return len( proj.eng.strata()  ) == 0

   #------------------------------------------------------------------------   
   def strata( self ):
      """Return a datraframe of command/strata pairs from the output set"""
      
      if self.empty_result_set(): return None
      t = pd.DataFrame( proj.eng.strata() )      
      t.columns = ["Command","Strata"]
      return t

   #------------------------------------------------------------------------
   def table( self, cmd , strata = 'BL' ):
      """Return a dataframe from the output set"""
      if self.empty_result_set(): return None
      r = proj.eng.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   #------------------------------------------------------------------------
   def variables( self, cmd , strata = 'BL' ):
      """Return a list of all variables for an output table"""
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
      """Run the POPS stager"""

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
      """Run SUN2019 prediction model for a project

      This assumes that ${age} will be set via a vars file, i.e.

         proj.var( 'vars' , 'ages.txt' )      

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
      return self.edf.get_id()
      
   #------------------------------------------------------------------------
   def attach_edf( self, f ):
      """Attach an EDF from a file"""
      return self.edf.attach_edf( f )

   #------------------------------------------------------------------------
   def attach_annot( self, annot ):
      """Attach annotations from a file"""
      return self.edf.attach_annot( annot )

   #------------------------------------------------------------------------
   def stat( self ):
      """Return a dataframe of basic statistics"""
      t = pd.DataFrame( self.edf.stat(), index=[0] ).T
      t.columns = ["Value"]
      return t

   #------------------------------------------------------------------------
   def refresh( self ):
      """Refresh an attached EDF"""
      self.edf.refresh()
      # also need to reset Luna problem flag
      # note: current kludge: problem is proj-wide
      #       so this will not play well w/ multiple EDFs
      # todo: implement inst-specific prob flag
      
      _proj = proj(False)
      _proj.reset();


   #------------------------------------------------------------------------
   def clear_vars(self, keys = None ):
      """Clear some or all individual-level variable(s)"""

      # all
      if keys is None:
         self.edf.clear_ivar()
         return

      # one/some
      if type( keys ) is not set: keys = set( keys )
      self.edf.clear_selected_ivar( keys )
      
   #------------------------------------------------------------------------
   def var( self , key = None , value = None ):
      """Set or get individual-level variable(s)"""
      return self.vars( key , value )
   
   #------------------------------------------------------------------------      
   def vars( self , key = None , value = None ):
      """Set or get individual-level variable(s)"""

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
      """Return channel header info"""
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
      """Returns of dataframe of annotation events"""
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
      """Returns of dataframe of annotation events"""
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
      """Evaluate one or more Luna commands, storing results internally"""
      self.edf.eval( cmdstr )
      return self.strata()
      
   #------------------------------------------------------------------------
   def eval_dummy( self, cmdstr ):      
      return self.edf.eval_dummy( cmdstr )

   #------------------------------------------------------------------------
   def eval_lunascope( self, cmdstr ):
      """Evaluate one or more Luna commands, storing results internally, return console log"""
      return self.edf.eval_lunascope( cmdstr )

   #------------------------------------------------------------------------
   def proc( self, cmdstr ):
      """Evaluate one or more Luna commands, returning results as an object"""
      # < log , tables >
      r = self.edf.proc( cmdstr )
      # extract and return result tables
      return tables( r[1] ) 

   #------------------------------------------------------------------------                                                                           
   def silent_proc( self, cmdstr ):
      """Silently evaluate one or more Luna commands (for internal use)"""
      
      _proj = proj(False)
      silence_mode = _proj.is_silenced()
      _proj.silence(True,False)
      
      r = self.edf.proc( cmdstr )

      _proj.silence( silence_mode , False )

      # extract and return result tables
      return tables( r[1] )

   #------------------------------------------------------------------------   
   def empty_result_set( self ):
      return len( self.edf.strata()  ) == 0

   #------------------------------------------------------------------------
   def strata( self ):
      """Return a dataframe of command/strata pairs from the output set"""
      if ( self.empty_result_set() ): return None
      t = pd.DataFrame( self.edf.strata() )
      t.columns = ["Command","Strata"]
      return t

   #------------------------------------------------------------------------
   def table( self, cmd , strata = 'BL' ):
      """Return a dataframe for a given command/strata pair from the output set"""
      if ( self.empty_result_set() ): return None
      r = self.edf.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   #------------------------------------------------------------------------
   def variables( self, cmd , strata = 'BL' ):
      """Return a list of all variables for a output set table"""
      if ( self.empty_result_set() ): return None
      return self.edf.variables( cmd , strata )


   #------------------------------------------------------------------------
   def e2i( self, epochs ):
      """Helper function to convert epoch (1-based) to intervals"""
      if type( epochs ) is not list: epochs = [ epochs ]
      return self.edf.e2i( epochs )
     
   # --------------------------------------------------------------------------------
   def s2i( self, secs ):
      """Helper function to convert seconds to intervals"""
      return self.edf.s2i( secs )

   # --------------------------------------------------------------------------------
   def data( self, chs , annots = None , time = False ):
      """Returns all data for certain channels and annotations"""
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.data( chs , annots , time )

   # --------------------------------------------------------------------------------
   def slice( self, intervals, chs , annots = None , time = False ):
      """Return signal/annotation data aggregated over a set of intervals"""
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.slice( intervals, chs , annots , time )

   # --------------------------------------------------------------------------------   
   def slices( self, intervals, chs , annots = None , time = False ):
      """Return a series of signal/annotation data objects for each requested interval"""
      if type( chs ) is not list: chs = [ chs ]
      if annots is not None:
         if type( annots ) is not list: annots = [ annots ]
      if annots is None: annots = [ ]
      return self.edf.slices( intervals, chs , annots , time )
   
   # --------------------------------------------------------------------------------
   def insert_signal( self, label , data , sr ):
      """Insert a signal into an in-memory EDF"""
      return self.edf.insert_signal( label , data , sr )

   # --------------------------------------------------------------------------------
   def update_signal( self, label , data ):
      """Update an existing signal in an in-memory EDF"""
      return self.edf.update_signal( label , data )

   # --------------------------------------------------------------------------------
   def insert_annot( self, label , intervals, durcol2 = False ):
      """Insert annotations into an in-memory dataset"""
      return self.edf.insert_annot( label , intervals , durcol2 )



   # --------------------------------------------------------------------------------
   #
   # Luna function wrappers
   #
   # --------------------------------------------------------------------------------


   # --------------------------------------------------------------------------------
   def freeze( self , f ):
      self.eval( 'FREEZE ' + f )

   # --------------------------------------------------------------------------------
   def thaw( self , f , remove = False ):
      if remove:
         self.eval( 'THAW tag=' + f + 'remove' )
      else:
         self.eval( 'THAW ' + f )

   # --------------------------------------------------------------------------------
   def empty_freezer( self ):
      self.eval( 'CLEAN-FREEZER' )
      
   # --------------------------------------------------------------------------------
   def mask( self , f = None ):
      if f is None: return
      if type(f) is not list: f = [ f ]
      [ self.eval( 'MASK ' + _f ) for _f in f ]
      self.eval( 'RE' )   

   
   # --------------------------------------------------------------------------------
   def segments( self ):
      self.eval( 'SEGMENTS' )
      return self.table( 'SEGMENTS' , 'SEG' )
   
   # --------------------------------------------------------------------------------
   def epoch( self , f = '' ):
      self.eval( 'EPOCH ' + f )


   # --------------------------------------------------------------------------------
   def epochs( self ):
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
      """Run the POPS stager"""

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
      """Run SUN2019 prediction model for a single individual"""
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
      """Return of a list of stages"""   
      hyp = self.silent_proc( "STAGE" )
      if type(hyp) is type(None): return
      if 'STAGE: E' in hyp:
         return hyp[ 'STAGE: E' ]
      return

   # --------------------------------------------------------------------------------   
   def hypno(self):
      """Hypnogram of sleep stages"""
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
      """Returns bool for which annotations are present"""
      if anns is None: return
      if type( anns ) is not list: anns = [ anns ]
      return self.edf.has_annots( anns )

   # --------------------------------------------------------------------------------
   def has_annot(self,anns):
      """Returns bool for which annotations are present"""
      return self.has_annots(anns)

   # --------------------------------------------------------------------------------
   def has_channels(self,ch):
      """Return a bool to indicate whether a given channel exists"""
      if ch is None: return
      if type(ch) is not list: ch = [ ch ]
      return self.edf.has_channels( ch )

   # --------------------------------------------------------------------------------
   def has(self,ch):
      """Return a bool to indicate whether a given channel exists"""
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
      """Generates a PSD plot (from PSD or MTM) for one or more channel(s)"""
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
      """PSD given channel 'ch'"""
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


      
# --------------------------------------------------------------------------------
#
# misc non-member utilities functions
#
# --------------------------------------------------------------------------------


def fetch_doms():
   """Fetch all command domains"""
   return _luna.fetch_doms( True )

def fetch_cmds( dom ):
   """Fetch all commands"""
   return _luna.fetch_cmds( dom, True )

def fetch_params( cmd ):
   """Fetch all command parameters"""
   return _luna.fetch_params( cmd, True )

def fetch_tbls( cmd ):
   """Fetch all command tables"""
   return _luna.fetch_tbls( cmd, True )

def fetch_vars( cmd, tbl ):
   """Fetch all command/table variables"""
   return _luna.fetch_vars( cmd, tbl, True )

def fetch_desc_dom( dom ):
   """Description for a domain"""
   return _luna.fetch_desc_dom( dom  )

def fetch_desc_cmd( cmd ):
   """Description for a command"""
   return _luna.fetch_desc_cmd( cmd )

def fetch_desc_param( cmd , param ):
   """Description for a command/parameter"""
   return _luna.fetch_desc_param( cmd, param )

def fetch_desc_tbl( cmd , tbl ):
   """Description for a command/table"""
   return _luna.fetch_desc_tbl( cmd, tbl )

def fetch_desc_var( cmd, tbl, var ):
   """Fetch all command/table variable"""
   return _luna.fetch_desc_var( cmd, tbl, var )


# --------------------------------------------------------------------------------
def cmdfile( f ):
   """load and parse a Luna command script from a file"""

   return _luna.cmdfile( f )


# --------------------------------------------------------------------------------
def strata( ts ):
   """Utility function to format tables"""
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
   """Utility function to format tables"""
   r = ts[cmd][strata]
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------
def tables( ts ):
   """Utility function to format tables"""
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
   """Utility function to format tables"""
   for title , df in dfs.items():
      print( _color.BOLD + _color.DARKCYAN + title + _color.END )
      ICD.display(df)


# --------------------------------------------------------------------------------
def subset( df , ids = None , qry = None , vars = None  ):
   """Utility function to subset table rows/columns"""

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
   """Utility function to extract and concatenate tables"""

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
   """Return version of lunapi & luna"""
   return { "lunapi": lp_version , "luna": _luna.version() }

class _color:
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




def default_xy():
   """Default channel locations (64-ch EEG only, currently)"""
   vals = [["FP1", "AF7", "AF3", "F1", "F3", "F5", "F7", "FT7", 
            "FC5", "FC3", "FC1", "C1", "C3", "C5", "T7", "TP7", "CP5", 
            "CP3", "CP1", "P1", "P3", "P5", "P7", "P9", "PO7", "PO3", 
            "O1", "IZ", "OZ", "POZ", "PZ", "CPZ", "FPZ", "FP2", "AF8", 
            "AF4", "AFZ", "FZ", "F2", "F4", "F6", "F8", "FT8", "FC6", 
            "FC4", "FC2", "FCZ", "CZ", "C2", "C4", "C6", "T8", "TP8", 
            "CP6", "CP4", "CP2", "P2", "P4", "P6", "P8", "P10", "PO8", 
            "PO4", "O2"],
           [-0.139058, -0.264503, -0.152969, -0.091616, -0.184692, 
            -0.276864, -0.364058, -0.427975, -0.328783, -0.215938, 
            -0.110678, -0.1125, -0.225, -0.3375, -0.45, -0.427975, 
            -0.328783, -0.215938, -0.110678, -0.091616, -0.184692, 
            -0.276864, -0.364058, -0.4309, -0.264503, -0.152969, 
            -0.139058, 0, 0, 0, 0, 0, 0, 0.139058, 0.264503, 0.152969, 
            0, 0, 0.091616, 0.184692, 0.276864, 0.364058, 0.427975, 
            0.328783, 0.215938, 0.110678, 0, 0, 0.1125, 0.225, 0.3375, 
            0.45, 0.427975, 0.328783, 0.215938, 0.110678, 0.091616, 
            0.184692, 0.276864, 0.364058, 0.4309, 0.264503, 0.152969, 
            0.139058],
           [0.430423, 0.373607, 0.341595, 0.251562, 0.252734, 
            0.263932, 0.285114, 0.173607, 0.162185, 0.152059, 0.14838, 
            0.05, 0.05, 0.05, 0.05, -0.073607, -0.062185, -0.052059, 
            -0.04838, -0.151562, -0.152734, -0.163932, -0.185114, 
            -0.271394, -0.273607, -0.241595, -0.330422, -0.45, -0.35, 
            -0.25, -0.15, -0.05, 0.45, 0.430423, 0.373607, 0.341595, 
            0.35, 0.25, 0.251562, 0.252734, 0.263932, 0.285114, 0.173607, 
            0.162185, 0.152059, 0.14838, 0.15, 0.05, 0.05, 0.05, 
            0.05, 0.05, -0.073607, -0.062185, -0.052059, -0.04838, 
            -0.151562, -0.152734, -0.163932, -0.185114, -0.271394, 
            -0.273607, -0.241595, -0.330422]]
    
   topo = pd.DataFrame(np.array(vals).T, columns=['CH', 'X', 'Y'])
   topo[['X', 'Y']] = topo[['X', 'Y']].apply(pd.to_numeric)
   return topo


   

# --------------------------------------------------------------------------------
def stgcol(ss):
    """Utility function: translate a sleep stage string to a colour for plotting"""
    stgcols = { 'N1' : "#00BEFAFF" ,
                'N2' : "#0050C8FF" ,
                'N3' : "#000050FF" ,
                'NREM4' : "#000032FF",
                'R' : "#FA1432FF",
                'W' : "#31AD52FF",
                'L' : "#F6F32AFF",
                '?' : "#64646464",
                None : "#00000000" }
    return [ stgcols.get(item,item) for item in ss ] 



# --------------------------------------------------------------------------------
def stgn(ss):
    """Utility function: translate a sleep stage string to a number for plotting"""
   
    stgns = { 'N1' : -1,
              'N2' : -2,
              'N3' : -3,
              'NREM4' : -4,
              'R' : 0,
              'W' : 1,
              'L' : 2,
              '?' : 2,
              None : 2 }
    return [ stgns.get(item,item) for item in ss ]




# --------------------------------------------------------------------------------
#
# Visualizations
#
# --------------------------------------------------------------------------------


# --------------------------------------------------------------------------------
def hypno( ss , e = None , xsize = 20 , ysize = 2 , title = None ):
    """Plot a hypnogram"""
    ssn = stgn( ss )
    if e is None: e = np.arange(0, len(ssn), 1)
    e = e/120
    plt.figure(figsize=(xsize , ysize ))
    plt.plot( e , ssn , c = 'gray' , lw = 0.5 )
    plt.scatter( e , ssn , c = stgcol( ss ) , zorder=2.5 , s = 10 )
    plt.ylabel('Sleep stage')
    plt.xlabel('Time (hrs)')
    plt.ylim(-3.5, 2.5)
    plt.xlim(0,max(e))
    plt.yticks([-3,-2,-1,0,1,2] , ['N3','N2','N1','R','W','?'] )
    if ( title != None ): plt.title( title )
    plt.show()

# --------------------------------------------------------------------------------
def hypno_density( probs , e = None , xsize = 20 , ysize = 2 , title = None ):
   """Generate a hypno-density plot from a prior POPS/SOAP run"""

   # no data?
   if len(probs) == 0: return

   res = probs[ ["PP_N1","PP_N2","PP_N3","PP_R","PP_W" ]  ]
   ne = len(res)
   x = np.arange(1, ne+1, 1)
   y = res.to_numpy(dtype=float)
   fig, ax = plt.subplots()
   xsize = 20
   ysize=2.5
   fig.set_figheight(ysize)
   fig.set_figwidth(xsize)
   ax.set_xlabel('Epoch')
   ax.set_ylabel('Prob(stage)')
   ax.stackplot(x, y.T , colors = stgcol([ 'N1','N2','N3','R','W']) )
   ax.set(xlim=(1, ne), xticks=[ 1 , ne ] , 
          ylim=(0, 1), yticks=np.arange(0, 1))                                                                                             
   plt.show()



# --------------------------------------------------------------------------------
def psd(df , ch, var = 'PSD' , minf = None, maxf = None, minp = None, maxp = None , 
        xlines = None , ylines = None, dB = False ):
    """Returns a PSD plot from PSD or MTM epoch table (CH_F)"""
    if ch is None: return
    if type( ch ) is not list: ch = [ ch ]
    if type( xlines ) is not list and xlines != None: xlines = [ xlines ]
    if type( ylines ) is not list and ylines != None: ylines = [ ylines ]
    df = df[ df['CH'].isin(ch) ]
    if len(df) == 0: return
    f = df['F'].to_numpy(dtype=float)
    p = df[var].to_numpy(dtype=float)
    if dB is True: p = 10*np.log10(p)
    cx = df['CH'].to_numpy(dtype=str)
    if minp is None: minp = min(p)
    if maxp is None: maxp = max(p)
    if minf is None: minf = min(f)
    if maxf is None: maxf = max(f)
    incl = np.zeros(len(df), dtype=bool)
    incl[ (f >= minf) & (f <= maxf) ] = True
    f = f[ incl ]
    p = p[ incl ]
    cx = cx[ incl ] 
    p[ p > maxp ] = maxp
    p[ p < minp ] = minp
    [ plt.plot(f[ cx == _ch ], p[ cx == _ch ] , label = _ch ) for _ch in ch ]
    plt.legend()
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Power (dB)')
    if xlines is not None: [plt.axvline(_x, linewidth=1, color='gray') for _x in xlines ]
    if ylines is not None: [plt.axhline(_y, linewidth=1, color='gray') for _y in ylines ]
    plt.show()


# --------------------------------------------------------------------------------
def spec(df , ch = None , var = 'PSD' , mine = None , maxe = None , minf = None, maxf = None, w = 0.025 ):
    """Returns a spectrogram from a PSD or MTM epoch table (CH_E_F)"""
    if ch is not None: df = df.loc[ df['CH'] == ch ]
    if len(df) == 0: return
    x = df['E'].to_numpy(dtype=int)
    y = df['F'].to_numpy(dtype=float)
    z = df[ var ].to_numpy(dtype=float)
    if mine is None: mine = min(x)
    if maxe is None: maxe = max(x)
    if minf is None: minf = min(y)
    if maxf is None: maxf = max(y)
    incl = np.zeros(len(df), dtype=bool)
    incl[ (x >= mine) & (x <= maxe) & (y >= minf) & (y <= maxf) ] = True
    x = x[ incl ]
    y = y[ incl ]
    z = z[ incl ]
    z = winsorize( z , limits=[w, w] )

    #include/exclude here...
    spec0( x,y,z,mine,maxe,minf,maxf)

    
# --------------------------------------------------------------------------------
def spec0( x , y , z , mine , maxe , minf, maxf ):
   xn = max(x) - min(x) + 1
   yn = np.unique(y).size
   zi, yi, xi = np.histogram2d(y, x, bins=(yn,xn), weights=z, density=False )
   counts, _, _ = np.histogram2d(y, x, bins=(yn,xn))   
   with np.errstate(divide='ignore', invalid='ignore'):
      zi = zi / counts
   zi = np.ma.masked_invalid(zi)
   fig, ax = plt.subplots()
   fig.set_figheight(2)
   fig.set_figwidth(15)
   ax.set_xlabel('Epoch')
   ax.set_ylabel('Frequency (Hz)')
   ax.set(xlim=(mine, maxe), ylim=(minf,maxf) )
   p1 = ax.pcolormesh(xi, yi, zi, cmap = 'turbo' )
   fig.colorbar(p1)
   ax.margins(0.1)
   plt.show()

# --------------------------------------------------------------------------------   
def topo_heat(chs, z,  ths = None , th=0.05 ,
              topo = None , 
              lmts= None , sz=70, colormap = "bwr", title = "", 
              rimcolor="black", lab = "dB"):
    """Generate a channel-wise topoplot"""

    z = np.array(z)
    if ths is not None: ths = np.array(ths)
    if topo is None: topo = default_xy()

    xlim = [-0.6, 0.6]
    ylim = [-0.6, 0.6]
    rng = [np.min(z), np.max(z)]

    if lmts is None : lmts = rng
    else: assert lmts[0] <= rng[0] <= lmts[1] and lmts[0] <= rng[1] <= lmts[1], "channel values are out of specified limits"
   
    assert len(set(topo['CH']).intersection(chs)) > 0, "no matching channels"
    
    chs = chs.apply(lambda x: x.upper())    
    topo = topo[topo['CH'].isin(chs)]
    topo["vals"] = np.nan
    topo["th_vals"] = np.nan
    topo["rims"] = 0.5

    for ix, ch in topo.iterrows():
        topo.loc[ix,'vals'] = z[chs == ch["CH"]]
        if ths is None:
           topo.loc[ix,'th_vals'] = 999;
        else:              
           topo.loc[ix,'th_vals'] = ths[chs == ch["CH"]] 

        if topo.loc[ix,'th_vals'] < th:
           topo.loc[ix,'rims'] = 1.5
      
    fig, ax = plt.subplots()
    sc = ax.scatter(topo.loc[:,"X"], topo.loc[:,"Y"],cmap=colormap, 
                    c=topo.loc[:, "vals"], edgecolors=rimcolor,
                    linewidths=topo['rims'], s=sz, vmin=lmts[0], vmax=lmts[1])
    plt.text(-0.4, 0.5, s=title, fontsize=10, ha='center', va='center')
    plt.text(0.15, -0.48, s=np.round(lmts[0], 2), fontsize=8, ha='center', va='center')
    plt.text(0.53, -0.48, s=np.round(lmts[1], 2), fontsize=8, ha='center', va='center')
    plt.text(0.35, -0.47, s=lab, fontsize=10, ha='center', va='center')
    
    plt.xlim(xlim)  
    plt.ylim(ylim)  
    plt.axis('off')
    
    cax = fig.add_axes([0.6, 0.15, 0.25, 0.02])  # [x, y, width, height]
    plt.colorbar(sc, cax=cax, orientation='horizontal')
    plt.axis('off')

# arguments
#topo = default_xy()
#ch_names = topo.loc[:, "CH"] # vector of channel names
#ch_vals = np.random.uniform(0, 3, size=len(ch_names))
#ch_vals[0:3] = -18
#th_vals = np.random.uniform(0.06, 1, size=len(ch_names)) # vector of channel values
#th_vals[ch_names == "O2"] = 0
#lmts=[-4, 4]#"default"
#ltopo_heat(ch_names, ch_vals, th_vals = th_vals, th=0.05,
#           lmts=lmts, sz=70,
#           colormap = "bwr", title = "DENSITY", 
#           rimcolor="black", lab = "n/min")
   

# --------------------------------------------------------------------------------
# segsrv

class segsrv:
   """Segment server instance"""

   def __init__(self,p):
      assert isinstance(p,inst)
      self.p = p
      self.segsrv = _luna.segsrv(p.edf)
      
   def populate(self,chs=None,anns=None,max_sr=None):
      if chs is None: chs = self.p.edf.channels()
      if anns is None: anns = self.p.edf.annots()
      if type(chs) is not list: chs = [ chs ]
      if type(anns) is not list: anns = [ anns ]
      if type(max_sr) is int: self.segsrv.input_throttle( max_sr )
      self.segsrv.populate( chs , anns )

   def window(self,a,b):
      assert isinstance(a, (int, float) )
      assert isinstance(b, (int, float) )
      self.segsrv.set_window( a, b )
      
   def get_signal(self,ch):
      assert isinstance(ch, str )
      return self.segsrv.get_signal( ch )

   def get_timetrack(self,ch):
      assert isinstance(ch, str )
      return self.segsrv.get_timetrack( ch )

   def get_time_scale(self):
      return self.segsrv.get_time_scale()

   def get_gaps(self):
      return self.segsrv.get_gaps()

   def set_scaling(self, nchs, nanns = 0 , yscale = 1 , ygroup = 1 , yheader = 0.05 , yfooter = 0.05 , scaling_fixed_annot = 0.1 , clip = True):
      self.segsrv.set_scaling( nchs, nanns, yscale, ygroup, yheader, yfooter, scaling_fixed_annot , clip )

   def get_scaled_signal(self, ch, n1):
      return self.segsrv.get_scaled_signal( ch , n1 )

   def fix_physical_scale(self,ch,lwr,upr):
      self.segsrv.fix_physical_scale( ch, lwr, upr )

   def empirical_physical_scale(self,ch):
      self.segsrv.empirical_physical_scale( ch )

   def free_physical_scale( self, ch ):
      self.segsrv.free_physical_scale( ch )

   def set_epoch_size( self, s ):
      self.segsrv.set_epoch_size( s )

   def get_epoch_size( self):
      return self.segsrv.get_epoch_size()

#   def get_epoch_timetrack(self):
#      return self.segsrv.get_epoch_timetrack()
      
   def num_epochs( self) :
      return self.segsrv.nepochs()

#   def num_seconds( self ):
#      return self.segsrv.get_ungapped_total_sec()
   
   def num_seconds_clocktime( self ):
      return self.segsrv.get_total_sec()
   
   def num_seconds_clocktime_original( self ):
      return self.segsrv.get_total_sec_original()

   def calc_bands( self, chs ):
      if type( chs ) is not list: chs = [ chs ]
      self.segsrv.calc_bands( chs );

   def calc_hjorths( self, chs ):
      if type( chs ) is not list: chs = [ chs ]
      self.segsrv.calc_hjorths( chs );

   def get_bands( self, ch ):
      return self.segsrv.get_bands( ch )

   def get_hjorths( self, ch ):
      return self.segsrv.get_hjorths( ch )
   
   def valid_window( self ):
      return self.segsrv.is_window_valid()

   def is_clocktime( self ):
      return self.segsrv.is_clocktime()

   def get_window_left( self ):
      return self.segsrv.get_window_left()

   def get_window_right( self ):
      return self.segsrv.get_window_right()
   
   def get_window_left_hms( self ):
      return self.segsrv.get_window_left_hms()

   def get_window_right_hms( self ):
      return self.segsrv.get_window_right_hms()

   def get_clock_ticks( self , n = 6 ):
      assert type( n ) is int
      return self.segsrv.get_clock_ticks( n )

   def get_hour_ticks( self ):
      return self.segsrv.get_hour_ticks()

   def get_window_phys_range( self , ch ):
      assert type(ch) is str
      return self.segsrv.get_window_phys_range( ch )
   
   def get_ylabel( self , n ):
      assert type(n) is int
      return self.segsrv.get_ylabel( n )

   def throttle(self,n):
      assert type(n) is int
      self.segsrv.throttle(n)

   def input_throttle(self,n):
      assert type(n) is int
      self.segsrv.input_throttle(n)

   def summary_threshold_mins(self,m):
      assert type(m) is int or type(m) is float
      self.segsrv.summary_threshold_mins(m)

   def get_annots(self):
      return self.segsrv.fetch_annots()

   def get_all_annots(self,anns):
      return self.segsrv.fetch_all_annots(anns)

   def compile_windowed_annots(self,anns):
      self.segsrv.compile_evts( anns )

   def get_annots_xaxes(self,ann):
      return self.segsrv.get_evnts_xaxes( ann )

   def get_annots_yaxes(self,ann):
      return self.segsrv.get_evnts_yaxes( ann )

   def set_annot_format6(self,b):
      self.segsrv.set_evnt_format6(b)
      
   def get_annots_xaxes_ends(self,ann):
      return self.segsrv.get_evnts_xaxes_ends( ann )

   def get_annots_yaxes_ends(self,ann):
      return self.segsrv.get_evnts_yaxes_ends( ann )



# --------------------------------------------------------------------------------
#
# Scope viewer
#
# --------------------------------------------------------------------------------

def scope( p,
           chs = None,
           bsigs = None , 
           hsigs = None,
           anns = None ,
           stgs = [ 'N1' , 'N2' , 'N3' , 'R' , 'W' , '?' , 'L' ] ,
           stgcols = { 'N1':'blue' , 'N2':'blue', 'N3':'navy','R':'red','W':'green','?':'gray','L':'yellow' } ,
           stgns = { 'N1':-1 , 'N2':-2, 'N3':-3,'R':0,'W':1,'?':2,'L':2 } ,
           sigcols = None,
           anncols = None, 
           throttle1_sr = 100 ,
           throttle2_np = 5 * 30 * 100 , 
           summary_mins = 30 ,
           height = 600 ,
           annot_height = 0.15 ,
           header_height = 0.04 ,
           footer_height = 0.01 
          ):

    # defaults
    scope_epoch_sec = 30
    
    # internally, we use 'sigs' but 'chs' is a more lunapi-consistent label
    sigs = chs
    
    # all signals/annotations present    
    all_sigs = p.edf.channels()
    all_annots = p.edf.annots()

    # units
    hdr = p.headers()
    units = dict( zip( hdr.CH , hdr.PDIM ) )
    
    # defaults
    if sigs is None: sigs = all_sigs
    if bsigs is None: bsigs = p.var( 'eeg' ).split(",")
    if hsigs is None: hsigs = p.var( 'eeg' ).split(",")
    if anns is None: anns = all_annots
    
    # ensure we do not have weird channels
    sigs = [x for x in all_sigs if x in sigs]
    bsigs = [x for x in sigs if x in bsigs ]
    hsigs = [x for x in sigs if x in hsigs ]
    anns = [x for x in all_annots if x in anns ]
    sig2n = dict( zip( sigs , list(range(0,len(sigs)))) )

    # empty?
    if len( sigs ) == 0 and len( anns ) == 0:
        print( 'No valid channels or annotations to display')
        return None
    
    # initiate segment-serverns 
    ss = segsrv( p )
    ss.calc_bands( bsigs )
    ss.calc_hjorths( hsigs )
    if type( throttle1_sr ) is int: ss.input_throttle( throttle1_sr )
    if type( throttle2_np ) is int: ss.throttle( throttle2_np )
    if type( summary_mins ) is int or type( summary_mins ) is float: ss.summary_threshold_mins( summary_mins )
    
    ss.populate( chs = sigs , anns = anns )

    # some key variables
    nsecs_clk = ss.num_seconds_clocktime_original()
    epoch_max = int( nsecs_clk / scope_epoch_sec )
    
    # color palette
    pcyc = cycle(px.colors.qualitative.Bold)
    palette = dict( zip( sigs , [ next(pcyc) for i in list(range(0,len(sigs))) ] ) )    
    apalette = dict( zip( anns , [ next(pcyc) for i in list(range(0,len(anns))) ] ) )
    # update w/ any user-specified cols, from anncols = { 'ann':'col' }  
    if sigcols is not None:
        for key, value in sigcols.items(): palette[ key ] = value
    if stgcols is not None:
        for key, value in stgcols.items(): apalette[ key ] = value
    if anncols is not None:
        for key, value in anncols.items(): apalette[ key ] = value
    

    # define widgets

    wlay1 = widgets.Layout( width='95%' ) 
    
    # channel selection box
    chlab = widgets.Label( value = 'Channels:' )
    chbox  = widgets.SelectMultiple( options=sigs, value=sigs, rows=7, description='', disabled=False , layout = wlay1 )
    if len(bsigs) != 0: pow_sel = widgets.Dropdown( options = bsigs, value=bsigs[0],description='',disabled=False,layout = wlay1 )
    else: pow_sel = widgets.Dropdown( options = bsigs, value=None,description="Band power:",disabled=False,layout = wlay1 )
    band_hjorth_sel = widgets.Checkbox( value = True , description = 'Hjorth' , disabled=False, indent=False )
    
    # annotations (display)
    anlab = widgets.Label( value = 'Annotations:' )
    anbox = widgets.SelectMultiple( options=anns , value=[], rows=3, description='', disabled=False , layout = wlay1 )

    # annotations (instance list/navigation)
    a1lab = widgets.Label( value = 'Instances:' )
    ansel = widgets.SelectMultiple( options=anns , value=[], rows=3, description='', disabled=False , layout = wlay1 )
    a1box = widgets.Select( options=[None] , value=None, rows=3, description='', disabled=False , layout = wlay1 )

    # time display labels
    tbox = widgets.Label( value = 'T: ' )
    tbox2 = widgets.Label( value = '' )                                                                                                                                                                                                                      
    tbox3 = widgets.Label( value = '' )                                                                                                                                                                                                                      

    # misc buttons
    reset_button = widgets.Button( description='Reset', disabled=False,button_style='',tooltip='',layout=widgets.Layout(width='98%') )
    keep_xscale = widgets.Checkbox( value = False , description = 'Fixed int.' , disabled=False, indent=False )
    show_ranges = widgets.Checkbox( value = True , description = 'Units' , disabled=False, indent=False )


    # naviation: main slider (top)
    smid = widgets.IntSlider(min=scope_epoch_sec/2, max=nsecs_clk - scope_epoch_sec/2, value=scope_epoch_sec/2, step=30, description='', readout=False,layout=widgets.Layout(width='100%') )
        
    # left panel buttons: interval width
    swid_label = widgets.Label( value = 'Width' )
    swid_dec_button = widgets.Button( description='<', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))
    swid = widgets.Label( value = '30' )
    swid_inc_button = widgets.Button( description='>', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))

    # left panel buttons: left/right advances
    epoch_label = widgets.Label( value = 'Epoch' )
    epoch_dec_button = widgets.Button( description='<', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))
    epoch = widgets.Label( value = '1' )
    epoch_inc_button = widgets.Button( description='>', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))

    # left panel buttons: Y-spacing
    yspace_label = widgets.Label( value = 'Space' )
    yspace_dec_button = widgets.Button( description='<', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))
    yspace = widgets.Label( value = '1' )
    yspace_inc_button = widgets.Button( description='>', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))

    # left panel buttons: Y-scaling
    yscale_label = widgets.Label( value = 'Scale' )
    yscale_dec_button = widgets.Button( description='<', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))
    yscale = widgets.Label( value = '0' )
    yscale_inc_button = widgets.Button( description='>', disabled=False,button_style='',tooltip='', layout=widgets.Layout(width='30px'))


    # --------------------- signal plotter (g)

    # traces (xNS), gaps(x1), labels (xNS), annots(xNA), clock-ticks(x1)
    fig = [go.Scatter(x = None, 
                      y = None, 
                      mode = 'lines',
                      line=dict(color=palette[sig], width=1),
                      hoverinfo='none',
                      name = sig ) for sig in sigs
    ] + [ go.Scatter( x = None , y = None ,
                      mode = 'lines' ,
                      fill='toself' ,
                      fillcolor='#223344',
                      line=dict(color='#888888', width=1),
                      hoverinfo='none',
                      name='Gap' ) 
    ] + [ go.Scatter( x = None , y = None ,
                      mode='text' ,
                      textposition='middle right',
                      textfont=dict(
                          size=11,
                          color='white'),
                      hoverinfo='none' ,
                      showlegend=False ) for sig in sigs 
    ] + [ go.Scatter( x = None , 
                      y = None , 
                      mode = 'lines',
                      fill='toself',
                      line=dict(color=apalette[ann], width=1),
                      hoverinfo='none',
                      name = ann ) for ann in anns
    ] + [ go.Scatter( x = None , y = None ,
                      mode = 'text' ,
                      textposition='bottom right',
                      textfont=dict(
                          size=11,
                          color='white'),
                      hoverinfo='none' ,
                      showlegend=False ) ] 

    
    layout = go.Layout( margin=dict(l=8, r=8, t=0, b=0),
                        yaxis=dict(range=[0,1]),
                        modebar={'orientation': 'v','bgcolor': '#E9E9E9','color': 'white','activecolor': 'white' },
                        yaxis_visible=False, 
                        yaxis_showticklabels=False,
                        xaxis_visible=False,
                        xaxis_showticklabels=False,
                        autosize=True, 
                        height=height,
                        plot_bgcolor='rgb(02,15,50)' ) 

    g = go.FigureWidget(data=fig, layout= layout )
    g._config = g._config | {'displayModeBar': False}
    #g.update_xaxes(showgrid=True, gridwidth=0.1, gridcolor='#445555')
    g.update_xaxes(showgrid=False)
    g.update_yaxes(showgrid=False)
    
    
    # -------------------- segment-plotter (sg)

    num_epochs = ss.num_epochs()
    tscale = ss.get_time_scale()
    tstarts = [ tscale[idx] for idx in range(0,len(tscale),2)]
    tstops = [ tscale[idx] for idx in range(1,len(tscale),2)]
    times = np.concatenate((tstarts, tstops), axis=1)

    # upper/lower boxes, then frame select, then actual segs
    sfig = [ go.Scatter(x=[0,0],y=[0.05,0.05],
                        mode='markers+lines',
                        marker=dict(color="navy",size=8)) 
            ] + [ go.Scatter(x=[0,0],y=[0.95,0.95],
                        mode='markers+lines',
                        marker=dict(color="navy",size=8))                             
            ] + [ go.Scatter(x=[0,0,0,0,0,None],y=[0,0,1,1,0,None],
                        mode='lines',
                        fill='toself',
                        fillcolor = 'rgba( 18, 65, 92, 0.75)' ,
                        line=dict(color="red",width=0.5)) 
            ] + [ go.Scatter(x=[x[1],x[1],x[3],x[3]],y=[0,1,1,0],   # was 0 1 3 2 
                        fill="toself",
                        mode = 'lines',
                        hoverinfo = 'none',
                        line=dict(color='rgb(19,114,38)', width=1), ) for x in times ]

    slayout = go.Layout( margin=dict(l=8, r=8, t=2, b=4),
                         showlegend=False,
                         xaxis=dict(range=[0,1]),
                         yaxis=dict(range=[0,1]),
                         yaxis_visible=False, 
                         yaxis_showticklabels=False,
                         xaxis_visible=False, 
                         xaxis_showticklabels=False,                         
                         autosize=True, 
                         height=15,
                         plot_bgcolor='rgb(255,255,255)' ) 

    sg = go.FigureWidget( data=sfig, layout=slayout )
    sg._config = sg._config | {'displayModeBar': False}

    # --------------------- hypnogram-level summary

    stgs = [ 'N1' , 'N2' , 'N3' , 'R' , 'W' , '?' , 'L' ]
    stgcols = { 'N1':'rgba(32, 178, 218, 1)' , 'N2':'blue', 'N3':'navy','R':'red','W':'green','?':'gray','L':'yellow' }
    stgns = { 'N1':-1 , 'N2':-2, 'N3':-3,'R':0,'W':1,'?':2,'L':2 }

    # clock-time stage info (in units no larger than 30 seconds)
    stg_evts = p.fetch_annots( stgs , 30 ) 
    if len( stg_evts ) != 0:
         stg_evts2 = stg_evts.copy()
         stg_evts2[ 'Start' ] = stg_evts2[ 'Stop' ]
         stg_evts[ 'IDX' ] = range(len(stg_evts))
         stg_evts2[ 'IDX' ] = range(len(stg_evts)) 
         stg_evts = pd.concat( [stg_evts2, stg_evts] )
         stg_evts = stg_evts.sort_values(by=['Start', 'IDX'])
         times = stg_evts['Start'].to_numpy()    
         ys = [ stgns[c] for c in stg_evts['Class'].tolist() ]
         cols = [ stgcols[c] for c in stg_evts['Class'].tolist() ]
    else:
        times = None
        ys = None
        cols = None
        
    hypfig = [ go.Scatter( x = times, y=ys, mode='lines', line=dict(color='gray')) ]  
    
    hypfig.append( go.Scatter(x = times, 
                              y = ys , 
                              mode = 'markers' , 
                              marker=dict( color = cols , size=2),                              
                              hoverinfo='none' )  )
    
    hyplayout =  go.Layout( margin=dict(l=8, r=8, t=0, b=0),
                            showlegend=False,
                            xaxis=dict(range=[0,nsecs_clk]),
                            yaxis=dict(range=[-4,3]),
                            yaxis_visible=False, 
                            yaxis_showticklabels=False,
                            xaxis_visible=False, 
                            xaxis_showticklabels=False,
                            autosize=True, 
                            height=35,
                            plot_bgcolor='rgb(255,255,255)' ) 
         
    hypg = go.FigureWidget( data = hypfig , layout = hyplayout )
    hypg._config = hypg._config | {'displayModeBar': False}


    # --------------------- band power/spectrogram (bg)
    
    #bfig = go.Heatmap( z = None , type = 'heatmap',  colorscale = 'RdBu_r', showscale = False , hoverinfo = 'none' )
    bfig = go.Heatmap( z = None , type = 'heatmap',  colorscale = 'turbo', showscale = False , hoverinfo = 'none' )
    
    blayout = go.Layout( margin=dict(l=8, r=8, t=0, b=0),
                         modebar={'orientation': 'h','bgcolor': '#E9E9E9','color': 'white','activecolor': 'white' },
                         showlegend=False,
                         yaxis_visible=False, 
                         yaxis_showticklabels=False,
                         xaxis_visible=False, 
                         xaxis_showticklabels=False,
                         autosize=True,                          
                         height=50,
                         plot_bgcolor='rgb(255,255,255)' ) 
    
    bg = go.FigureWidget( bfig , blayout )
    bg._config = bg._config | {'displayModeBar': False}


    # --------------------- build overall box (containerP)

    # ----- containers - left panel

    ctr_lab_container = widgets.VBox(children=[ swid_label , epoch_label, yspace_label , yscale_label  ] ,
                                     layout = widgets.Layout( width='30%', align_items='center' , display='flex', flex_flow='column' ) )
                                 
    ctr_dec_container = widgets.VBox(children=[ swid_dec_button , epoch_dec_button, yspace_dec_button , yscale_dec_button  ] ,
                                     layout = widgets.Layout( width='20%', align_items='center' , display='flex', flex_flow='column' ))
                                 
    ctr_val_container = widgets.VBox(children=[ swid , epoch , yspace , yscale  ] ,
                                     layout = widgets.Layout( width='30%', align_items='center' , display='flex', flex_flow='column' ))
                                 
    ctr_inc_container = widgets.VBox(children=[ swid_inc_button ,  epoch_inc_button, yspace_inc_button , yscale_inc_button ] ,
                                     layout = widgets.Layout( width='20%', align_items='center' , display='flex', flex_flow='column' ))

    # left panel: group top set of widgets
    ctr_container = widgets.VBox( children=[ tbox, widgets.HBox(children=[ ctr_lab_container, ctr_dec_container, ctr_val_container, ctr_inc_container ] ) , reset_button ] ,
                                  layout = widgets.Layout( width='100%' ) )

    # left panel: lower buttons
    lower_buttons = widgets.HBox( children=[ keep_xscale , show_ranges ] ,
                                  layout = widgets.Layout( width='100%' ) )

    # left panel: construct all
    left_panel = widgets.VBox(children=[ ctr_container,
                                         chlab, chbox,
                                         widgets.HBox( children = [ band_hjorth_sel, pow_sel ] ),
                                         anlab, anbox, a1lab, ansel, a1box,
                                         lower_buttons ] ,
                              layout = widgets.Layout( width='95%' , margin='0 0 0 5px' , overflow_x = 'hidden' ) )

    # right panel: combine plots
    containerS = widgets.VBox(children=[ smid , hypg, sg, bg, g ] , layout = widgets.Layout( width='95%' , margin='0 5px 0 5px' , overflow_x = 'hidden' ) )
    
    # make the final app (just join left+right panels)
    container_app = AppLayout(header=None,
                              left_sidebar=left_panel,
                              center=containerS,
                              right_sidebar=None,
                              pane_widths=[1, 8, 0],
                              align_items = 'stretch' ,
                              footer=None , layout = widgets.Layout( border='3px none #708090' , margin='10px 5px 10px 5px' , overflow_x = 'hidden' ) )

    
    # --------------------- callback functions
        
    def redraw():

        # update hms message
        tbox.value = 'T: ' + ss.get_window_left_hms() + ' - ' + ss.get_window_right_hms()

        # get annots
        ss.compile_windowed_annots( anbox.value )
 
        x1 = ss.get_window_left()
        x2 = ss.get_window_right()

        # update pointers on segment plot
        s1 = x1 / nsecs_clk
        s2 = x2 / nsecs_clk
        sg.data[0].x = [ s1, s2 ]
        sg.data[1].x = [ s1, s2 ]
        sg.data[2].x = [ s1 , s2 , s2 , s1 , s1 , None ]

        # update main plot
        with g.batch_update():
            ns = len(sigs)
            na = len(anns)

            # axes
            g.update_xaxes(range = [x1,x2])
            
            # signals (0)
            selected = [ x in chbox.value for x in sigs ]
            idx=0
            for i in list(range(0,ns)):
                if selected[i] is True:
                    g.data[i].x = ss.get_timetrack( sigs[i] )
                    g.data[i].y = ss.get_scaled_signal( sigs[i] , idx )
                    g.data[i].visible = True
                    idx += 1
                else:
                    g.data[i].visible = False

            # gaps (last trace)
            gidx = ns
            gaps = list( ss.get_gaps() )
            if len(gaps) == 0:
                g.data[ gidx ].visible = False
            else:
                # make into 6-value formats
                xgaps = [(a, b, b, a, a, None ) for a, b in gaps ]
                ygaps = [(0, 0, 1-header_height, 1-header_height, 0, None ) for a, b in gaps ]
                g.data[ gidx ].x = [x for sub in xgaps for x in sub]
                g.data[ gidx ].y = [y for sub in ygaps for y in sub]
                g.data[ gidx ].visible = True

            # ranges? (+ns)
            if show_ranges.value is True:
                idx=0
                xl = x1 + (x2-x1 ) * 0.01 
                for i in list(range(0,ns)):
                    if selected[i] is True:
                        ylim = ss.get_window_phys_range( sigs[i] )
                        ylab = sigs[i] + ' ' + str(round(ylim[0],3)) + ':' + str(round(ylim[1],3)) + ' (' + units[sigs[i]] +')'
                        g.data[i+ns+1].x = [ xl ]
                        g.data[i+ns+1].y = [ ss.get_ylabel( idx ) * (1 - header_height ) ]
                        g.data[i+ns+1].text = [ ylab ]
                        g.data[i+ns+1].visible = True
                        idx += 1
                    else:
                        g.data[i+ns+1].visible = False
 

            # annots (+2ns + gap)
            ns2 = 2 * ns + 1
            selected = [ x in anbox.value for x in anns ]
            for i in list(range(0,na)):
                if selected[i] is True:
                    g.data[i+ns2].x = ss.get_annots_xaxes( anns[i] )
                    g.data[i+ns2].y = ss.get_annots_yaxes( anns[i] )
                    g.data[i+ns2].visible = True
                else:
                    g.data[i+ns2].visible = False

            # clock-ticks
            gidx = 2 * ns + na + 1
            tks = ss.get_clock_ticks(6)
            tx = list( tks.keys() )
            tv = list( tks.values() )
            if len( tx ) == 0:
                g.data[ gidx ].visible = False
            else:
                g.data[ gidx ].x = tx 
                g.data[ gidx ].y = [ 1 - header_height + ( header_height ) * 0.5 for x in tx ]
                g.data[ gidx ].text = tv
                g.data[ gidx ].visible = True

    def rescale(change):
       ss.set_scaling( len(chbox.value) , len( anbox.value) , 2**float(yscale.value) , float(yspace.value) , header_height, footer_height , annot_height )
       redraw()
    
    def update_bandpower(change):
        if pow_sel.value is None: return 
        if len( pow_sel.value ) == 0: return
        if band_hjorth_sel.value is True:
           S = np.transpose( ss.get_hjorths( pow_sel.value ) )
           S = np.asarray(S,dtype=object)
           S[np.isnan(S.astype(np.float64))] = None
           bg.update_traces({'z': S } , selector = {'type':'heatmap'} )
        else:
           S = np.transpose( ss.get_bands( pow_sel.value ) )
           S = np.asarray(S,dtype=object)
           S[np.isnan(S.astype(np.float64))] = None
           bg.update_traces({'z': S } , selector = {'type':'heatmap'} )

    def pop_a1(change):
        a1box.options = ss.get_all_annots( ansel.value )

    def a1_win(change):
        # format <annot> | t1-t2 (seconds)
        # allow for pipe in <annot> name
        nwin = a1box.value.split( '| ')[-1]
        nwin = nwin.split('-')
        nwin = [ float(x) for x in nwin ]

        # center on mid of annot
        mid = nwin[0] + ( nwin[1] - nwin[0] ) / 2

        # width: either based on annot, or keep as is
        if keep_xscale.value is False:
            swid.unobserve(set_window_from_sliders, names="value")
            swid.value = str( round( nwin[1] - nwin[0] , 2 ) )
            swid.observe(set_window_from_sliders, names="value")
            
        # update smid, and trigger redraw via set_window_from_sliders()
        smid.value = mid

    def set_window_from_sliders(change):
        w = float( swid.value )
        p1 = smid.value - 0.5 * w
        if p1 < 0: p1 = 0
        p2 = p1 + w
        if p2 >= ss.num_seconds_clocktime():
            p2 = ss.num_seconds_clocktime() - 1 
        ss.window( p1 , p2 )
        epoch.value = str(1+int(smid.value/30))
        redraw()

    def fn_reset(b):
        swid.value = str( 30 )
        yspace.value = str( 1 )
        yscale.value = str( 0 )
                
    def fn_dec_epoch(b):
        if ( smid.value - scope_epoch_sec ) >= smid.min :
            smid.value = smid.value - scope_epoch_sec

    def fn_inc_epoch(b):
        if ( smid.value + scope_epoch_sec ) <= smid.max :
            smid.value = smid.value + scope_epoch_sec
        
    def fn_dec_swid(b):
        swid_var = float( swid.value )
        if swid_var > 3.5: swid_var = swid_var / 2
        if swid_var > 100: swid.value = str( int( swid_var ))
        else: swid.value = str( swid_var )

    def fn_inc_swid(b):
        swid_var = float( swid.value )
        if swid_var < 40000: swid_var = swid_var * 2
        if swid_var > 100: swid.value = str( int( swid_var ) )
        else: swid.value = str( swid_var )

    def fn_yspace_dec(b):
        yspace_var = float( yspace.value )
        if yspace_var > 0.05: yspace_var = yspace_var - 0.1
        yspace.value = str( round( yspace_var , 1 ) )

    def fn_yspace_inc(b):
        yspace_var = float( yspace.value )
        if yspace_var < 0.95: yspace_var = yspace_var + 0.1
        yspace.value = str( round( yspace_var , 1 ) )
        
    def fn_yscale_dec(b):
        yscale_var = float( yscale.value )
        if yscale_var > -2: yscale_var = yscale_var - 0.2
        yscale.value = str( round( yscale_var , 1 ) )

    def fn_yscale_inc(b):
        yscale_var = float( yscale.value )
        if yscale_var < 2: yscale_var = yscale_var + 0.2
        yscale.value = str( round( yscale_var , 1 ) )

    def fn_hjorth_band(b):
        if band_hjorth_sel.value is True:
           pow_sel.options = hsigs
        else:
           pow_sel.options = bsigs
        
    # --------------------- hook up widgets

    # observers
    smid.observe(set_window_from_sliders, names="value")
    swid.observe(set_window_from_sliders, names="value")

    show_ranges.observe(set_window_from_sliders)

    band_hjorth_sel.observe( fn_hjorth_band )
    
    swid_dec_button.on_click(fn_dec_swid)
    swid_inc_button.on_click(fn_inc_swid)

    epoch_dec_button.on_click(fn_dec_epoch)
    epoch_inc_button.on_click(fn_inc_epoch)

    reset_button.on_click(fn_reset)
                          
    # summaries
    pow_sel.observe(update_bandpower,names="value")

    # rescale plots
    yscale_dec_button.on_click( fn_yscale_dec )
    yscale_inc_button.on_click( fn_yscale_inc )
    yspace_dec_button.on_click( fn_yspace_dec )
    yspace_inc_button.on_click( fn_yspace_inc )

    yscale.observe( rescale , names="value")
    yspace.observe( rescale , names="value")
    

    # channel selection
    chbox.observe( rescale ,names="value")

    # annots
    anbox.observe( rescale , names="value")
    ansel.observe( pop_a1 , names="value")
    a1box.observe( a1_win , names="value")

    
    # ---------------------  display
    update_bandpower(None)
    ss.set_scaling( len(chbox.value) , len( anbox.value) , 2**float(yscale.value) , float(yspace.value) , header_height, footer_height , annot_height )

    ss.window( 0 , 30 )
    epoch.value = str(1);

    redraw()
    return container_app


# --------------------------------------------------------------------------------
# moonbeam

class moonbeam:
   """Moonbeam utility to pull NSRR data"""

   df1 = None  # available cohorts
   df2 = None  # available files for current cohort
   curr_cohort = None
   
   def __init__(self, nsrr_tok , cdir = None ):
      """ Initiate Moonbeam with an NSRR token """
      self.nsrr_tok = nsrr_tok
      self.df1 = self.cohorts()
      if cdir is None: cdir = os.path.join( tempfile.gettempdir() , 'luna-moonbeam' )
      self.set_cache(cdir)

   def set_cache(self,cdir):
      """ Set the folder for caching downloaded records """
      self.cdir = cdir
      print( 'using cache folder for downloads: ' + self.cdir )
      os.makedirs( os.path.dirname(self.cdir), exist_ok=True)

   def cached(self,file):
      """ Check whether a file is already cached """ 
      return os.path.exists( os.path.join( self.cdir , file ) )

   def cohorts(self):
      """ List all available cohorts accessible from the given NSRR user token """ 
      req = requests.get( 'https://zzz.bwh.harvard.edu/cgi-bin/moonbeam.cgi?t=' + self.nsrr_tok ).content
      self.df1 = pd.read_csv(io.StringIO(req.decode('utf-8')),sep='\t',header=None)
      self.df1.columns = ['Cohort','Description']
      return self.df1

   def cohort(self,cohort1):
      """ List all files (EDFs and annotations) available for a given cohort """
      if type(cohort1) is int: cohort1 = self.df1.loc[cohort1,'Cohort']
      if type(cohort1) is not str: return
      self.curr_cohort = cohort1
      req = requests.get( 'https://zzz.bwh.harvard.edu/cgi-bin/moonbeam.cgi?t=' + self.nsrr_tok + "&c=" + cohort1).content
      df = pd.read_csv(io.StringIO(req.decode('utf-8')),sep='\t',header=None)
      df.columns = [ 'cohort' , 'IID' , 'file' ]

      #  get EDFs, annots then merge
      df_edfs = df[ df['file'].str.contains(".edf$|.edf.gz$" , case = False ) ][[ 'IID' , 'file' ]]
      df_annots = df[ ~ df['file'].str.contains(".edf$|.edf.gz$" , case = False ) ][[ 'IID' , 'file' ]]
      self.df2 = pd.merge( df_edfs , df_annots , on='IID' , how='left' )
      self.df2.columns = [ 'ID' , 'EDF' , 'Annot' ]
      return self.df2

   
   def inst(self, iid ):
      """ Create an instance of a record, either downloaded or cached """
      if self.df2 is None: return
      if self.curr_cohort is None: return
      
      # ensure we have this file 
      self.pull( iid , self.curr_cohort )

      # ensure we have a proj (from proj singleton)
      proj1 = proj(False)
      p = proj1.inst( self.curr_id )
      edf1 = str( pathlib.Path( self.cdir ).joinpath( self.curr_edf ).expanduser().resolve() )      
      p.attach_edf( edf1 ) 
      
      if self.curr_annot is not None:
         annot1 = str( pathlib.Path( self.cdir ).joinpath( self.curr_annot ).expanduser().resolve() )
         p.attach_annot( annot1 )

      # return handle back
      return p

    
   def pull(self, iid , cohort ):
      """ Download an individual record (if not already cached) """      
      if self.df2.empty: return False

      # iid
      if type(iid) is int: iid = self.df2.loc[iid,'ID']
      self.curr_id = iid

      # EDF
      self.curr_edf = self.df2.loc[ self.df2['ID'] == iid,'EDF'].item()
      self.pull_file( self.curr_edf )

      # EDFZ .idx
      if re.search(r'\.edf\.gz$',self.curr_edf,re.IGNORECASE) or re.search(r'\.edfz$',self.curr_edf,re.IGNORECASE):
         self.pull_file( self.curr_edf + '.idx' )

      # annots (optional)
      self.curr_annot = self.df2.loc[ self.df2['ID'] == iid,'Annot'].item()
      if self.curr_annot is not None:
         self.pull_file( self.curr_annot )

   def pull_file( self , file ):
      import functools
      import pathlib
      import shutil
      import requests
      from tqdm.auto import tqdm

      if self.cached( file ) is True: 
          print( file + ' is already cached' )
          return

      # save file to cdir/{path/}file, e.g. path will be cohort
      path = pathlib.Path( self.cdir ).joinpath( file ).expanduser().resolve() 
      path.parent.mkdir(parents=True, exist_ok=True)

      print( '\nbeaming ' + self.curr_id + ' : ' + file  )

      url = 'https://zzz.bwh.harvard.edu/cgi-bin/moonbeam.cgi?t=' + self.nsrr_tok + "&f=" + file    
      r = requests.get(url, stream=True, allow_redirects=True)

      if r.status_code != 200:
         r.raise_for_status()  # Will only raise for 4xx codes, so...
         raise RuntimeError(f"Request to {url} returned status code {r.status_code}")
      file_size = int(r.headers.get('Content-Length', 0))

      desc = "(Unknown total file size)" if file_size == 0 else ""
      r.raw.read = functools.partial(r.raw.read, decode_content=True)  # Decompress if needed
      with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc) as r_raw:
          with path.open("wb") as f:
              shutil.copyfileobj(r_raw, f)


   def pheno(self, cohort = None, iid = None):
      """ Pull phenotypes for a given individual """

      coh1 = cohort
      id1 = iid

      if coh1 is None:
         if self.curr_cohort is None: return
         coh1 = self.curr_cohort
         
      if id1 is None:
         if self.curr_id is None: return
         id1 = self.curr_id
            
      url = 'https://zzz.bwh.harvard.edu/cgi-bin/moonbeam.cgi?t=' + self.nsrr_tok + '&c=' + self.curr_cohort + '&p=' + id1 
      req = requests.get( url )

      if req.status_code != 200:
         req.raise_for_status()  # Will only raise for 4xx codes, so...
         raise RuntimeError(f"Moonbeam returned status code {req.status_code}")
      
      df = pd.read_csv(io.StringIO(req.content.decode('utf-8')),sep='\t',header=None)
      df.columns = ['Variable', 'Value', 'Units', 'Description' ]
      pri = [ "nsrr_age", "nsrr_sex", "nsrr_bmi", "nsrr_flag_spsw", "nsrr_ahi_hp3r_aasm15", "nsrr_ahi_hp4u_aasm15" ] 
      df1 = df[   df['Variable'].isin( pri ) ]
      df2 = df[ ~ df['Variable'].isin( pri ) ] 
      df = pd.concat( [ df1 , df2 ] )
      return df



