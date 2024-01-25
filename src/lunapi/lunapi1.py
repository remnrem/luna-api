"""lunapi1 module provides a high-level convenience wrapper around lunapi0 module functions."""

# Luna Python wrapper
# v0.1, 21-Jan-2024

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

lp_version = "v0.0.4"
   
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
   
   def __init__(self):
      self.n = 0
      print( "initiated lunapi",lp_version,proj.eng ,"\n" )
      self.silence( False )
      self.eng = _luna.inaugurate()
      
   def retire():
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

   
   def sample_list(self, filename = None ):
      """Reads a sample-list 'filenamne' and returns the number of observations

      If filename is not defined, this returns the internal sample list
      as an object

      Parameters
      ----------
      filename : str
          optional filename of a sample-list to read

      Returns
      -------
      list
          a list of strings representing the sample-list (IDs, EDFs, annotations for each individual)
      """
    
      # return sample list
      if filename is None:
         return proj.eng.get_sample_list()

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
   
   def inst( self, n ):
      """Generates a new instance"""
      
      return inst(proj.eng.inst( n ))
      

   #------------------------------------------------------------------------
      
#   def import_db( self, filename ):
#      """Reads a Luna 'destrat' output database"""      
#      proj.eng.import_db( filename )

   #------------------------------------------------------------------------
