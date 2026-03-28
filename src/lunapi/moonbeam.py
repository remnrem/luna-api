"""NSRR data access via the official sleepdata.org API.

This module exports :class:`moonbeam`, a helper for querying NSRR datasets,
downloading EDF/annotation assets into a local cache, and creating Luna
instances.  Dataset/file mappings are driven by a curated TSV manifest
maintained at https://github.com/remnrem/luna-api (``nsrr/MANIFEST``).
"""

import functools
import os
import pathlib
import re
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from .project import proj

_BASE_URL = "https://sleepdata.org"
_API_V1 = f"{_BASE_URL}/api/v1"
_CLIENT_MEDIUM = "nsrr-lunapi-v1"
_MANIFEST_URL = ("https://raw.githubusercontent.com/remnrem/luna-api/"
                 "main/nsrr/MANIFEST")
_MANIFEST_LOCAL = ".manifest"   # filename within cdir
_REQUEST_DELAY = 0.15           # seconds between API calls
_MAX_WORKERS = 4                # parallel download threads


def _fmt_size(nbytes):
    """Human-readable file size string."""
    nbytes = int(nbytes or 0)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if nbytes < 1024:
            return f"{nbytes:.1f}\u202f{unit}"
        nbytes //= 1024
    return f"{nbytes:.1f}\u202fPB"


