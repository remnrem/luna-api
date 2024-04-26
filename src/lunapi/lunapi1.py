"""lunapi1 module provides a high-level convenience wrapper around lunapi0 module functions."""

# Luna Python wrapper
# v0.0.6, 26-Apr-2024

import lunapi.lunapi0 as _luna
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from IPython.core import display as ICD
from scipy.stats.mstats import winsorize

# resource set for Docker container version
class resources:
   POPS_PATH = '/build/nsrr/common/resources/pops/'
   POPS_LIB = 's2'
   MODEL_PATH = '/build/luna-models/'

lp_version = "v0.0.6"
   
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

      df : boolean
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
      
   def reset(self):
      """ Drop Luna problem flag """
      proj.eng.reset()

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

   #------------------------------------------------------------------------
   def var(self,key=None,value=None):
      """Set or return a project-level argument/option"""
      if key == None:
         return proj.eng.get_all_opts()
      if value == None:
         if type(key) is not list: key = [ key ]
         return proj.eng.get_opt( key )
      else:         
         proj.eng.opt( key, str( value ) )

   #------------------------------------------------------------------------                                                                                                                                                            
   def varmap(self,d):
      """Sets project-level arguments/options"""
      if isinstance(d, dict):
         for k, v in d.items():
            self.var(k,v)
         
   #------------------------------------------------------------------------
   def vars(self):
      """Return a dictionary of all project-level variables"""
      return proj.eng.get_all_opts()

   
   #------------------------------------------------------------------------
   def clear_var(self,key):
      """Clear a project-level option/variable"""
      proj.eng.clear_opt(key)

   #------------------------------------------------------------------------
   def clear_vars(self,key):
      """Clear a project-level option/variable"""
      if type(key) is not list: key = [ key ]
      proj.eng.clear_opts(key)

   #------------------------------------------------------------------------
   def clear_all_vars(self):
      """Clear all project-level options/variables"""
      proj.eng.clear_all_opts()

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
      if s == None:
         return proj.eng.import_db(f)
      else:
         return proj.eng.import_db_subset(f,s)

   #------------------------------------------------------------------------      
   def eval(self, cmdstr ):
      """Evaluates one or more Luna commands for all sample-list individuals"""
      r = proj.eng.eval(cmdstr)
      return tables( r )

   #------------------------------------------------------------------------ 
   def silent_eval(self, cmdstr ):
      """Silently evaluates one or more Luna commands for all sample-list individuals"""
      silence_mode = self.is_silenced()
      self.silence(True,False)
      r = proj.eng.eval(cmdstr)
      self.silence( silence_mode , False )
      return tables( r )
   
   
   #------------------------------------------------------------------------   
   def commands( self ):
      """Return a list of commands in the output set (following eval()"""
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
      t.columns = ["Command","Stratum"]
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

      if path == None: path = resources.POPS_PATH
      if lib == None: lib = resources.POPS_LIB
      
      import os
      if not os.path.isdir( path ):         
         return 'could not open POPS resource path ' + path 

      if s == None and s1 == None:
         print( 'must set s or s1 and s2 to EEGs' )
         return

      if ( s1 == None ) != ( s2 == None ):
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
      
      if s != None: self.var( 's' , s )
      else: self.clear_var( 's' )
      
      if m != None: self.var( 'm' , m )
      else: self.clear_var( 'm' )

      if s1 != None: self.var( 's1' , s1 )
      else: self.clear_var( 's1' )
      
      if s2 != None: self.var( 's2' , s2 )
      else: self.clear_var( 's2' )
      
      if m1 != None: self.var( 'm1' , m1 )
      else: self.clear_var( 'm1' )
      
      if m2 != None: self.var( 'm2' , m2 )
      else: self.clear_var( 'm2' )
            
      # get either one- or two-channel mode Luna script from POPS folder
      twoch = s1 != None and s2 != None;
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
      self.eval( cmdstr )

      # return of results
      return self.table( 'POPS' )


   # --------------------------------------------------------------------------------
   def predict_SUN2019( self, cen , th = '3' , path = None ):
      """Run SUN2019 prediction model for a project

      This assumes that ${age} will be set via a vars file, i.e.

         proj.opt( 'vars' , 'ages.txt' )      

      """
      if path == None: path = resources.MODEL_PATH
      if type( cen ) is list: cen = ','.join( cen )
      self.var( 'cen' , cen )
      self.var( 'mpath' , path )
      self.var( 'th' , str(th) )
      self.eval( cmdfile( resources.MODEL_PATH + '/m1-adult-age-luna.txt' ) )
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
   def ivar( self , key , value = None ):
      """Set or get an individual-level variable"""
      if value != None: self.edf.ivar( key , str(value) )
      else: return self.edf.get_ivar( key )
         
   #------------------------------------------------------------------------                                                                                                                                                            
   def ivarmap(self,d):
      """Sets individual-level variables"""
      if isinstance(d, dict):
         for k, v in d.items():
            self.ivar(k,v)

   #------------------------------------------------------------------------      
   def ivars( self ):
      """Return all individual-level variables"""
      return self.edf.ivars()

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
      df = self.proc( "HEADERS" )[ 'HEADERS: CH' ]
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
   def eval( self, cmdstr ):
      """Evaluate one or more Luna commands, storing results internally"""
      self.edf.eval( cmdstr )
      return self.strata()
      
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
      t.columns = ["Command","Stratum"]
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
      return self.edf.e2i( epochs )
   
   # --------------------------------------------------------------------------------
   def s2i( self, secs ):
      """Helper function to convert seconds to intervals"""
      return self.edf.s2i( secs )

   # --------------------------------------------------------------------------------
   def data( self, chs , annots = None , time = False ):
      """Returns all data for certain channels and annotations"""
      if type( chs ) is not list: chs = [ chs ]
      if annots != None:
         if type( annots ) is not list: annots = [ annots ]
      if annots == None: annots = [ ]
      return self.edf.data( chs , annots , time )

   # --------------------------------------------------------------------------------
   def slice( self, intervals, chs , annots = None , time = False ):
      """Return signal/annotation data aggregated over a set of intervals"""
      if type( chs ) is not list: chs = [ chs ]
      if annots != None:
         if type( annots ) is not list: annots = [ annots ]
      if annots == None: annots = [ ]
      return self.edf.slice( intervals, chs , annots , time )

   # --------------------------------------------------------------------------------   
   def slices( self, intervals, chs , annots = None , time = False ):
      """Return a series of signal/annotation data objects for each requested interval"""
      if type( chs ) is not list: chs = [ chs ]
      if annots != None:
         if type( annots ) is not list: annots = [ annots ]
      if annots == None: annots = [ ]
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
      if f == None: return
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
   def psd( self, ch, var = 'PSD' , minf = None, maxf = None, minp = None, maxp = None , xlines = None , ylines = None ):
      """Generates a PSD plot (from PSD or MTM)"""
      if ch == None: return
      if type(ch) is not list: ch = [ ch ]

      if var == 'PSD':
         self.eval( 'PSD spectrum dB sig=' + ','.join(ch) )
         df = self.table( 'PSD' , 'CH_F' )
      else:
         self.eval( 'MTM tw=15 dB sig=' + ','.join(ch) )
         df = self.table( 'MTM' , 'CH_F' )
         
      psd( df = df , ch = ch , var = var ,
           minf = minf , maxf = maxf , minp = minp , maxp = maxp ,
           xlines = xlines , ylines = ylines )
      
    
   # --------------------------------------------------------------------------------
   def spec( self, ch, var = 'PSD' , mine = None, maxe = None, minf = None, maxf = None , w = 0.025 ):
      """Generates a PSD spectrogram (from PSD or MTM)"""
      if ch == None: return
      if type(ch) is not list: ch = [ ch ]

      if var == 'PSD':
         self.eval( 'PSD epoch-spectrum dB sig=' + ','.join(ch) )
         df = self.table( 'PSD' , 'CH_E_F' )
      else:
         self.eval( 'MTM epoch-spectra epoch epoch-output dB tw=15 sig=' + ','.join(ch) )
         df = self.table( 'MTM' , 'CH_E_F' )
         
      spec( df = df , ch = None , var = var ,
            mine = mine , maxe = maxe , minf = minf , maxf = maxf , w = w )
   
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

      if path == None: path = resources.POPS_PATH
      if lib == None: lib = resources.POPS_LIB
      
      import os
      if not os.path.isdir( path ):         
         return 'could not open POPS resource path ' + path 

      if s == None and s1 == None:
         print( 'must set s or s1 and s2 to EEGs' )
         return

      if ( s1 == None ) != ( s2 == None ):
         print( 'must set s or s1 and s2 to EEGs' )
         return
         
      # set options
      self.ivar( 'mpath' , path )
      self.ivar( 'lib' , lib )
      self.ivar( 'do_edger' , '1' if do_edger else '0' )
      self.ivar( 'do_reref' , '1' if do_reref else '0' )
      self.ivar( 'no_filter' , '1' if no_filter else '0' )
      self.ivar( 'LOFF' , lights_off )
      self.ivar( 'LON' , lights_on )

      if s != None: self.ivar( 's' , s )
      if m != None: self.ivar( 'm' , m )
      if s1 != None: self.ivar( 's1' , s1 )
      if s2 != None: self.ivar( 's2' , s2 )
      if m1 != None: self.ivar( 'm1' , m1 )
      if m2 != None: self.ivar( 'm2' , m2 )
      
      # get either one- or two-channel mode Luna script from POPS folder
      twoch = s1 != None and s2 != None;
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
      if path == None: path = resources.MODEL_PATH
      if type( cen ) is list : cen = ','.join( cen )
      
      # set ivars
      if age == None:
         print( 'need to set age ivar' )
         return
      self.ivar( 'age' , str(age) )
      self.ivar( 'cen' , cen )
      self.ivar( 'mpath' , path )
      self.ivar( 'th' , str(th) )
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
      """Returns boolean for whether staging is present"""
      _proj = proj(False)
      silence_mode = _proj.is_silenced()
      _proj.silence(True,False)
      res = self.edf.has_staging()
      _proj.silence( silence_mode , False )
      return res

   # --------------------------------------------------------------------------------
   def has_annots(self,anns):
      """Returns boolean for which annotations are present"""
      if anns == None: return
      if type( anns ) is not list: anns = [ anns ]
      return self.edf.has_annots( anns )

   # --------------------------------------------------------------------------------
   def has_annot(self,anns):
      """Returns boolean for which annotations are present"""
      return self.has_annots(anns)

   # --------------------------------------------------------------------------------
   def has_channels(self,ch):
      """Return a boolean to indicate whether a given channel exists"""
      if ch == None: return
      if type(ch) is not list: ch = [ ch ]
      return self.edf.has_channels( ch )

   # --------------------------------------------------------------------------------
   def has(self,ch):
      """Return a boolean to indicate whether a given channel exists"""
      if ch == None: return
      if type(ch) is not list: ch = [ ch ]
      return self.edf.has_channels( ch )

   # --------------------------------------------------------------------------------                                                                  
   def spec(self,ch,mine = None , maxe = None , minf = None, maxf = None, w = 0.025 ):
      """PSD given channel 'ch'"""
      if type( ch ) is not str:
         return
      if all( self.has( ch ) ) is not True:
         return
      res = self.silent_proc( "PSD epoch-spectrum dB sig="+ch )[ 'PSD: CH_E_F' ]
      return spec( res , ch=ch, var='PSD', mine=mine,maxe=maxe,minf=minf,maxf=maxf,w=w)

   # --------------------------------------------------------------------------------
   def psd(self, ch, minf = None, maxf = None, minp = None, maxp = None , xlines = None , ylines = None ):
      """Spectrogram plot for a given channel 'ch'"""
      if type( ch ) is not str:
         return
      if all( self.has( ch ) ) is not True:
         return
      res = self.silent_proc( "PSD spectrum dB sig="+ch )[ 'PSD: CH_F' ]
      return psd( res , ch, minf = minf, maxf = maxf, minp = minp, maxp = maxp , xlines = xlines , ylines = ylines )

      
