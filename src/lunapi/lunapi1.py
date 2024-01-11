
# Luna Python wrapper
# v0.1, 2-Jan-2024

import lunapi.lunapi0 as _luna

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.core import display as ICD

# C++ singleton class (engine & sample list)
# lunapi_t      --> luna

# one observation
# lunapi_inst_T --> inst

# --------------------------------------------------------------------------------
# luna class 

class proj:

   # single static engine class
   eng = _luna.inaugurate()
   
   def __init__(self):
      self.version = "v0.1"
      self.n = 0
      print( "initiated lunapi",self.version,proj.eng ,"\n" )
      
   def retire():
      return _luna.retire()

   def build(self,tok):
      if type(tok) is not list: tok = [ tok ]
      return proj.eng.build_sample_list(tok)
   
   def sample_list(self, f=None ):
      # return sample list
      if f is None:
         return proj.eng.get_sample_list()

      # read sample list from file
      self.n = proj.eng.read_sample_list(f)
      print( "read",self.n,"individuals from",f)

   def nobs(self):
      return proj.eng.nobs()
   
   def inst( self, n ):
      return inst(proj.eng.inst( n ))

   def import_db( self, filename ):
      proj.eng.import_db( filename )
   
   def import_db( self, filename , ids ):
      proj.eng.import_db( filename , ids )
   
   def clear(self):
      proj.eng.clear()
   
   def silence(self,b):
      proj.eng.silence(b)
      
   def opt(self,key,value):
      proj.eng.opt( key, value )
      
   def opt(self,key):
      return proj.eng.opt( key )

   def opts(self):
      return proj.eng.opts()

   def clear_opt(self,key):
      proj.eng.clear_opt(key)
      
   def clear_opts(self):
      proj.eng.clear_opts()
   
   def clear_ivars(self):
      proj.eng.clear_ivars()

   def get_n(self,id):
      return proj.eng.get_n(id)

   def get_id(self,n):
      return proj.eng.get_id(n)

   def get_edf(self,x):
      if ( isinstance(x,int) ):
         return proj.eng.get_edf(x)
      else:
         return proj.eng.get_edf(proj.eng.get_n(x))
      
   def get_annots(self,x):
      if ( isinstance(n,int) ):
         return proj.eng.get_annot(x)
      else:
         return proj.eng.get_annot(proj.eng.get_n(x))

   def import_db(self,f,s=None):
      if s is None:
         return proj.eng.import_db(f)
      else:
         return proj.eng.import_db_subset(f,s)
      
   def eval(self, cmdstr ):
      r = proj.eng.eval(cmdstr)
      return tables( r )

   def commands( self ):
      t = pd.DataFrame( proj.eng.commands() )
      t.columns = ["Command"]
      return t

   def strata( self ):
      t = pd.DataFrame( proj.eng.strata() )
      t.columns = ["Command","Stata"]
      return t

   def table( self, cmd , strata = 'BL' ):
      r = proj.eng.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   def vars( self, cmd , strata = 'BL' ):
      return proj.eng.variables( cmd , strata )

   


# --------------------------------------------------------------------------------
# inst class 

