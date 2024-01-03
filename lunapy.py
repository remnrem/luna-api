
# Luna Python wrapper
# v0.1, 2-Jan-2024

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.core import display as ICD

ver = '0.1'

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

def version():
    return ver

def stat( p ):
    t = pd.DataFrame( p.stat() , index=[0] ).T
    t.columns = ["Value"]
    return t

def eval( p , cmdstr ):
    print( p.eval( cmdstr ) )
    
def strata( p ):
    t = pd.DataFrame( p.strata() )
    t.columns = ["Command","Stata"]
    return t

def table( p , cmd , strata ):
    r = p.table( cmd , strata )
    t = pd.DataFrame( r[1] ).T
    t.columns = r[0]
    return t

def table2( r ):
    t = pd.DataFrame( r[1] ).T
    t.columns = r[0]
    return t
 
def proc( p , cmdstr ):
   # < log , tables >
   r = p.proc( cmdstr )

   # print console to stdout
   print( r[0] )    

   # extract and return result tables
   return tables( r[1] ) 


def tables( ts ):
    r = { }
    for cmd in ts:
        strata = ts[cmd].keys()
        for stratum in strata:
            r[ cmd + ": " + stratum ] = table2( ts[cmd][stratum] ) 
    return r
 
def show( dfs ):
    for title , df in dfs.items():
        print( color.BOLD + color.DARKCYAN + title + color.END )
        ICD.display(df)



# --------------------------------------------------------------------------------
#
# Helpers
#
# --------------------------------------------------------------------------------


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

def stages(p):
    p.silence( True )
#    p.proc( "STAGE" )[ 'STAGE: E' ]
#    hyp = lp.table( p, "STAGE" , "E" ) 
    p.silence( False )
    return hyp

# --------------------------------------------------------------------------------
#
# Plots
#
# --------------------------------------------------------------------------------
 
# hypno() make a hypnogram given a table from 'STAGE: E', e.g. from stages() 

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

    