# --------------------------------------------------------------------------------
#
# misc non-member utilities functions
#
# --------------------------------------------------------------------------------


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
   t.columns = ["Command","Stratum"]
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
   for cmd in ts:
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
    if e == None: e = np.arange(0, len(ssn), 1)
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
    if ch == None: return
    if type( ch ) is not list: ch = [ ch ]
    if type( xlines ) is not list and xlines != None: xlines = [ xlines ]
    if type( ylines ) is not list and ylines != None: ylines = [ ylines ]
    df = df[ df['CH'].isin(ch) ]
    if len(df) == 0: return
    f = df['F'].to_numpy(dtype=float)
    p = df[var].to_numpy(dtype=float)
    if dB is True: p = 10*np.log10(p)
    cx = df['CH'].to_numpy(dtype=str)
    if minp == None: minp = min(p)
    if maxp == None: maxp = max(p)
    if minf == None: minf = min(f)
    if maxf == None: maxf = max(f)
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
    if xlines != None: [plt.axvline(_x, linewidth=1, color='gray') for _x in xlines ]
    if ylines != None: [plt.axhline(_y, linewidth=1, color='gray') for _y in ylines ]
    plt.show()


# --------------------------------------------------------------------------------
def spec(df , ch = None , var = 'PSD' , mine = None , maxe = None , minf = None, maxf = None, w = 0.025 ):
    """Returns a spectrogram from a PSD or MTM epoch table (CH_E_F)"""
    if ch != None: df = df.loc[ df['CH'] == ch ]
    if len(df) == 0: return
    x = df['E'].to_numpy(dtype=int)
    y = df['F'].to_numpy(dtype=float)
    z = df[ var ].to_numpy(dtype=float)
    if mine == None: mine = min(x)
    if maxe == None: maxe = max(x)
    if minf == None: minf = min(y)
    if maxf == None: maxf = max(y)
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
    if ths != None: ths = np.array(ths)
    if topo == None: topo = default_xy()

    xlim = [-0.6, 0.6]
    ylim = [-0.6, 0.6]
    rng = [np.min(z), np.max(z)]

    if lmts == None : lmts = rng
    else: assert lmts[0] <= rng[0] <= lmts[1] and lmts[0] <= rng[1] <= lmts[1], "channel values are out of specified limits"
   
    assert len(set(topo['CH']).intersection(chs)) > 0, "no matching channels"
    
    chs = chs.apply(lambda x: x.upper())    
    topo = topo[topo['CH'].isin(chs)]
    topo["vals"] = np.nan
    topo["th_vals"] = np.nan
    topo["rims"] = 0.5

    for ix, ch in topo.iterrows():
        topo.loc[ix,'vals'] = z[chs == ch["CH"]]
        if ths == None:
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
   
