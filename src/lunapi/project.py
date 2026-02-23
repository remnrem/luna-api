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
      """Retires an existing Luna engine generated via proj()
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
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
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """

      tbl = proj.eng.validate_sample_list()
      tbl = pd.DataFrame( tbl )
      tbl.columns = [ 'ID' , 'Filename', 'Valid' ]
      tbl.index += 1
      return tbl


   #------------------------------------------------------------------------
      
   def reset(self):
      """Drop Luna problem flag
         
         Returns
         -------
         None
                 No value is returned.
      """
      proj.eng.reset()

   def reinit(self):
      """Re-initialize project
         
         Returns
         -------
         None
                 No value is returned.
      """
      proj.eng.reinit()

   #------------------------------------------------------------------------
   
   def inst( self, n ):
      """Generates a new instance
         
         Parameters
         ----------
         n : object\n        Input argument `n`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Generates a new instance with empty fixed-size EDF
         
         Parameters
         ----------
         id : object\n        Input argument `id`.
         nr : object\n        Input argument `nr`.
         rs : object\n        Input argument `rs`.
         startdate : object\n        Input argument `startdate`.
         starttime : object\n        Input argument `starttime`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Clears any existing project sample-list
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      proj.eng.clear()


   #------------------------------------------------------------------------

   def silence(self, b = True , verbose = False ):
      """Toggles the output mode on/off
         
         Parameters
         ----------
         b : object\n        Input argument `b`.
         verbose : object\n        Input argument `verbose`.
         
         Returns
         -------
         None
                 No value is returned.
      """
      if verbose:
         if b: print( 'silencing console outputs' )
         else: print( 'enabling console outputs' )
      proj.eng.silence(b)

   #------------------------------------------------------------------------

   def is_silenced(self, b = True ):
      """Reports on whether log is silenced
         
         Parameters
         ----------
         b : object\n        Input argument `b`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return proj.eng.is_silenced()
      
      
   #------------------------------------------------------------------------

   def flush(self):
      """Internal command, to flush the output buffer
         
         Returns
         -------
         None
                 No value is returned.
      """
      proj.eng.flush()

   # --------------------------------------------------------------------------------

   def include( self, f ):
      """Include options/variables from a @parameter-file
         
         Parameters
         ----------
         f : object\n        Input argument `f`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return proj.eng.include( f )


   #------------------------------------------------------------------------

   def aliases( self ):
      """Return a table of signal/annotation aliases
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      t = pd.DataFrame( proj.eng.aliases() )      
      t.index = t.index + 1
      if len( t ) == 0: return t
      t.columns = ["Type", "Preferred", "Case-insensitive, sanitized alias" ]
      with pd.option_context('display.max_rows', None,):   
         display(t)

   #------------------------------------------------------------------------

   def var(self , key=None , value=None):
      """Set or get project-level options(s)/variables(s)
         
         Parameters
         ----------
         key : object\n        Input argument `key`.
         value : object\n        Input argument `value`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return self.vars( key, value )

   #------------------------------------------------------------------------

   def vars(self , key=None , value=None):
      """Set or get project-level options(s)/variables(s)
         
         Parameters
         ----------
         key : object\n        Input argument `key`.
         value : object\n        Input argument `value`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Clear project-level option(s)/variable(s)
         
         Parameters
         ----------
         key : object\n        Input argument `key`.
         
         Returns
         -------
         None
                 No value is returned.
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
      """Clear individual-level variables for all individuals
         
         Returns
         -------
         None
                 No value is returned.
      """
      proj.eng.clear_ivars()

   #------------------------------------------------------------------------

   def get_n(self,id):
      """Return the number of individuals in the sample-list
         
         Parameters
         ----------
         id : object\n        Input argument `id`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return proj.eng.get_n(id)

   #------------------------------------------------------------------------   

   def get_id(self,n):
      """Return the ID of an individual from the sample-list
         
         Parameters
         ----------
         n : object\n        Input argument `n`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return proj.eng.get_id(n)

   #------------------------------------------------------------------------

   def get_edf(self,x):
      """Return the EDF filename for an individual from the sample-list
         
         Parameters
         ----------
         x : object\n        Input argument `x`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if ( isinstance(x,int) ):
         return proj.eng.get_edf(x)
      else:
         return proj.eng.get_edf(proj.eng.get_n(x))


   #------------------------------------------------------------------------      

   def get_annots(self,x):
      """Return the annotation filenames for an individual from the sample-list
         
         Parameters
         ----------
         x : object\n        Input argument `x`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      if ( isinstance(x,int) ):
         return proj.eng.get_annot(x)
      else:
         return proj.eng.get_annot(proj.eng.get_n(x))


   #------------------------------------------------------------------------      

   def import_db(self,f,s=None):
      """Import a destrat-style Luna output database
         
         Parameters
         ----------
         f : object\n        Input argument `f`.
         s : object\n        Input argument `s`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
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
      """Evaluates one or more Luna commands for all sample-list individuals
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      r = proj.eng.eval(cmdstr)
      return tables( r )

   #------------------------------------------------------------------------ 

   def silent_proc(self, cmdstr ):
      """Silently evaluates one or more Luna commands for all sample-list individuals
         
         Parameters
         ----------
         cmdstr : object\n        Input argument `cmdstr`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      silence_mode = self.is_silenced()
      self.silence(True,False)
      r = proj.eng.eval(cmdstr)
      self.silence( silence_mode , False )
      return tables( r )
      
   #------------------------------------------------------------------------   

   def commands( self ):
      """Return a list of commands in the output set (following proc()
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      t = pd.DataFrame( proj.eng.commands() )
      t.columns = ["Command"]
      return t

   #------------------------------------------------------------------------

   def empty_result_set( self ):
      """Return whether the project result store currently has no tables.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
      """
      return len( proj.eng.strata()  ) == 0

   #------------------------------------------------------------------------   

   def strata( self ):
      """Return a datraframe of command/strata pairs from the output set
         
         Returns
         -------
         object
                 See function description for the concrete return type.
      """
      
      if self.empty_result_set(): return None
      t = pd.DataFrame( proj.eng.strata() )      
      t.columns = ["Command","Strata"]
      return t

   #------------------------------------------------------------------------

   def table( self, cmd , strata = 'BL' ):
      """Return a dataframe from the output set
         
         Parameters
         ----------
         cmd : object\n        Input argument `cmd`.
         strata : object\n        Input argument `strata`.
         
         Returns
         -------
         object
                 See function description for the concrete return type.
      """
      if self.empty_result_set(): return None
      r = proj.eng.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   #------------------------------------------------------------------------

   def variables( self, cmd , strata = 'BL' ):
      """Return a list of all variables for an output table
         
         Parameters
         ----------
         cmd : object\n        Input argument `cmd`.
         strata : object\n        Input argument `strata`.
         
         Returns
         -------
         object
                 Result value produced by the Luna backend wrapper.
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
      """Run SUN2019 prediction model for a project
         
         This assumes that ${age} will be set via a vars file, i.e.
         
            proj.var( 'vars' , 'ages.txt' )
         
         Parameters
         ----------
         cen : object\n        Input argument `cen`.
         th : object\n        Input argument `th`.
         path : object\n        Input argument `path`.
         
         Returns
         -------
         object
                 See function description for the concrete return type.
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
