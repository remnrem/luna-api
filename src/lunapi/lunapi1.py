"""lunapi1 module provides a high-level convenience wrapper around lunapi0 module functions."""

# Luna Python wrapper
# v0.1, 21-Jan-2024

import lunapi.lunapi0 as _luna
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from IPython.core import display as ICD

class resources:
   POPS_PATH = '/nsrr/common/resources/pops/'
   POPS_LIB = 's2'

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
      self.version = "v0.0.4"
      self.n = 0
      print( "initiated lunapi",self.version,proj.eng ,"\n" )
      
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
      """Reads a sample-list 'filenamne' or return the number of observations

      If filename is not defined, this returns the internal sample list
      of an object

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
      
   def import_db( self, filename ):
      proj.eng.import_db( filename )

   #------------------------------------------------------------------------
   def import_db( self, filename , ids ):
      proj.eng.import_db( filename , ids )

   #------------------------------------------------------------------------
   def clear(self):
      proj.eng.clear()


   #------------------------------------------------------------------------
   def silence(self,b):
      proj.eng.silence(b)
      
   #------------------------------------------------------------------------
   def opt(self,key=None,value=None):
      if key is None:
         return proj.eng.get_all_opts()
      if value is None:
         if type(key) is not list: key = [ key ]
         return proj.eng.get_opts( key )
      else:         
         proj.eng.opt( key, value )

         
   #------------------------------------------------------------------------
   def opts(self):
      return proj.eng.get_all_opts()

   
   #------------------------------------------------------------------------
   def clear_opt(self,key):
      proj.eng.clear_opt(key)

   #------------------------------------------------------------------------
   def clear_opts(self):
      proj.eng.clear_opts()

   #------------------------------------------------------------------------   
   def clear_ivars(self):
      proj.eng.clear_ivars()

   #------------------------------------------------------------------------
   def get_n(self,id):
      return proj.eng.get_n(id)

   #------------------------------------------------------------------------   
   def get_id(self,n):
      return proj.eng.get_id(n)

   #------------------------------------------------------------------------
   def get_edf(self,x):
      if ( isinstance(x,int) ):
         return proj.eng.get_edf(x)
      else:
         return proj.eng.get_edf(proj.eng.get_n(x))


   #------------------------------------------------------------------------      
   def get_annots(self,x):
      if ( isinstance(n,int) ):
         return proj.eng.get_annot(x)
      else:
         return proj.eng.get_annot(proj.eng.get_n(x))


   #------------------------------------------------------------------------      
   def import_db(self,f,s=None):
      if s is None:
         return proj.eng.import_db(f)
      else:
         return proj.eng.import_db_subset(f,s)

   #------------------------------------------------------------------------      
   def eval(self, cmdstr ):
      r = proj.eng.eval(cmdstr)
      return tables( r )


   #------------------------------------------------------------------------   
   def commands( self ):
      t = pd.DataFrame( proj.eng.commands() )
      t.columns = ["Command"]
      return t

   #------------------------------------------------------------------------
   def empty_result_set( self ):
      return len( proj.eng.strata()  ) == 0

   #------------------------------------------------------------------------   
   def strata( self ):
      if empty_result_set(): return None
      t = pd.DataFrame( proj.eng.strata() )      
      t.columns = ["Command","Stata"]
      return t

   #------------------------------------------------------------------------
   def table( self, cmd , strata = 'BL' ):
      if empty_result_set(): return None
      r = proj.eng.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   #------------------------------------------------------------------------
   def vars( self, cmd , strata = 'BL' ):
      if empty_result_set(): return None
      return proj.eng.variables( cmd , strata )

   
# --------------------------------------------------------------------------------
# inst class 

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
      return self.edf.attach_edf( f )

   #------------------------------------------------------------------------
   def attach_annot( self, annot ):
      return self.edf.attach_annot( annot )

   #------------------------------------------------------------------------
   def stat( self ):
      t = pd.DataFrame( self.edf.stat(), index=[0] ).T
      t.columns = ["Value"]
      return t

   #------------------------------------------------------------------------
   def refresh( self ):
      self.edf.refresh()

   #------------------------------------------------------------------------
   def drop( self ):
      self.edf.drop()

   #------------------------------------------------------------------------      
   def channels( self ):
      t = pd.DataFrame( self.edf.channels() )
      t.columns = ["Channels"]
      return t

   #------------------------------------------------------------------------   
   def annots( self ):
      t = pd.DataFrame( self.edf.annots() )
      t.columns = ["Annotations"]
      return t

   #------------------------------------------------------------------------
   def eval( self, cmdstr ):
      print( self.edf.eval( cmdstr ) )

   #------------------------------------------------------------------------
   def proc( self, cmdstr ):
      # < log , tables >
      r = self.edf.proc( cmdstr )
      # print console to stdout
      print( r[0] )
      # extract and return result tables
      return tables( r[1] ) 

   #------------------------------------------------------------------------   
   def empty_result_set( self ):
      return len( self.edf.strata()  ) == 0

   #------------------------------------------------------------------------
   def strata( self ):
      if ( self.empty_result_set() ): return None
      t = pd.DataFrame( self.edf.strata() )
      t.columns = ["Command","Stata"]
      return t

   #------------------------------------------------------------------------
   def table( self, cmd , strata = 'BL' ):
      if ( self.empty_result_set() ): return None
      r = self.edf.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   #------------------------------------------------------------------------
   def vars( self, cmd , strata = 'BL' ):
      if ( self.empty_result_set() ): return None
      return self.edf.variables( cmd , strata )


   #------------------------------------------------------------------------
   def e2i( self, epochs ):
      return self.edf.e2i( epochs )
   
   # --------------------------------------------------------------------------------
   def s2i( self, secs ):
      return self.edf.s2i( secs )

   # --------------------------------------------------------------------------------
   def data( self, chs , annots , time = False ):
      return self.edf.data( chs , annots , time )

   # --------------------------------------------------------------------------------
   def slice( self, intervals, chs , annots , time = False ):
      return self.edf.slice( intervals, chs , annots , time )

   # --------------------------------------------------------------------------------   
   def slices( intervals, chs , annots , time = False ):
      return self.edf.slices( intervals, chs , annots , time )
   

   # --------------------------------------------------------------------------------
   def insert_signal( self, label , data , sr ):
      return self.edf.insert_signal( label , data , sr )

   # --------------------------------------------------------------------------------
   def update_signal( self, label , data ):
      return self.edf.update_signal( label , data )

   # --------------------------------------------------------------------------------
   def insert_annot( self, label , intervals, durcol2 = False ):
      return self.edf.insert_annot( label , intervals , durcol2 )


   
   # --------------------------------------------------------------------------------
   def pops( self, chs , path = resources.POPS_PATH , lib = resources.POPS_LIB , edger = True ):
      """Run the POPS stager"""

      import os
      if not os.path.isdir( path ):         
         return 'could not open POPS resource path ' + path + '\n'
      
      # resources.POPS_PATH
      # resources.POPS_LIB

      # luna edfs/learn-nsrr01.edf -s 'COPY sig=EEG  tag=FLT
      #                                FILTER sig=EEG_FLT bandpass=0.3,35  tw=0.2 ripple=0.01
      #                                COPY sig=EEG_FLT  tag=NORM
      #                                ROBUST-NORM sig=EEG_FLT_NORM epoch winsor=0.002
      #                                POPS path=/Users/smp37/dropbox/projects/moonlight/pops lib=s2 alias=CEN,ZEN|EEG_FLT,EEG_FLT_NORM'

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
   r = ts[cmd][strata]
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------
def tables( ts ):
   r = { }
   for cmd in ts:
      strata = ts[cmd].keys()
      for stratum in strata:
         r[ cmd + ": " + stratum ] = table2df( ts[cmd][stratum] ) 
      return r

# --------------------------------------------------------------------------------
def table2df( r ):
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

# --------------------------------------------------------------------------------
def show( dfs ):
   for title , df in dfs.items():
      print( color.BOLD + color.DARKCYAN + title + color.END )
      ICD.display(df)


  
# --------------------------------------------------------------------------------
#
# Helpers
#
# --------------------------------------------------------------------------------

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
    """translate a sleep stage string to a colour for plotting"""
    stgcols = { 'N1' : "#00BEFAFF" ,
                'N2' : "#0050C8FF" ,
                'N3' : "#000050FF" ,
                'NREM4' : "#000032FF",
                'R' : "#FA1432FF",
                'W' : "#31AD52FF",
                'L' : "#F6F32AFF",
                '?' : "#64646464" }    
    return [ stgcols.get(item,item) for item in ss ] 



# --------------------------------------------------------------------------------
def stgn(ss):
    """translate a sleep stage string to a numeric for plotting"""
   
    stgns = { 'N1' : -1,
              'N2' : -2,
              'N3' : -3,
              'NREM4' : -4,
              'R' : 0,
              'W' : 1,
              'L' : 2,
              '?' : 2 }
    return [ stgns.get(item,item) for item in ss ]


# --------------------------------------------------------------------------------
#
# Luna function wrappers
#
# --------------------------------------------------------------------------------


def stages():
   """return of alist of stages"""   
   global p
   if p is None:
      return      
   p.silence( True )
   #    p.proc( "STAGE" )[ 'STAGE: E' ]
   #    hyp = lp.table( p, "STAGE" , "E" ) 
   p.silence( False )
   return hyp



# --------------------------------------------------------------------------------
#
# Visualizations
#
# --------------------------------------------------------------------------------


# --------------------------------------------------------------------------------
def hypno( ss , e = None , xsize = 20 , ysize = 2 , title = None ):
    """Plot a hypnogram"""
    ssn = lunapi.stgn( ss )
    if e is None: e = np.arange(1, len(ss)+1, 1)
    plt.figure(figsize=(xsize , ysize ))
    plt.plot( e/120 , ssn , c = 'gray' , lw = 0.5 )
    plt.scatter( e/120 , ssn , c = lunapi.stgcol( ss ) , zorder=2.5 , s = 10 )
    plt.ylabel('Sleep stage')
    plt.xlabel('Time (hrs)')
    plt.ylim(-3.5, 2.5)
    plt.yticks([-3,-2,-1,0,1,2] , ['N3','N2','N1','R','W','?'] )
    if ( title is not None ): plt.title( title )
    plt.show()

# --------------------------------------------------------------------------------
def hypno_density( ss , e = None , xsize = 20 , ysize = 2 , title = None ):
   import matplotlib.pyplot as plt
   import numpy as np

   x = np.arange(1, len(res), 1)
   y = res.to_numpy()
   fig, ax = plt.subplots()
   ax.stackplot(x, y)
   ax.set(xlim=(0, 8), xticks=np.arange(1, 8),
          ylim=(0, 8), yticks=np.arange(1, 8))
   plt.show()

    
# --------------------------------------------------------------------------------
def spec(df , ch = None ):
    """Returns a spectrogram from a PSD or MTM epoch table (CH_E_F)"""
    if ch is not None: df = df.loc[ df['CH'] == ch ]
    if len(df) == 0: return
    x = df['E'].to_numpy(dtype=int)
    y = df['F'].to_numpy(dtype=float)
    z = df['PSD'].to_numpy(dtype=float)
    z = winsorize( z , limits=[0.025, 0.025] )
    spec0( x,y,z )

# --------------------------------------------------------------------------------
def spec0( x , y , z ):
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
   