class moonbeam:
    """Client for the NSRR sleepdata.org data catalog.

    File/ID mappings are read from a curated TSV manifest rather than
    crawled at runtime, which makes cohort loading instant and immune to
    dataset layout differences across studies.

    Parameters
    ----------
    nsrr_tok : str
        Personal NSRR API token (obtain at ``https://sleepdata.org/token``).
    cdir : str, optional
        Local download cache.  Defaults to ``luna-nsrr`` inside the system
        temp directory.

    Examples
    --------
    >>> mb = moonbeam('my-token')
    >>> mb.cohorts()
    >>> mb.cohort('cfs')                  # all subcohorts
    >>> mb.cohort('cfs', 'cfs-visit5')    # one subcohort
    >>> p  = mb.inst('cfs-visit5-800001')
    >>> mb.pull_many(['cfs-visit5-800001', 'cfs-visit5-800002'])
    >>> mb.status()
    """

    def __init__(self, nsrr_tok, cdir=None):
        self.nsrr_tok = nsrr_tok
        self._last_req = 0.0
        self.df1 = None           # accessible cohorts DataFrame
        self.df2 = None           # current cohort/subcohort manifest DataFrame
        self.curr_cohort = None
        self.curr_subcohort = None
        self.curr_id = None
        self.curr_edf = None      # remote path within cohort
        self.curr_annots = []     # list of remote annotation paths

        # _mf: cohort -> subcohort -> id -> {'edf': str, 'annots': [str,...]}
        self._mf = {}

        self._verify_token()
        if cdir is None:
            cdir = os.path.join(tempfile.gettempdir(), 'luna-nsrr')
        self.set_cache(cdir)
        self._load_or_fetch_manifest()
        self.df1 = self.cohorts()

    # ------------------------------------------------------------------
    # Core HTTP helper
    # ------------------------------------------------------------------

    def _get(self, url, params=None, stream=False, timeout=60):
        """Rate-limited authenticated GET."""
        since = time.monotonic() - self._last_req
        if since < _REQUEST_DELAY:
            time.sleep(_REQUEST_DELAY - since)
        p = {} if params is None else dict(params)
        p['auth_token'] = self.nsrr_tok
        r = requests.get(url, params=p, stream=stream, timeout=timeout)
        self._last_req = time.monotonic()
        return r

    def _verify_token(self):
        """Confirm the token is valid; raise on failure."""
        try:
            r = self._get(f"{_API_V1}/account/profile.json")
            data = r.json()
        except Exception as exc:
            raise RuntimeError(f"Could not reach sleepdata.org: {exc}") from exc
        if not data.get('authenticated', False):
            raise ValueError(
                "Invalid NSRR token.  Obtain yours at https://sleepdata.org/token"
            )
        print(f"Authenticated as: {data.get('username', '?')} "
              f"({data.get('email', '')})")

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def set_cache(self, cdir):
        """Set the local folder used to cache downloaded files.

        Parameters
        ----------
        cdir : str
            Path to the desired cache directory.  Created automatically.
        """
        self.cdir = str(cdir)
        print(f'Using cache folder: {self.cdir}')
        os.makedirs(self.cdir, exist_ok=True)

    def cached(self, rel_path):
        """Return True if *rel_path* already exists in the local cache.

        Parameters
        ----------
        rel_path : str
            Path relative to the cache root
            (e.g. ``'cfs/polysomnography/edfs/cfs-visit5-800001.edf'``).
        """
        return os.path.exists(os.path.join(self.cdir, rel_path))

    def _local_path(self, cohort, remote_path):
        """Absolute local :class:`~pathlib.Path` for a cohort file."""
        return pathlib.Path(self.cdir) / cohort / remote_path.lstrip('/')

    def status(self, cohort=None):
        """Print a summary of files present in the local cache.

        Parameters
        ----------
        cohort : str, optional
            Restrict report to one cohort.
        """
        root = pathlib.Path(self.cdir)
        if not root.exists():
            print("Cache is empty (directory does not exist).")
            return

        slugs = [cohort] if cohort else [
            d.name for d in sorted(root.iterdir())
            if d.is_dir() and not d.name.startswith('.')
        ]

        grand_files = grand_size = 0
        for slug in slugs:
            cpath = root / slug
            if not cpath.is_dir():
                continue
            files = sorted(
                f for f in cpath.rglob('*')
                if f.is_file() and not f.name.startswith('.')
            )
            size = sum(f.stat().st_size for f in files)
            grand_files += len(files)
            grand_size += size
            print(f"\n{slug}/  ({len(files)} files, {_fmt_size(size)})")
            for f in files:
                print(f"  {f.relative_to(cpath)}  ({_fmt_size(f.stat().st_size)})")

        print(f"\nTotal: {grand_files} files, {_fmt_size(grand_size)}")

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def _manifest_local_path(self):
        return pathlib.Path(self.cdir) / _MANIFEST_LOCAL

    def _parse_manifest(self, text):
        """Parse TSV manifest text into ``self._mf``.

        Expected columns (tab-separated, no header):
        ``cohort  subcohort  ID  EDF  annots``

        *annots* is ``'.'`` when absent, else comma-separated remote paths.
        """
        mf = {}
        skipped = 0
        for lineno, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) != 5:
                skipped += 1
                continue
            cohort, subcohort, iid, edf, annots_str = parts
            annots = [] if annots_str == '.' else annots_str.split(',')
            (mf
             .setdefault(cohort, {})
             .setdefault(subcohort, {})
             )[iid] = {'edf': edf, 'annots': annots}
        if skipped:
            print(f"  manifest: skipped {skipped} malformed line(s).")
        return mf

    def _load_or_fetch_manifest(self):
        """Load manifest from cache; fetch from GitHub if not present."""
        p = self._manifest_local_path()
        if p.exists():
            with open(p) as fh:
                text = fh.read()
            self._mf = self._parse_manifest(text)
            n = sum(len(subs) for cd in self._mf.values() for subs in cd.values())
            print(f"Manifest loaded from cache "
                  f"({n} individuals, {len(self._mf)} cohort(s)).")
        else:
            self._fetch_manifest()

    def _fetch_manifest(self):
        """Download manifest from GitHub and save to cache."""
        print(f"Fetching manifest from {_MANIFEST_URL} …")
        try:
            r = requests.get(_MANIFEST_URL, timeout=30)
            r.raise_for_status()
        except Exception as exc:
            print(f"Warning: could not fetch manifest: {exc}")
            self._mf = {}
            return
        text = r.text
        self._mf = self._parse_manifest(text)
        p = self._manifest_local_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w') as fh:
            fh.write(text)
        n = sum(len(subs) for cd in self._mf.values() for subs in cd.values())
        print(f"Manifest saved "
              f"({n} individuals, {len(self._mf)} cohort(s)).")

    def refresh_manifest(self):
        """Re-download the manifest from GitHub, replacing the cached copy."""
        self._fetch_manifest()

    # ------------------------------------------------------------------
    # Cohort listing
    # ------------------------------------------------------------------

    def cohorts(self):
        """Return a DataFrame of NSRR datasets the current token can access.

        Datasets are filtered to those present in the manifest; the
        ``Subcohorts`` column shows which logical sub-datasets are defined.

        Returns
        -------
        pandas.DataFrame
            Columns: ``['Cohort', 'Description', 'Subcohorts']``.
        """
        accessible = {}
        page = 1
        while True:
            r = self._get(f"{_API_V1}/datasets.json", params={'page': page})
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            for d in data:
                slug = d.get('slug', '')
                accessible[slug] = d.get('name', slug)
            if len(data) < 20:
                break
            page += 1

        rows = []
        for slug, name in accessible.items():
            subcohorts = list(self._mf.get(slug, {}).keys())
            rows.append({
                'Cohort': slug,
                'Description': name,
                'Subcohorts': ', '.join(subcohorts) if subcohorts else '(not in manifest)',
            })

        self.df1 = pd.DataFrame(rows)
        return self.df1

    def cohort(self, cohort1, subcohort=None):
        """Load the manifest for a cohort (or subcohort) as the current view.

        Parameters
        ----------
        cohort1 : str or int
            NSRR dataset slug or integer row index into :meth:`cohorts`.
        subcohort : str, optional
            If given, restrict to this subcohort and set it as current.

        Returns
        -------
        pandas.DataFrame
            Columns: ``['Subcohort', 'ID', 'EDF', 'Annot']``.
            *Annot* contains the first annotation path, or ``'.'``.
        """
        if isinstance(cohort1, int):
            cohort1 = self.df1.loc[cohort1, 'Cohort']
        if not isinstance(cohort1, str):
            return

        if cohort1 not in self._mf:
            print(f"'{cohort1}' is not in the manifest. "
                  "Try refresh_manifest() if it was recently added.")
            return

        self.curr_cohort = cohort1
        self.curr_subcohort = subcohort

        rows = []
        for sc, subjects in self._mf[cohort1].items():
            if subcohort and sc != subcohort:
                continue
            for iid, info in subjects.items():
                first_annot = info['annots'][0] if info['annots'] else '.'
                rows.append({
                    'Subcohort': sc,
                    'ID': iid,
                    'EDF': info['edf'],
                    'Annot': first_annot,
                })

        self.df2 = pd.DataFrame(rows, columns=['Subcohort', 'ID', 'EDF', 'Annot'])
        return self.df2

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def _resolve_iid(self, iid, subcohort):
        """Return (subcohort, info-dict) for an individual.

        *subcohort* defaults to ``self.curr_subcohort``.  Raises if the ID
        is ambiguous across subcohorts.
        """
        cohort = self.curr_cohort
        sc = subcohort or self.curr_subcohort

        if isinstance(iid, int):
            row = self.df2.iloc[iid]
            iid = row['ID']
            sc = sc or row['Subcohort']

        if sc:
            subs = self._mf[cohort].get(sc, {})
            if iid not in subs:
                raise KeyError(f"ID '{iid}' not found in subcohort '{sc}'.")
            return sc, iid, subs[iid]

        # Search all subcohorts
        matches = [
            (sc2, subs[iid])
            for sc2, subs in self._mf[cohort].items()
            if iid in subs
        ]
        if not matches:
            raise KeyError(f"ID '{iid}' not found in cohort '{cohort}'.")
        if len(matches) > 1:
            options = [m[0] for m in matches]
            raise RuntimeError(
                f"ID '{iid}' appears in multiple subcohorts: {options}. "
                "Pass subcohort= to disambiguate."
            )
        sc, info = matches[0]
        return sc, iid, info

    def pull(self, iid, subcohort=None):
        """Download EDF and annotation files for one individual (if not cached).

        Parameters
        ----------
        iid : str or int
            Individual ID, or integer row index into :meth:`cohort` DataFrame.
        subcohort : str, optional
            Subcohort label.  Defaults to the current subcohort; required when
            the same ID appears in more than one subcohort.
        """
        if self._mf is None or self.curr_cohort is None:
            raise RuntimeError("Call cohort() first.")

        sc, iid, info = self._resolve_iid(iid, subcohort)
        self.curr_subcohort = sc
        self.curr_id = iid
        self.curr_edf = info['edf']
        self.curr_annots = info['annots']

        print(f"\nPulling {iid}  [{sc}]  from '{self.curr_cohort}':")
        self.pull_file(self.curr_cohort, self.curr_edf)

        # EDFZ companion index
        if re.search(r'\.(edf\.gz|edfz)$', self.curr_edf, re.IGNORECASE):
            self.pull_file(self.curr_cohort, self.curr_edf + '.idx')

        for annot in self.curr_annots:
            self.pull_file(self.curr_cohort, annot)

    def pull_file(self, cohort, remote_path):
        """Download a single file from NSRR into the local cache.

        Skips the download if the file is already present.

        Parameters
        ----------
        cohort : str
            NSRR dataset slug (e.g. ``'cfs'``).
        remote_path : str
            Path of the file within the dataset (relative to its root).

        Raises
        ------
        RuntimeError
            On HTTP error.
        """
        from tqdm.auto import tqdm

        remote_path = remote_path.lstrip('/')
        local = self._local_path(cohort, remote_path)
        label = os.path.basename(remote_path)

        if local.exists():
            print(f"  [cached] {remote_path}")
            return

        local.parent.mkdir(parents=True, exist_ok=True)

        url = (f"{_BASE_URL}/datasets/{cohort}/files/"
               f"a/{self.nsrr_tok}/m/{_CLIENT_MEDIUM}/{remote_path}")

        r = requests.get(url, stream=True, allow_redirects=True, timeout=300)
        if r.status_code != 200:
            r.raise_for_status()
            raise RuntimeError(
                f"Download failed for {remote_path}: HTTP {r.status_code}"
            )

        total = int(r.headers.get('Content-Length', 0)) or None
        r.raw.read = functools.partial(r.raw.read, decode_content=True)

        with tqdm.wrapattr(r.raw, "read", total=total, desc=label,
                           unit='B', unit_scale=True, unit_divisor=1024) as raw:
            with open(local, 'wb') as fh:
                shutil.copyfileobj(raw, fh)

    def pull_many(self, iids, subcohort=None, cohort=None,
                  max_workers=_MAX_WORKERS):
        """Download files for multiple individuals with parallel connections.

        Already-cached files are skipped automatically.

        Parameters
        ----------
        iids : list of str or int
            Individual IDs to download.
        subcohort : str, optional
            Subcohort label.  Defaults to the current subcohort.
        cohort : str, optional
            Dataset slug.  Defaults to the current cohort.
        max_workers : int, optional
            Parallel download threads (default: 4).
        """
        if cohort is None:
            cohort = self.curr_cohort
        if cohort not in self._mf:
            raise RuntimeError("Call cohort() first.")

        # Build flat job list: (cohort, remote_path)
        jobs = []
        for iid in iids:
            try:
                sc, iid_str, info = self._resolve_iid(iid, subcohort)
            except (KeyError, RuntimeError) as exc:
                print(f"  [skipped] {iid}: {exc}")
                continue
            jobs.append((cohort, info['edf']))
            if re.search(r'\.(edf\.gz|edfz)$', info['edf'], re.IGNORECASE):
                jobs.append((cohort, info['edf'] + '.idx'))
            for annot in info['annots']:
                jobs.append((cohort, annot))

        errors = []

        def _download(args):
            coh, rpath = args
            if self._local_path(coh, rpath).exists():
                return coh, rpath, None
            try:
                self.pull_file(coh, rpath)
                return coh, rpath, None
            except Exception as exc:
                return coh, rpath, str(exc)

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_download, job): job for job in jobs}
            for fut in as_completed(futures):
                coh, rpath, err = fut.result()
                if err:
                    errors.append((coh, rpath, err))
                    print(f"  [FAILED] {rpath}: {err}")

        if errors:
            print(f"\n{len(errors)} download(s) failed.")
        else:
            print(f"\n{len(jobs)} file(s) processed.")

    # ------------------------------------------------------------------
    # Luna integration
    # ------------------------------------------------------------------

    def inst(self, iid, subcohort=None):
        """Return a Luna instance for one individual, downloading if needed.

        Parameters
        ----------
        iid : str or int
            Individual ID, or integer row index.
        subcohort : str, optional
            Subcohort label.  Defaults to the current subcohort.

        Returns
        -------
        lunapi.instance.inst or None
        """
        if self.curr_cohort is None:
            return None

        self.pull(iid, subcohort=subcohort)

        proj1 = proj(False)
        p = proj1.inst(self.curr_id)

        edf1 = str(self._local_path(self.curr_cohort, self.curr_edf).resolve())
        p.attach_edf(edf1)

        if self.curr_annots:
            ann1 = str(
                self._local_path(self.curr_cohort, self.curr_annots[0]).resolve()
            )
            p.attach_annot(ann1)

        return p


__all__ = ["moonbeam"]
