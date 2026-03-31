"""NSRR data access via the official sleepdata.org API.

This module exports :class:`moonbeam`, a helper for querying NSRR datasets,
downloading EDF/annotation assets into a local cache, and creating Luna
instances.  Dataset/file mappings are driven by a curated TSV manifest
maintained at https://github.com/remnrem/luna-api (``nsrr/MANIFEST``).
"""

import base64
import functools
import getpass
import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
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
_DATASETS_PAGE_SIZE = 10
_TOKEN_PATH = pathlib.Path.home() / '.config' / 'lunapi' / '.token'
_PERMS_PATH = pathlib.Path.home() / '.config' / 'lunapi' / '.allowed_cohorts.json'


# ------------------------------------------------------------------
# Token obfuscation helpers (module-level, no extra dependencies)
# ------------------------------------------------------------------

def _machine_key():
    """SHA-256 key derived from the current user + hostname."""
    seed = f"{getpass.getuser()}@{socket.gethostname()}:lunapi-nsrr"
    return hashlib.sha256(seed.encode()).digest()


def _obfuscate(token):
    """XOR *token* with the machine key and return a base64 string."""
    key = _machine_key()
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(token.encode()))
    return base64.b64encode(xored).decode()


def _deobfuscate(data):
    """Reverse of :func:`_obfuscate`; returns the original token string."""
    key = _machine_key()
    xored = base64.b64decode(data.encode())
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(xored)).decode()


def _save_token(token):
    """Write *token* to the cache file (permissions 0600)."""
    _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_PATH.write_text(_obfuscate(token))
    _TOKEN_PATH.chmod(0o600)


def _load_token():
    """Return the cached token, or None if not present / unreadable."""
    if not _TOKEN_PATH.exists():
        return None
    try:
        return _deobfuscate(_TOKEN_PATH.read_text().strip())
    except Exception:
        return None


def _token_cache_key(token):
    """Return a stable non-reversible cache key for a token."""
    return hashlib.sha256(str(token).encode()).hexdigest()


def _save_allowed_cohorts(token, cohorts):
    """Persist the token-visible cohort slugs for reuse on future connects."""
    _PERMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "token_sha256": _token_cache_key(token),
        "cohorts": sorted(str(x) for x in cohorts),
        "updated_at": time.time(),
    }
    _PERMS_PATH.write_text(json.dumps(payload))
    _PERMS_PATH.chmod(0o600)


