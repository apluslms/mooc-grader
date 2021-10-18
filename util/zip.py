import os
from typing import Optional
from zipfile import ZipFile, ZipInfo

def extract(zipfile: ZipFile, info: ZipInfo, path: Optional["os.PathLike[str]"] = None, pwd: Optional[bytes] = None):
    """
    Extracts a file while preserving permissions
    """
    out_path = zipfile.extract( info.filename, path=path, pwd=pwd )

    perm = info.external_attr >> 16
    os.chmod( out_path, perm )

def extract_all(zipfile: ZipFile, path: Optional["os.PathLike[str]"] = None, pwd: Optional[bytes] = None):
    """
    Extracts all files while preserving permissions
    """
    for zipinfo in zipfile.infolist():
        extract(zipfile, zipinfo, path, pwd)
