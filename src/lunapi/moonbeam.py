"""Moonbeam client API.

This module exports :class:`moonbeam`, a helper for querying NSRR Moonbeam
catalog metadata and downloading EDF/annotation assets into a local cache.
"""

import pandas as pd
import requests
import io
import tempfile
import os
import re
import pathlib

from .project import proj


class moonbeam:
   """Client for the NSRR Moonbeam data catalog.

   Moonbeam provides programmatic access to sleep study cohorts hosted by
   the National Sleep Research Resource (NSRR).  This class handles
   authentication, catalog queries, file downloads with progress bars, and
   automatic Luna instance creation from cached data.

   Parameters
   ----------
   nsrr_tok : str
       Your personal NSRR API token.
   cdir : str, optional
       Local directory used as the download cache.  Defaults to a
       ``luna-moonbeam`` sub-folder inside the system temporary directory.

   Examples
   --------
   >>> mb = moonbeam('my-nsrr-token')
   >>> mb.cohorts()
   >>> mb.cohort('shhs1')
   >>> p = mb.inst('shhs1-200001')
   """

   df1 = None  # available cohorts
   df2 = None  # available files for current cohort
   curr_cohort = None

   def __init__(self, nsrr_tok , cdir = None ):
      """Initialise Moonbeam with an NSRR token and optional cache directory."""
      self.nsrr_tok = nsrr_tok
      self.df1 = self.cohorts()
      if cdir is None: cdir = os.path.join( tempfile.gettempdir() , 'luna-moonbeam' )
      self.set_cache(cdir)

   def set_cache(self,cdir):
      """Set the local folder used to cache downloaded files.

      Parameters
      ----------
      cdir : str
          Path to the desired cache directory.  The directory (and any
          missing parent directories) will be created automatically.

      Returns
      -------
      None
      """
      self.cdir = cdir
      print( 'using cache folder for downloads: ' + self.cdir )
      os.makedirs( os.path.dirname(self.cdir), exist_ok=True)

   def cached(self,file):
      """Return whether *file* already exists in the local cache.

      Parameters
      ----------
      file : str
          File path relative to the cache root (typically
          ``<cohort>/<filename>``).

      Returns
      -------
      bool
          ``True`` if the file is present in the cache; ``False`` otherwise.
      """
      return os.path.exists( os.path.join( self.cdir , file ) )

   def cohorts(self):
      """Fetch the list of NSRR cohorts accessible with the current token.

      Returns
      -------
      pandas.DataFrame
          DataFrame with columns ``['Cohort', 'Description']``.
      """
      req = requests.get( 'https://zzz.bwh.harvard.edu/cgi-bin/moonbeam.cgi?t=' + self.nsrr_tok ).content
      self.df1 = pd.read_csv(io.StringIO(req.decode('utf-8')),sep='\t',header=None)
      self.df1.columns = ['Cohort','Description']
      return self.df1

   def cohort(self,cohort1):
      """Fetch the file manifest for a given cohort and set it as current.

      Parameters
      ----------
      cohort1 : str or int
          Cohort identifier string (e.g. ``'shhs1'``) or integer row index
          into the DataFrame returned by :meth:`cohorts`.

      Returns
      -------
      pandas.DataFrame
          DataFrame with columns ``['ID', 'EDF', 'Annot']``, one row per
          individual in the cohort.
      """
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
      """Return a Luna instance for one individual, downloading files if needed.

      Calls :meth:`pull` to ensure the EDF (and annotation file, if present)
      are available in the local cache, then creates and returns a fully
      attached :class:`~lunapi.instance.inst` object.

      A call to :meth:`cohort` must have been made first to set the current
      cohort and populate the file manifest.

      Parameters
      ----------
      iid : str or int
          Individual ID string, or integer row index into the DataFrame
          returned by :meth:`cohort`.

      Returns
      -------
      lunapi.instance.inst or None
          Attached instance, or ``None`` if no cohort has been set.
      """
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
      """Download an individual's EDF and annotation files (if not cached).

      Downloads the EDF (and its ``.idx`` companion for compressed files)
      as well as the annotation file (if one is listed in the manifest).
      Files that are already present in the cache are skipped.

      Parameters
      ----------
      iid : str or int
          Individual ID string, or integer row index into the cohort
          manifest DataFrame.
      cohort : str
          Cohort identifier (must match the current cohort set by
          :meth:`cohort`).

      Returns
      -------
      None
      """
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
      """Download a single file from Moonbeam into the local cache.

      If *file* is already present in the cache the download is skipped.
      Progress is displayed via a ``tqdm`` progress bar.

      Parameters
      ----------
      file : str
          Remote file path as returned by the Moonbeam catalog
          (e.g. ``'shhs1/shhs1-200001.edf.gz'``).

      Returns
      -------
      None

      Raises
      ------
      RuntimeError
          If the HTTP response status code indicates an error.
      """
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
      """Fetch phenotype data for an individual from Moonbeam.

      If *cohort* and *iid* are omitted, the method uses the cohort and
      individual set by the most recent :meth:`pull` or :meth:`inst` call.

      Parameters
      ----------
      cohort : str, optional
          Cohort identifier.  Defaults to the current cohort.
      iid : str, optional
          Individual ID.  Defaults to the most recently accessed individual.

      Returns
      -------
      pandas.DataFrame
          DataFrame with columns ``['Variable', 'Value', 'Units',
          'Description']``.  Key NSRR harmonised variables (age, sex, BMI,
          AHI, etc.) are listed first.

      Raises
      ------
      RuntimeError
          If the Moonbeam server returns a non-200 status code.
      """

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


__all__ = ["moonbeam"]