def _load_allowed_cohorts(token):
    """Load cached token-visible cohort slugs, if they match this token."""
    if not _PERMS_PATH.exists():
        return None
    try:
        payload = json.loads(_PERMS_PATH.read_text())
    except Exception:
        return None
    if payload.get("token_sha256") != _token_cache_key(token):
        return None
    cohorts = payload.get("cohorts")
    if not isinstance(cohorts, list):
        return None
    return {str(x) for x in cohorts if str(x).strip()}


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
    nsrr_tok : str, optional
        Personal NSRR API token (obtain at ``https://sleepdata.org/token``).
        If omitted, the token saved by a previous call is used.
    cdir : str, optional
        Local download cache.  Defaults to ``luna-nsrr`` inside the system
        temp directory.

    Examples
    --------
    >>> mb = moonbeam('my-token')          # first use — token is cached
    >>> mb = moonbeam()                    # subsequent use — token loaded automatically
    >>> moonbeam.clear_token()             # remove cached token
    >>> mb.cohorts()
    >>> mb.cohort('cfs')                   # all subcohorts
    >>> mb.cohort('cfs', 'cfs-visit5')     # one subcohort
    >>> p  = mb.inst('cfs-visit5-800001')
    >>> mb.pull_many(['cfs-visit5-800001', 'cfs-visit5-800002'])
    >>> mb.status()
    """

    def __init__(self, nsrr_tok=None, cdir=None):
        if nsrr_tok is None:
            nsrr_tok = _load_token()
            if nsrr_tok is None:
                raise ValueError(
                    "No NSRR token provided and none cached.\n"
                    "Pass nsrr_tok= or call moonbeam.save_token('your-token').\n"
                    "Obtain a token at https://sleepdata.org/token"
                )

        self.nsrr_tok = nsrr_tok
        self._last_req = 0.0
        self.df1 = None           # cohort summary DataFrame
        self.df2 = None           # current cohort/subcohort manifest DataFrame
        self.curr_cohort = None
        self.curr_subcohort = None
        self.curr_id = None
        self.curr_edf = None      # remote path within cohort
        self.curr_annots = []     # list of remote annotation paths
        self._allowed_cohort_slugs = None

        # _mf: cohort -> subcohort -> id -> {'edf': str, 'annots': [str,...]}
        self._mf = {}

        self._verify_token()
        _save_token(nsrr_tok)     # cache after successful auth
        self._allowed_cohort_slugs = _load_allowed_cohorts(nsrr_tok)

        if cdir is None:
            cdir = os.path.join(tempfile.gettempdir(), 'luna-nsrr')
        self.set_cache(cdir)
        self._load_or_fetch_manifest()
        self.df1 = self.cohorts()

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    @staticmethod
    def save_token(token):
        """Save *token* to the local cache for passwordless future sessions.

        The token is obfuscated using XOR with a SHA-256 key derived from
        the current username and hostname, then base64-encoded and written to
        ``~/.config/lunapi/.token`` with permissions ``0600`` (owner
        read/write only).  This is not cryptographic encryption, but the file
        is not human-readable and is bound to the specific user account and
        machine — a copy of the file will not decode on a different system.

        Call :meth:`clear_token` to remove the cached token.

        Parameters
        ----------
        token : str
            NSRR API token (obtain at ``https://sleepdata.org/token``).
        """
        _save_token(token)
        print(f"Token saved to {_TOKEN_PATH}")

    @staticmethod
    def clear_token():
        """Remove the cached NSRR token from ``~/.config/lunapi/.token``.

        After calling this method, an explicit *nsrr_tok* argument will be
        required when constructing a new :class:`moonbeam` instance.
        """
        if _TOKEN_PATH.exists():
            _TOKEN_PATH.unlink()
            print(f"Cached token removed ({_TOKEN_PATH}).")
        else:
            print("No cached token found.")

    # ------------------------------------------------------------------
    # Core HTTP helper
    # ------------------------------------------------------------------

    def _get(self, url, params=None, stream=False, timeout=60):
        """Rate-limited authenticated GET request.

        Enforces a minimum inter-request delay of ``_REQUEST_DELAY`` seconds
        and appends ``auth_token`` to every request automatically.
        """
        since = time.monotonic() - self._last_req
        if since < _REQUEST_DELAY:
            time.sleep(_REQUEST_DELAY - since)
        p = {} if params is None else dict(params)
        p['auth_token'] = self.nsrr_tok
        r = requests.get(url, params=p, stream=stream, timeout=timeout)
        self._last_req = time.monotonic()
        return r

    def _verify_token(self):
        """Validate the token against the sleepdata.org account API.

        Prints the authenticated username and e-mail on success.

        Raises
        ------
        RuntimeError
            If the sleepdata.org API cannot be reached.
        ValueError
            If the token is rejected (``authenticated: false``).
        """
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
        """Return whether *rel_path* already exists in the local cache.

        Parameters
        ----------
        rel_path : str
            Path relative to the cache root, i.e.
            ``{cohort}/{remote_path}`` (e.g.
            ``'cfs/polysomnography/edfs/cfs-visit5-800001.edf'``).

        Returns
        -------
        bool
            ``True`` if the file is present on disk; ``False`` otherwise.
        """
        return os.path.exists(os.path.join(self.cdir, rel_path))

    def _local_path(self, cohort, remote_path):
        """Return the absolute local :class:`~pathlib.Path` for a dataset file.

        The on-disk layout mirrors the remote structure:
        ``{cdir}/{cohort}/{remote_path}``.
        """
        return pathlib.Path(self.cdir) / cohort / remote_path.lstrip('/')

    def clear_cache(self, cohort=None):
        """Delete downloaded files from the local cache.

        The cached manifest (``.manifest``) is always preserved so that the
        next session does not need to re-fetch it from GitHub.

        Parameters
        ----------
        cohort : str, optional
            If given, remove only that cohort's sub-folder (e.g. ``'cfs'``).
            If omitted, all cohort sub-folders are removed.
        """
        root = pathlib.Path(self.cdir)
        if cohort:
            target = root / cohort
            if not target.exists():
                print(f"Nothing cached for '{cohort}'.")
                return
            size = sum(f.stat().st_size for f in target.rglob('*') if f.is_file())
            shutil.rmtree(target)
            print(f"Removed {target}  ({_fmt_size(size)})")
        else:
            if not root.exists():
                print("Cache is already empty.")
                return
            total = 0
            for child in sorted(root.iterdir()):
                # preserve the manifest file itself
                if child.is_dir():
                    size = sum(f.stat().st_size for f in child.rglob('*') if f.is_file())
                    total += size
                    shutil.rmtree(child)
                    print(f"  removed {child.name}/  ({_fmt_size(size)})")
            print(f"Cache cleared  ({_fmt_size(total)} freed)")

    def status(self, cohort=None):
        """Print a tree of downloaded files with sizes.

        Lists every file under each cohort sub-folder, grouped by cohort,
        with a grand total at the end.

        Parameters
        ----------
        cohort : str, optional
            Restrict the report to one cohort (e.g. ``'cfs'``).  If omitted,
            all cohorts present in the cache are shown.
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
        """Return the :class:`~pathlib.Path` of the locally cached manifest."""
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
        """Re-download the manifest from GitHub, replacing the cached copy.

        Use this after new datasets or individuals have been added to the
        upstream manifest at ``nsrr/MANIFEST`` in the luna-api repository.
        The in-memory ``_mf`` dict and the local ``.manifest`` file are both
        updated immediately.
        """
        self._fetch_manifest()

    # ------------------------------------------------------------------
    # Cohort listing
    # ------------------------------------------------------------------

    def _datasets_on_page(self, page):
        """Return one page of dataset records visible to this token."""
        r = self._get(
            f"{_API_V1}/datasets.json",
            params={"page": page},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return []

    def allowed_cohorts(self, refresh=False):
        """Return the dataset slugs visible to the current NSRR token.

        This queries the NSRR dataset listing API and caches the resulting
        slug set on the instance. Public datasets and datasets explicitly
        granted to the token are both included because both are downloadable.

        Parameters
        ----------
        refresh : bool, optional
            Force a fresh API query even if cached results are available.

        Returns
        -------
        set[str]
            Dataset slugs visible to the token.
        """
        if self._allowed_cohort_slugs is not None and not refresh:
            return set(self._allowed_cohort_slugs)

        allowed = set()
        page = 1
        while True:
            datasets = self._datasets_on_page(page)
            if not datasets:
                break
            for row in datasets:
                if isinstance(row, dict):
                    slug = row.get("slug")
                    if slug:
                        allowed.add(str(slug))
            if len(datasets) < _DATASETS_PAGE_SIZE:
                break
            page += 1

        self._allowed_cohort_slugs = allowed
        _save_allowed_cohorts(self.nsrr_tok, allowed)
        return set(allowed)

    def cohorts(self):
        """Return a DataFrame of cohorts defined in the manifest.

        Uses the manifest for cohort membership counts and the cached result
        of :meth:`allowed_cohorts` for authorization annotations.  The result
        is also stored as ``self.df1``.

        Returns
        -------
        pandas.DataFrame
            One row per cohort with columns:

            ``Cohort``
                NSRR dataset slug (e.g. ``'cfs'``).
            ``Subcohorts``
                Comma-separated list of subcohort labels defined for this
                cohort.
            ``N``
                Total number of individuals across all subcohorts.
            ``Cached``
                Number of individuals whose EDF is already on disk.
            ``Authorized``
                ``True`` when the current NSRR token can see/download the
                cohort in the NSRR dataset listing, ``False`` otherwise.
        """
        allowed = set(self._allowed_cohort_slugs or ())
        rows = []
        for cohort, subcohort_data in self._mf.items():
            subcohorts = list(subcohort_data.keys())
            n = 0
            cached = 0
            for subs in subcohort_data.values():
                for info in subs.values():
                    n += 1
                    if self._local_path(cohort, info['edf']).exists():
                        cached += 1
            rows.append({
                'Cohort': cohort,
                'Subcohorts': ', '.join(subcohorts),
                'N': n,
                'Cached': cached,
                'Authorized': cohort in allowed,
            })

        self.df1 = pd.DataFrame(rows)
        return self.df1

    def cohort(self, cohort1, subcohort=None):
        """Set the active cohort and return its individual manifest.

        Sets ``self.curr_cohort`` (and ``self.curr_subcohort`` when
        *subcohort* is given).  The result is also stored as ``self.df2``.
        Does not contact the network.

        Parameters
        ----------
        cohort1 : str or int
            NSRR dataset slug (e.g. ``'cfs'``) or integer row index into
            the DataFrame returned by :meth:`cohorts`.
        subcohort : str, optional
            If given, restrict the view to this subcohort (e.g.
            ``'baseline'``) and record it as the current subcohort.
            When omitted, all subcohorts are included and
            ``curr_subcohort`` is cleared.

        Returns
        -------
        pandas.DataFrame
            One row per individual with columns:

            ``Subcohort``
                Subcohort label for this row.
            ``ID``
                Subject identifier (e.g. ``'cfs-visit5-800001'``).
            ``EDF``
                Remote path to the EDF file relative to the cohort root.
            ``Annot``
                Remote path to the primary annotation file, or ``'.'`` if
                none is defined.
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
        """Locate an individual in the manifest and return their file info.

        *subcohort* falls back to ``self.curr_subcohort`` when not given.
        Integer *iid* values are resolved against ``self.df2``.

        Parameters
        ----------
        iid : str or int
            Individual ID string or integer row index into ``self.df2``.
        subcohort : str or None
            Subcohort to search.  If ``None`` and ``curr_subcohort`` is also
            unset, all subcohorts are searched.

        Returns
        -------
        tuple
            ``(subcohort, iid, info)`` where *subcohort* is the resolved
            subcohort label, *iid* is the string ID, and *info* is a dict
            with keys ``'edf'`` (str) and ``'annots'`` (list of str).

        Raises
        ------
        KeyError
            If *iid* is not found in the specified (or any) subcohort.
        RuntimeError
            If *iid* appears in more than one subcohort and no subcohort is
            specified.
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
        """Download EDF and annotation files for one individual.

        Files already present in the cache are skipped.  For compressed EDF
        files (``.edf.gz`` / ``.edfz``) the companion ``.idx`` index file is
        downloaded automatically.  Updates ``curr_id``, ``curr_edf``,
        ``curr_annots``, and ``curr_subcohort``.

        A call to :meth:`cohort` must have been made first to set the active
        cohort.

        Parameters
        ----------
        iid : str or int
            Individual ID string, or integer row index into ``self.df2``.
        subcohort : str, optional
            Subcohort label.  Defaults to ``curr_subcohort``; must be
            supplied explicitly when the same ID appears in more than one
            subcohort.

        Raises
        ------
        RuntimeError
            If no cohort has been set, or if *iid* is ambiguous across
            subcohorts.
        KeyError
            If *iid* is not found in the manifest.
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

        The file is stored at ``{cdir}/{cohort}/{remote_path}``, mirroring
        the remote directory structure.  Download progress is shown via a
        ``tqdm`` progress bar.  If the file is already present on disk the
        download is silently skipped.

        Parameters
        ----------
        cohort : str
            NSRR dataset slug (e.g. ``'cfs'``).
        remote_path : str
            Path of the file within the dataset, relative to the dataset
            root (e.g. ``'polysomnography/edfs/cfs-visit5-800001.edf'``).

        Raises
        ------
        RuntimeError
            If the server returns a non-200 HTTP status code.
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
        """Download files for multiple individuals using parallel connections.

        Builds a flat list of all EDF, annotation, and (where applicable)
        ``.idx`` files required by *iids*, then fetches them concurrently
        using a thread pool.  Files already present in the cache are skipped
        before a thread is even allocated.  A summary line is printed on
        completion; individual failures are reported inline and do not abort
        remaining downloads.

        A call to :meth:`cohort` must have been made first.

        Parameters
        ----------
        iids : list of str or int
            Individual IDs to download.  Integer entries are resolved as row
            indices into ``self.df2``.
        subcohort : str, optional
            Subcohort label applied to all IDs.  Defaults to
            ``curr_subcohort``.  IDs that are ambiguous across subcohorts
            and have no subcohort specified are skipped with a warning.
        cohort : str, optional
            Dataset slug.  Defaults to ``curr_cohort``.
        max_workers : int, optional
            Maximum number of simultaneous download connections (default: 4).
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

        Calls :meth:`pull` to ensure the EDF (and all annotation files) are
        present in the cache, then creates and returns a fully attached
        :class:`~lunapi.instance.inst` object.  When multiple annotations
        are listed in the manifest, only the first is attached; the full
        list is available via ``self.curr_annots``.

        A call to :meth:`cohort` must have been made first.

        Parameters
        ----------
        iid : str or int
            Individual ID string, or integer row index into ``self.df2``.
        subcohort : str, optional
            Subcohort label.  Defaults to ``curr_subcohort``.

        Returns
        -------
        lunapi.instance.inst or None
            A fully attached instance ready for Luna commands, or ``None``
            if no cohort has been set.
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