#   def import_db( self, filename , ids ):
#      """Reads a subset of individuals from a 'destrat' output database"""
#      
#      proj.eng.import_db( filename , ids )

   #------------------------------------------------------------------------
   def clear(self):
      """Clears any existing project sample-list"""
      
      proj.eng.clear()


   #------------------------------------------------------------------------
   def silence(self, b = True ):
      """Toggles the output mode on/off"""
      
      if b: print( 'silencing console outputs' )
      else: print( 'enabling console outputs' )
      proj.eng.silence(b)
      
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
         proj.eng.opt( key, value )

         
   #------------------------------------------------------------------------
   def vars(self):
      """Return a dictionary of all project-level variables"""
      return proj.eng.get_all_opts()

   
   #------------------------------------------------------------------------
   def clear_var(self,key):
      """Clear a project-level option/variable"""
      proj.eng.clear_opt(key)

   #------------------------------------------------------------------------
   def clear_vars(self):
      """Clear all project-level options/variables"""
      proj.eng.clear_opts()

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
      if ( isinstance(n,int) ):
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
      t.columns = ["Command","Stata"]
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
      return proj.eng.variables( cmd , strata )


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
             m = None , m1 = None , m2 = None ):
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
      if s != None: self.var( 's' , s )
      if m != None: self.var( 'm' , m )
      if s1 != None: self.var( 's1' , s1 )
      if s2 != None: self.var( 's2' , s2 )
      if m1 != None: self.var( 'm1' , m1 )
      if m2 != None: self.var( 'm2' , m2 )
      
      # get either one- or two-channel mode Luna script from POPS folder
      twoch = s1 != None and s2 != None;
      if twoch: cmdstr = cmdfile( path + '/s2.ch2.txt' )
      else: cmdstr = cmdfile( path + '/s2.ch1.txt' )
      
      # run the command
      self.eval( cmdstr )

      # return of results
      res = self.table( 'POPS' , 'E' )
      res = res[ ["PP_N1","PP_N2","PP_N3","PP_R","PP_W" ]  ]
      return res


   # --------------------------------------------------------------------------------
   def predict_SUN2019( self, cen , th = '3' , path = None ):
      """Run SUN2019 prediction model for a project

      This assumes that ${age} will be set via a vars file, i.e.

         proj.opt( 'vars' , 'ages.txt' )      

      """
      if path == None: path = resources.MODEL_PATH
      self.var( 'cen' , cen )
      self.var( 'mpath' , path )
      self.var( 'th' , str(th) )
      return self.eval( cmdfile( resources.MODEL_PATH + '/m1-adult-age-luna.txt' ) )




      

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

   #------------------------------------------------------------------------      
   def ivar( self , key , value = None ):
      """Set or get an individual-level variable"""
      if value != None: self.edf.ivar( key , value )
      else: return self.edf.get_ivar( key )
         
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
   def empty_result_set( self ):
      return len( self.edf.strata()  ) == 0

   #------------------------------------------------------------------------
   def strata( self ):
      """Return a dataframe of command/strata pairs from the output set"""
      if ( self.empty_result_set() ): return None
      t = pd.DataFrame( self.edf.strata() )
      t.columns = ["Command","Stata"]
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
   def data( self, chs , annots , time = False ):
      """Returns all data for certain channels and annotations"""
      return self.edf.data( chs , annots , time )

   # --------------------------------------------------------------------------------
   def slice( self, intervals, chs , annots , time = False ):
      """Return signal/annotation data aggregated over a set of intervals"""
      return self.edf.slice( intervals, chs , annots , time )

   # --------------------------------------------------------------------------------   
   def slices( intervals, chs , annots , time = False ):
      """Return a series of signal/annotation data objects for each requested interval"""
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
   def pops( self, chs , path = None , lib = None , edger = True ):
      """Run the POPS stager"""

      if path == None: path = resources.POPS_PATH
      if lib == None: lib = resources.POPS_LIB
      
      import os
      if not os.path.isdir( path ):         
         return 'could not open POPS resource path ' + path 

      # e.g. basic form (+ EDGER)
      # luna edfs/learn-nsrr01.edf -s 'COPY sig=EEG  tag=FLT
      #                                FILTER sig=EEG_FLT bandpass=0.3,35  tw=0.2 ripple=0.01
      #                                COPY sig=EEG_FLT  tag=NORM
      #                                ROBUST-NORM sig=EEG_FLT_NORM epoch winsor=0.002
      #                                POPS path=.../pops lib=s2 alias=CEN,ZEN|EEG_FLT,EEG_FLT_NORM'

      cmdstr = ""
      
      # assume single channel
      # include 'edger tool'
      if type( chs ) is str:
         cmdstr = 'COPY sig=' + chs + ' tag=FLT'
         cmdstr = cmdstr + ' & FILTER  sig=' + chs + '_FLT bandpass=0.3,35  tw=0.2 ripple=0.01 ' 
         cmdstr = cmdstr + ' & COPY sig=' + chs + '_FLT tag=NORM' 
         cmdstr = cmdstr + ' & ROBUST-NORM sig=' + chs + '_FLT_NORM epoch winsor=0.002 ' 

         if edger:
            cmdstr = cmdstr + ' & EDGER sig=' + chs + '_FLT cache=ec1' 
            cmdstr = cmdstr + ' & POPS cache=ec1 path=' + path + ' lib=' + lib + ' alias=CEN,ZEN|' + chs + '_FLT,' + chs + '_FLT_NORM ' 
         else:
            cmdstr = cmdstr + ' & POPS path=' + path + ' lib=' + lib + ' alias=CEN,ZEN|' + chs + '_FLT,' + chs + '_FLT_NORM ' 

      # two-channel equivalence case
      if type( chs ) is list and len( chs ) == 2:
         cmdstr = 'COPY sig=' + chs[0] + ' tag=FLT'
         cmdstr = cmdstr + ' & COPY sig=' + chs[1] + ' tag=FLT'
         cmdstr = cmdstr + ' & FILTER  sig=' + chs[0] + '_FLT bandpass=0.3,35  tw=0.2 ripple=0.01 ' 
         cmdstr = cmdstr + ' & FILTER  sig=' + chs[1] + '_FLT bandpass=0.3,35  tw=0.2 ripple=0.01 ' 
         cmdstr = cmdstr + ' & COPY sig=' + chs[0] + '_FLT tag=NORM' 
         cmdstr = cmdstr + ' & COPY sig=' + chs[1] + '_FLT tag=NORM' 
         cmdstr = cmdstr + ' & ROBUST-NORM sig=' + chs[0] + '_FLT_NORM epoch winsor=0.002 ' 
         cmdstr = cmdstr + ' & ROBUST-NORM sig=' + chs[1] + '_FLT_NORM epoch winsor=0.002 ' 

         if edger:
            cmdstr = cmdstr + ' & EDGER sig=' + chs[0] + '_FLT,' + chs[1] + '_FLT cache=ec1'
            cmdstr = cmdstr + ' & POPS cache=ec1 path=' + path + ' lib=' + lib \
            + ' alias=CEN,ZEN|' + chs[0] + '_FLT,' + chs[0] + '_FLT_NORM ' \
            + ' equiv=CEN,ZEN|' + chs[1] + '_FLT,' + chs[1] + '_FLT_NORM '
         else:
            cmdstr = cmdstr + ' & POPS path=' + path + ' lib=' + lib \
            + ' alias=CEN,ZEN|' + chs[0] + '_FLT,' + chs[0] + '_FLT_NORM ' \
            + ' equiv=CEN,ZEN|' + chs[1] + '_FLT,' + chs[1] + '_FLT_NORM '
         
      # run the command
      self.proc( cmdstr )

      # return of results
      res = self.table( 'POPS' , 'E' )
      res = res[ ["PP_N1","PP_N2","PP_N3","PP_R","PP_W" ]  ]
      return res


   # --------------------------------------------------------------------------------
   def predict_SUN2019( self, cen , age = None , th = '3' , path = None ):
      """Run SUN2019 prediction model for a single individual"""
      if path == None: path = resources.MODEL_PATH
      # set ivars
      if age == None:
         print( 'need to set age ivar' )
         return
      self.ivar( 'age' , str(age) )
      self.ivar( 'cen' , cen )
      self.ivar( 'mpath' , path )
      self.ivar( 'th' , str(th) )
      self.eval( cmdfile( resources.MODEL_PATH + '/m1-adult-age-luna.txt' ) )

   # --------------------------------------------------------------------------------   
   def stages():
      """Return of alist of stages"""   
      #    p.proc( "STAGE" )[ 'STAGE: E' ]
      #    hyp = lp.table( p, "STAGE" , "E" ) 
      #   p.silence( False )
      # return hyp


   
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
   t.columns = ["Command","Stata"]
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
         r[ cmd + ": " + stratum ] = table2df( ts[cmd][stratum] ) 
      return r

