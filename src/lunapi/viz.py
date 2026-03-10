"""Visualization helpers for notebook workflows.

Exports plotting utilities for hypnograms, spectra, topographic maps, and
the interactive ``scope`` viewer built on ``ipywidgets`` and Plotly.
"""

import pandas as pd
import numpy as np

from .segsrv import segsrv


def default_xy():
   """Return default 2-D scalp electrode locations for a standard 64-channel EEG montage.

   Returns
   -------
   pandas.DataFrame
       DataFrame with columns ``['CH', 'X', 'Y']`` giving the
       normalised Cartesian coordinates of each electrode (top-down view,
       nose pointing up).
   """
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
    """Map a sequence of sleep stage labels to their canonical hex display colours.

    Parameters
    ----------
    ss : list of str
        Sleep stage labels (e.g. ``['W', 'N1', 'N2', 'R', '?']``).

    Returns
    -------
    list of str
        Hex colour string for each label (e.g. ``'#0050C8FF'`` for N2).
        Unknown labels are returned unchanged.
    """
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
    """Map a sequence of sleep stage labels to their canonical numeric codes.

    Codes: N1 → −1, N2 → −2, N3 → −3, R → 0, W → 1, L/? → 2.

    Parameters
    ----------
    ss : list of str
        Sleep stage labels.

    Returns
    -------
    list of int
        Numeric stage code for each label.  Unknown labels are returned
        unchanged.
    """
   
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
    """Plot a colour-coded hypnogram from a sequence of sleep stage labels.

    Parameters
    ----------
    ss : array-like of str
        Per-epoch sleep stage labels (e.g. from
        :meth:`~lunapi.instance.inst.stages`).
    e : array-like of int, optional
        Epoch indices.  If omitted, epochs are numbered ``0, 1, 2, …``.
        Values are divided by 120 before plotting to convert to hours
        (assuming 30-second epochs).
    xsize : float, optional
        Figure width in inches.  Default ``20``.
    ysize : float, optional
        Figure height in inches.  Default ``2``.
    title : str, optional
        Optional plot title.

    Returns
    -------
    None
        The hypnogram is rendered inline via Matplotlib.
    """
    import matplotlib.pyplot as plt
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
   """Plot a stacked-probability hypno-density chart from POPS/SOAP output.

   Displays per-epoch posterior stage probabilities as a stacked area plot,
   giving an at-a-glance picture of staging confidence across the night.

   Parameters
   ----------
   probs : pandas.DataFrame
       DataFrame containing columns ``PP_N1``, ``PP_N2``, ``PP_N3``,
       ``PP_R``, and ``PP_W`` (as returned by the POPS command).
   e : ignored, optional
       Reserved for future use; currently unused.
   xsize : float, optional
       Figure width in inches.  Default ``20``.
   ysize : float, optional
       Figure height in inches.  Default ``2``.
   title : str, optional
       Optional plot title.

   Returns
   -------
   None
       The chart is rendered inline via Matplotlib.
   """

   import matplotlib.pyplot as plt

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
    """Plot power spectral density from a Luna ``PSD`` or ``MTM`` ``CH_F`` table.

    Parameters
    ----------
    df : pandas.DataFrame
        Result table with at least columns ``'CH'``, ``'F'``, and the
        power variable named by *var*.  Typically the ``'PSD: CH_F'`` or
        ``'MTM: CH_F'`` table returned by :meth:`~lunapi.instance.inst.proc`.
    ch : str or list of str
        Channel label(s) to plot.
    var : str, optional
        Column name containing the power values (``'PSD'`` or ``'MTM'``).
        Default ``'PSD'``.
    minf : float, optional
        Minimum frequency (Hz) for the x-axis.  Default: data minimum.
    maxf : float, optional
        Maximum frequency (Hz) for the x-axis.  Default: data maximum.
    minp : float, optional
        Minimum power for the y-axis.  Default: data minimum.
    maxp : float, optional
        Maximum power for the y-axis.  Default: data maximum.
    xlines : float or list of float, optional
        Vertical reference lines at these frequencies.
    ylines : float or list of float, optional
        Horizontal reference lines at these power values.
    dB : bool, optional
        If ``True``, convert power values to dB (10·log₁₀) before
        plotting.  Default ``False``.

    Returns
    -------
    None
        The plot is rendered inline via Matplotlib.
    """
    import matplotlib.pyplot as plt
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
    """Plot an epoch-by-frequency spectrogram from a Luna ``CH_E_F`` result table.

    Parameters
    ----------
    df : pandas.DataFrame
        Result table with columns ``'E'`` (epoch), ``'F'`` (frequency),
        ``'CH'`` (channel), and the power variable named by *var*.
        Typically the ``'PSD: CH_E_F'`` or ``'MTM: CH_E_F'`` table.
    ch : str, optional
        Channel to plot.  If ``None``, all channels in *df* are included.
    var : str, optional
        Column name for power values.  Default ``'PSD'``.
    mine : int, optional
        First epoch to display.  Default: first epoch in the data.
    maxe : int, optional
        Last epoch to display.  Default: last epoch in the data.
    minf : float, optional
        Minimum frequency (Hz).  Default: data minimum.
    maxf : float, optional
        Maximum frequency (Hz).  Default: data maximum.
    w : float, optional
        Winsorisation proportion applied to power values before colour
        mapping.  Default ``0.025``.

    Returns
    -------
    None
        The spectrogram is rendered inline via Matplotlib.
    """
    from scipy.stats.mstats import winsorize
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
   """Render a 2-D spectrogram heatmap from raw epoch/frequency/value vectors.

   Low-level helper called by :func:`spec`.  Bins *z* values into an
   epoch × frequency grid and displays the result as a ``pcolormesh``
   plot.

   Parameters
   ----------
   x : array-like of int
       Epoch index for each observation.
   y : array-like of float
       Frequency (Hz) for each observation.
   z : array-like of float
       Power value for each observation.
   mine : int
       Minimum epoch index for the x-axis.
   maxe : int
       Maximum epoch index for the x-axis.
   minf : float
       Minimum frequency (Hz) for the y-axis.
   maxf : float
       Maximum frequency (Hz) for the y-axis.

   Returns
   -------
   None
       The heatmap is rendered inline via Matplotlib.
   """
   import matplotlib.pyplot as plt
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
    """Plot a channel-wise topographic heat map on a scalp electrode layout.

    Renders a scatter plot in electrode space where each dot is coloured
    by the scalar value *z* for that channel.  Channels with an associated
    p-value below *th* are drawn with a thicker rim.

    Parameters
    ----------
    chs : array-like of str
        Channel labels corresponding to each value in *z*.
    z : array-like of float
        Scalar values to colour-map (one per channel in *chs*).
    ths : array-like of float, optional
        P-values (or thresholding values) for each channel.  Channels
        with ``ths < th`` receive a highlighted rim.  Default ``None``
        (no thresholding).
    th : float, optional
        Significance threshold applied to *ths*.  Default ``0.05``.
    topo : pandas.DataFrame, optional
        Electrode coordinate table with columns ``['CH', 'X', 'Y']``.
        Defaults to the 64-channel layout from :func:`default_xy`.
    lmts : list of two float, optional
        ``[vmin, vmax]`` colour-map limits.  Default: ``[min(z), max(z)]``.
    sz : float, optional
        Marker size (points²) for each electrode dot.  Default ``70``.
    colormap : str, optional
        Matplotlib colour map name.  Default ``'bwr'``.
    title : str, optional
        Text label placed in the upper-left of the figure.  Default ``''``.
    rimcolor : str, optional
        Edge colour for all electrode markers.  Default ``'black'``.
    lab : str, optional
        Colour-bar label.  Default ``'dB'``.

    Returns
    -------
    None
        The topoplot is rendered inline via Matplotlib.
    """

    import matplotlib.pyplot as plt
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
    """Create the interactive notebook scope viewer for one instance.

    Parameters
    ----------
    p : inst
        Target Luna instance.
    chs, bsigs, hsigs : list of str, optional
        Signal channel selections for traces/bands/Hjorth summaries.
    anns : list of str, optional
        Annotation classes to include.
    stgs : list of str, optional
        Sleep-stage labels used by hypnogram rendering.
    stgcols, stgns : dict, optional
        Stage-to-color and stage-to-numeric maps.
    sigcols, anncols : dict, optional
        Optional explicit color overrides.
    throttle1_sr : int, optional
        Input sample-rate throttle.
    throttle2_np : int, optional
        Output point-count throttle.
    summary_mins : int or float, optional
        Threshold (minutes) for summary behavior in backend.
    height : int, optional
        Main scope plot height.
    annot_height, header_height, footer_height : float, optional
        Relative layout proportions.

    Returns
    -------
    ipywidgets.AppLayout or None
        Widget application, or ``None`` when no valid channels/annots exist.
    """

    import plotly.graph_objects as go
    import plotly.express as px
    from ipywidgets import widgets, AppLayout
    from itertools import cycle

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

__all__ = [
    "default_xy",
    "stgcol",
    "stgn",
    "hypno",
    "hypno_density",
    "psd",
    "spec",
    "spec0",
    "topo_heat",
    "scope",
]
