import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
from astropy.io import fits
from numpy.typing import ArrayLike
from packaging import version
from scipy.stats import circmean


def average_angle(angles: ArrayLike):
    """
    Return the circular mean of the given angles in degrees.

    Parameters
    ----------
    angles : ArrayLike
        Angles in degrees, between [180, -180]

    Returns
    -------
    average_angle
        The average angle in degrees via the circular mean
    """
    rads = np.deg2rad(angles)
    radmean = circmean(rads, high=np.pi, low=-np.pi)
    return np.rad2deg(radmean)


def find_dark_settings(filelist):
    exp_set = set()
    for filename in filelist:
        with fits.open(filename) as hdus:
            hdr = hdus[0].header
            texp = hdr["EXPTIME"]  # exposure time in seconds
            gain = hdr["U_EMGAIN"]
            exp_set.add((texp, gain))

    return exp_set


def check_version(config: str, vpp: str) -> bool:
    """
    Checks compatibility between versions following semantic versioning.

    Parameters
    ----------
    config : str
        Version string for the configuration
    vpp : str
        Version string for `fastpdi_dpp`

    Returns
    -------
    bool
    """
    config_maj, config_min, config_pat = version.parse(config).release
    vpp_maj, vpp_min, vpp_pat = version.parse(vpp).release
    if vpp_maj == 0:
        flag = config_maj == vpp_maj and config_min == vpp_min and vpp_pat >= config_pat
    else:
        flag = config_maj == vpp_maj and vpp_min >= config_min
        if vpp_min == config_min:
            flag = flag and vpp_pat >= config_pat
    return flag


def get_paths(
    filename, /, suffix=None, outname=None, output_directory=None, filetype=".fits", **kwargs
):
    path = Path(filename)
    _suffix = "" if suffix is None else f"_{suffix}"
    if output_directory is None:
        output_directory = path.parent
    else:
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
    if outname is None:
        outname = re.sub("\.fits(\..*)?", f"{_suffix}{filetype}", path.name)
    outpath = output_directory / outname
    return path, outpath


def any_file_newer(filenames, outpath):
    out_mt = Path(outpath).stat().st_mtime
    gen = (Path(f).stat().st_mtime > out_mt for f in filenames)
    return any(gen)


class FileType(Enum):
    GEN2 = 0
    OG = 1


@dataclass(frozen=True)
class FileInfo:
    file_type: FileType
    camera: int

    def __post_init__(self):
        if not (self.camera == 1 or self.camera == 2):
            raise ValueError(f"Invalid camera number {self.camera}")

    @classmethod
    def from_hdr(cls, header):
        if "U_FLCSTT" in header:
            filetype = FileType.GEN2
        else:
            filetype = FileType.OG
        camera = header["U_CAMERA"]
        return cls(filetype, camera)

    @classmethod
    def from_file(cls, filename, ext: int | str = 0):
        with fits.open(filename) as hdus:
            hdu = hdus[ext]
            return cls.from_hdr(hdu.header)