# --------------------------------------------------------------------------------
def table2df( r ):
   """Utility function to format tables"""
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------
def show( dfs ):
   """Utility function to format tables"""
   for title , df in dfs.items():
      print( color.BOLD + color.DARKCYAN + title + color.END )
      ICD.display(df)
 
# --------------------------------------------------------------------------------
#
# Helpers
#
# --------------------------------------------------------------------------------

def version():
   """Return version of lunapi & luna"""
   return { "lunapi": lp_version , "luna": _luna.version() }

class color:
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
# TODO: stage duration plot
# TODO: NREM cycle plot
# TODO: overview of hypnogram plot


# --------------------------------------------------------------------------------
def spec(df , ch = None , mine = None , maxe = None , minf = None, maxf = None, w = 0.025 ):
    """Returns a spectrogram from a PSD or MTM epoch table (CH_E_F)"""
    if ch != None: df = df.loc[ df['CH'] == ch ]
    if len(df) == 0: return
    x = df['E'].to_numpy(dtype=int)
    y = df['F'].to_numpy(dtype=float)
    z = df['PSD'].to_numpy(dtype=float)
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
def ltopo_heat(ch_names, ch_vals,  th_vals, lmts="default",
               sz=70, colormap = "bwr", title = "", 
               th=0.05, rimcolor="black", lab = "dB"):
    """Generate a channel-wise topoplot"""
    
    topo = default_xy()
    xlim = [-0.6, 0.6]
    ylim = [-0.6, 0.6]
    rng = [np.min(ch_vals), np.max(ch_vals)]
    if lmts == "default":
        lmts = rng
    else:
        assert lmts[0] <= rng[0] <= lmts[1] and lmts[0] <= rng[1] <= lmts[1], "channel values are out of specified limits"
   
    assert len(set(topo['CH']).intersection(ch_names)) > 0, "no matching channels"
    
    ch_names = ch_names.apply(lambda x: x.upper())    
    topo = topo[topo['CH'].isin(ch_names)]
    topo["vals"] = np.nan
    topo["th_vals"] = np.nan
    topo["rims"] = 0.5

    for ix, ch in topo.iterrows():
        topo.loc[ix,'vals'] = ch_vals[ch_names == ch["CH"]] 
        topo.loc[ix,'th_vals'] = th_vals[ch_names == ch["CH"]] 
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
#ltopo_heat(ch_names, ch_vals, lmts=lmts, sz=70,
#           colormap = "bwr", title = "DENSITY", th=0.05, th_vals = th_vals,
#           rimcolor="black", lab = "n/min")
   