class inst:
   
   def __init__(self,p=None):
      if ( isinstance(p,str) ):
         self.edf = _luna.inst(p)
      elif (isinstance(p,_luna.inst)):
         self.edf = p
      else:
         self.edf = _luna.inst()

   def __repr__(self):
      return f'{self.edf}'

   def attach_edf( self, f ):
      return self.edf.attach_edf( f )

   def attach_annot( self, annot ):
      return self.edf.attach_annot( annot )
    
   def stat( self ):
      t = pd.DataFrame( self.edf.stat(), index=[0] ).T
      t.columns = ["Value"]
      return t

   def refresh( self ):
      self.edf.refresh()

   def drop( self ):
      self.edf.drop()

   def channels( self ):
      t = pd.DataFrame( self.edf.channels() )
      t.columns = ["Channels"]
      return t

   def annots( self ):
      t = pd.DataFrame( self.edf.annots() )
      t.columns = ["Annotations"]
      return t

   def eval( self, cmdstr ):
      print( self.edf.eval( cmdstr ) )
    
   def proc( self, cmdstr ):
      # < log , tables >
      r = self.edf.proc( cmdstr )
      # print console to stdout
      print( r[0] )
      # extract and return result tables
      return tables( r[1] ) 

   def strata( self ):
      t = pd.DataFrame( self.edf.strata() )
      t.columns = ["Command","Stata"]
      return t

   def table( self, cmd , strata = 'BL' ):
      r = self.edf.table( cmd , strata )
      t = pd.DataFrame( r[1] ).T
      t.columns = r[0]
      return t

   def vars( self, cmd , strata = 'BL' ):
      return self.edf.variables( cmd , strata )


   # --------------------------------------------------------------------------------
   # intervals/slices

   def e2i( self, epochs ):
      return self.edf.e2i( epochs )
   
   def s2i( self, secs ):
      return self.edf.s2i( secs )

   # --------------------------------------------------------------------------------
   # data access

   def data( self, chs , annots , time = False ):
      return self.edf.data( chs , annots , time )
   
   def slice( self, intervals, chs , annots , time = False ):
      return self.edf.slice( intervals, chs , annots , time )

   def slices( intervals, chs , annots , time = False ):
      return self.edf.slices( intervals, chs , annots , time )
   

   # --------------------------------------------------------------------------------
   # add/update signals & annotations

   def insert_signal( self, label , data , sr ):
      return self.edf.insert_signal( label , data , sr )
   
   def update_signal( self, label , data ):
      return self.edf.update_signal( label , data )

   def insert_annot( self, label , intervals, durcol2 = False ):
      return self.edf.insert_annot( label , intervals , durcol2 )





# --------------------------------------------------------------------------------
# misc non-member utilities functions


# load and parse a Luna command script from a file      
def cmdfile( f ):
   return _luna.cmdfile( f )

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

def table( ts, cmd , strata = 'BL' ):
   r = ts[cmd][strata]
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t

def tables( ts ):
   r = { }
   for cmd in ts:
      strata = ts[cmd].keys()
      for stratum in strata:
         r[ cmd + ": " + stratum ] = table2df( ts[cmd][stratum] ) 
      return r

   
def table2df( r ):
   t = pd.DataFrame( r[1] ).T
   t.columns = r[0]
   return t


def show( dfs ):
   for title , df in dfs.items():
      print( color.BOLD + color.DARKCYAN + title + color.END )
      ICD.display(df)





   
# --------------------------------------------------------------------------------
# Helpers

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

# stgcol() translate a sleep stage string to a colour for plotting

def stgcol(ss):
    stgcols = { 'N1' : "#00BEFAFF" ,
                'N2' : "#0050C8FF" ,
                'N3' : "#000050FF" ,
                'NREM4' : "#000032FF",
                'R' : "#FA1432FF",
                'W' : "#31AD52FF",
                'L' : "#F6F32AFF",
                '?' : "#64646464" }    
    return [ stgcols.get(item,item) for item in ss ] 


# stgn() translate a sleep stage string to a numeric for plotting

def stgn(ss):
    stgns = { 'N1' : -1,
              'N2' : -2,
              'N3' : -3,
              'NREM4' : -4,
              'R' : 0,
              'W' : 1,
              'L' : 2,
              '?' : 2 }
    return [ stgns.get(item,item) for item in ss ]

 
# stages() convenience function to return a list of stages

def stages():
   global p
   if p is None:
      return      
   p.silence( True )
   #    p.proc( "STAGE" )[ 'STAGE: E' ]
   #    hyp = lp.table( p, "STAGE" , "E" ) 
   p.silence( False )
   return hyp



# --------------------------------------------------------------------------------
# Viz : hypnograms

def hypno( hyp ):
    plt.figure(figsize=(20,2))
    plt.plot( hyp['E']/120 , hyp['STAGE_N'] , c = 'gray' , lw = 0.5 )
    plt.scatter( hyp['E']/120 , hyp['STAGE_N'] , c = stgcol( hyp['STAGE'] ) , zorder=2.5 , s = 10 )
    plt.ylabel('Sleep stage')
    plt.xlabel('Time (hrs)')
    plt.ylim(-3.5, 2.5)
    plt.yticks([-3,-2,-1,0,1,2] , ['N3','N2','N1','R','W','?'] )
    plt.title("id1")
    plt.show() 

    
