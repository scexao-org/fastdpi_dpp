from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import astropy.units as u
from astropy.coordinates import Angle, SkyCoord
from serde import field, serialize
from serde.toml import to_toml

import fastpdi_dpp as vpp
from fastpdi_dpp.constants import SATSPOT_ANGLE


## Some base classes for repeated functionality
@serialize
@dataclass(kw_only=True)
class OutputDirectory:
    output_directory: Optional[Path] = field(default=None, skip_if_default=True)
    force: bool = field(default=False, skip_if_default=True)

    def __post_init__(self):
        if self.output_directory is not None:
            self.output_directory = Path(self.output_directory)

    def to_toml(self) -> str:
        return to_toml(self)


@serialize
@dataclass
class CamFileInput:
    cam1: Optional[Path] = field(default=None, skip_if_default=True)
    cam2: Optional[Path] = field(default=None, skip_if_default=True)

    def __post_init__(self):
        if self.cam1 is not None:
            self.cam1 = Path(self.cam1)

        if self.cam2 is not None:
            self.cam2 = Path(self.cam2)

    def to_toml(self) -> str:
        return to_toml(self)


@serialize
@dataclass
class CoordinateOptions:
    """Astronomical coordinate options

    .. admonition:: Tip: GAIA
        :class: Tip

        This can be auto-generated wtih GAIA coordinate information through the command line ``dpp new`` interface.

    Parameters
    ----------
    object: str
        SIMBAD-friendly object name
    ra: str
        Right ascension in sexagesimal hour angles
    dec: str
        Declination in sexagesimal degrees
    parallax: float
        parallax of system in mas
    pm_ra: float
        Proper motion of RA axis in mas/yr, by default 0.
    pm_dec: float
        Proper motion of DEC axis in mas/yr, by default 0.
    frame: str
        Coordinate reference frame, by default "icrs".
    obstime: str
        Observation time as a string, by default "J2016" (to coincide with GAIA coordinates)
    """

    object: str
    ra: str
    dec: str
    parallax: float
    pm_ra: float = field(default=0)
    pm_dec: float = field(default=0)
    frame: str = field(default="icrs", skip_if_default=True)
    obstime: str = field(default="J2016", skip_if_default=True)

    def __post_init__(self):
        if isinstance(self.ra, str):
            self.ra_ang = Angle(self.ra, "hour")
        else:
            self.ra_ang = Angle(self.ra, "deg")
        self.ra = self.ra_ang.to_string(pad=True, sep=":")
        self.dec_ang = Angle(self.dec, "deg")
        self.dec = self.dec_ang.to_string(pad=True, sep=":")

    def to_toml(self) -> str:
        obj = {"coordinate": self}
        return to_toml(obj)

    def get_coord(self) -> SkyCoord:
        return SkyCoord(
            ra=self.ra_ang,
            dec=self.dec_ang,
            pm_ra_cosdec=self.pm_ra * u.mas / u.year,
            pm_dec=self.pm_dec * u.mas / u.year,
            distance=1e3 / self.parallax * u.pc,
            frame=self.frame,
            obstime=self.obstime,
        )


## Define classes for each configuration block
@serialize
@dataclass
class DistortionOptions:
    """Geometric distortion correction options

    .. admonition:: Advanced Usage
        :class: warning

        Distortion correction requires specialized calibration files. Please get in contact with the SCExAO team for more details

    Parameters
    ----------
    transform_filename: Path
        The path to a CSV with the distortion corrections for each camera.
    """

    transform_filename: Path

    def __post_init__(self):
        self.transform_filename = Path(self.transform_filename)

    def to_toml(self) -> str:
        obj = {"calibrate": {"distortion": self}}
        return to_toml(obj)


@serialize
@dataclass
class CalibrateOptions(OutputDirectory):
    """Options for general image calibration

    The calibration strategy is generally

    #. Subtract dark frame, if provided
    #. Normalize by flat field, if provided
    #. Bad pixel correction, if set
    #. Flip along y-axis
    #. Apply distortion correction, if provided
    #. Split left/right frames, if in PDI mode

    .. admonition:: Outputs

        If in PDI mode, two files will be saved in the output directory for each input file, with `_left` and `_right` appended. The calibrated files will be saved with the "_calib" suffix.

    Parameters
    ----------
    master_dark: Optional[Path]
        Path to master dark file. By default None.
    master_flat: Optional[Path]
        Path to master flat file. By default None.
    distortion: Optional[Path]
        (Advanced) Options for geometric distortion correction. By default None.
    fix_bad_pixels: bool
        If true, will run LACosmic algorithm for one iteration on each frame and correct bad pixels. By default false.
    output_directory : Optional[Path]
        The calibrated files will be saved to the output directory. If not provided, will use the current working directory. By default None.
    force : bool
        If true, will force this processing step to occur.

    Examples
    --------
    >>> conf = CalibrateOptions(
            master_dark="master_dark.fits",
            output_directory="calibrated"
        )
    >>> print(conf.to_toml())

    .. code-block:: toml

        [calibrate]
        output_directory = "calibrated"
        master_dark = "master_dark.fits"

        [calibrate.distortion]
        transform_filename = "20230102_fcs16000_params.csv"
    """

    master_dark: Optional[Path] = field(default=None, skip_if_default=True)
    master_flat: Optional[Path] = field(default=None, skip_if_default=True)
    fix_bad_pixels: bool = field(default=True)

    def __post_init__(self):
        super().__post_init__()
        if self.master_dark is not None:
            self.master_dark = Path(self.master_dark)
        if self.master_flat is not None:
            self.master_flat = Path(self.master_flat)

    def to_toml(self) -> str:
        obj = {"calibrate": self}
        return to_toml(obj)


@serialize
@dataclass(frozen=True)
class CoronagraphOptions:
    """Coronagraph options

    Parameters
    ----------
    iwa : float
        Coronagraph inner working angle (IWA) in mas.

    Examples
    --------
    >>> conf = CoronagraphOptions(iwa=113)
    >>> print(conf.to_toml())

    .. code-block:: toml

        [coronagraph]
        iwa = 113
    """

    iwa: float

    def to_toml(self) -> str:
        obj = {"coronagraph": self}
        return to_toml(obj)


@serialize
@dataclass(frozen=True)
class SatspotOptions:
    """Satellite spot options

    Parameters
    ----------
    radius : float
        Satellite spot radius in lambda/D, by default 15.9. If doing PDI this should be 11.2.
    angle : float
        Satellite spot position angle (in degrees), by default 45 - `PUPIL_OFFSET`.
    amp : float
        Satellite spot modulation amplitude (in nm), by default 50.

    Examples
    --------
    >>> conf = SatspotOptions(radius=11.2, amp=25)
    >>> print(conf.to_toml())

    .. code-block:: toml

        [satspots]
        radius = 11.2
        angle = 84.6
        amp = 25
    """

    radius: float = field(default=15.9)
    angle: float = field(default=SATSPOT_ANGLE)
    amp: float = field(default=50)

    def to_toml(self) -> str:
        obj = {"satspots": self}
        return to_toml(obj)


@serialize
@dataclass
class FrameSelectOptions(OutputDirectory):
    """Frame selection options

    Frame selection metrics can be measured on the central PSF, or can be done on calibration speckles (satellite spots). Satellite spots will be used if the `satspots` option is set in the pipeline. The quality metrics are

    * normvar - The variance normalized by the mean.
    * l2norm - The L2-norm, roughly equivalent to the RMS value
    * peak - maximum value

    .. admonition:: Outputs

        For each input file, a CSV with frame selection metrics for each slice will be saved in the output directory with the "_metrics" suffix and a cube with bad frames discarded will be saved with the "_selected" suffix.

    Parameters
    ----------
    cutoff : float
        The cutoff quantile for frame selection where 0 means no frame selection and 1 would discard all frames.
    metric : str
        The frame selection metric, one of `"peak"`, `"l2norm"`, and `"normvar"`, by default `"normvar"`.
    window_size : int
        The window size (in pixels) to cut out around PSFs before measuring the frame selection metric, by default 20.
    output_directory : Optional[Path]
        The trimmed files will be saved to the output directory. If not provided, will use the current working directory. By default None.
    force : bool
        If true, will force this processing step to occur.

    Examples
    --------
    >>> conf = FrameSelectOptions(cutoff=0.7, output_directory="selected")
    >>> print(conf.to_toml())

    .. code-block:: toml

        [frame_select]
        output_directory = "selected"
        cutoff = 0.7
        metric = "normvar"
    """

    cutoff: float
    metric: str = field(default="normvar")
    window_size: int = field(default=20, skip_if_default=True)

    def __post_init__(self):
        super().__post_init__()
        if self.metric not in ("peak", "l2norm", "normvar"):
            raise ValueError(f"Frame selection metric not recognized: {self.metric}")
        if self.cutoff < 0 or self.cutoff > 1:
            raise ValueError(
                f"Must use a value between 0 and 1 for frame selection quantile (got {self.cutoff})"
            )

    def to_toml(self) -> str:
        obj = {"frame_select": self}
        return to_toml(obj)


@serialize
@dataclass
class RegisterOptions(OutputDirectory):
    """Image registration options

    Image registration can be done on the central PSF, or can be done on calibration speckles (satellite spots). Satellite spots will be used if the `satspots` option is set in the pipeline. The registration methods are

    * com - centroid
    * peak - pixel at highest value
    * dft - Cross-correlation between frames using discrete Fourier transform (DFT) upsampling for subpixel accuracy
    * gaussian - Model fit using a Gaussian PSF
    * airydisk - Model fit using a Moffat PSF
    * moffat - Model fit using an Airy disk PSF

    .. admonition:: Outputs

        For each input file, a CSV with PSF centroids (or centroids for each satellite spot) will be saved in the output directory with the "_offsets" suffix and a registered cube will be saved with the "_aligned" suffix.

    Parameters
    ----------
    method : str
        The image registration method, one of `"com"`, `"peak"`, `"dft"`, `"airydisk"`, `"moffat"`, or `"gaussian"`. By default `"com"`.
    window_size : int
        The window size (in pixels) to cut out around PSFs before measuring the centroid, by default 20.
    smooth : bool
        If true, will Gaussian smooth the input frames before measuring offsets, by default true.
    dft_factor : int
        If using the DFT method, the upsampling factor (inverse of centroid precision), by default 1.
    output_directory : Optional[Path]
        The PSF offsets and aligned files will be saved to the output directory. If not provided, will use the current working directory. By default None.
    force : bool
        If true, will force this processing step to occur.

    Examples
    --------
    >>> conf = RegisterOptions(method="com", output_directory="registered")
    >>> print(conf.to_toml())

    .. code-block:: toml

        [register]
        output_directory = "registered"
        method = "com"
    """

    method: str = field(default="com")
    window_size: int = field(default=20, skip_if_default=True)
    smooth: Optional[int] = field(default=True)
    dft_factor: int = field(default=1, skip_if_default=True)

    def __post_init__(self):
        super().__post_init__()
        if self.method not in ("com", "peak", "dft", "airydisk", "moffat", "gaussian"):
            raise ValueError(f"Registration method not recognized: {self.method}")

    def to_toml(self) -> str:
        obj = {"register": self}
        return to_toml(obj)


@serialize
@dataclass
class CollapseOptions(OutputDirectory):
    """
    Cube collapse options

    * median - Pixel-by-pixel median
    * mean - Pixel-by-pixel mean
    * varmean - Pixel-by-pixel mean weighted by frame variance
    * biweight - Pixel-by-pixel biweight location

    .. admonition:: Outputs

        For each input file, a collapsed frame will be saved in the output directory with the "_collapsed" suffix.


    Parameters
    ----------
    method : str
        The collapse method, one of `"median"`, `"mean"`, `"varmean"`, or `"biweight"`. By default `"median"`.
    output_directory : Optional[Path]
        The collapsed files will be saved to the output directory. If not provided, will use the current working directory. By default None.
    force : bool
        If true, will force this processing step to occur.


    Examples
    --------
    >>> conf = CollapseOptions(output_directory="collapsed")
    >>> print(conf.to_toml())

    .. code-block:: toml

        [collapse]
        output_directory = "collapsed"
    """

    method: str = field(default="median", skip_if_default=True)

    def __post_init__(self):
        super().__post_init__()
        if self.method not in ("median", "mean", "varmean", "biweight"):
            raise ValueError(f"Collapse method not recognized: {self.method}")

    def to_toml(self) -> str:
        obj = {"collapse": self}
        return to_toml(obj)


@serialize
@dataclass
class IPOptions:
    """Instrumental polarization (IP) correction options.

    There are three main IP correction techniques

    * Ad-hoc correction using PSF photometry
        In each diff image, the partial polarization of the central PSF is measured and removed, presuming there should be no polarized stellar signal. In coronagraphic data, this uses the light penetrating the partially transmissive focal plane masks (~0.06%).
    * Ad-hoc correction using PSF photometry of calibration speckles (satellite spots)
        Same as above, but using the average correction for the four satellite spot PSFs instead of the central PSF.
    * Mueller-matrix model correction (not currently implemented)
        Uses a calibrated Mueller-matrix model which accurately reflects the impacts of all polarizing optics in FastPDI. WIP.

    .. admonition:: Outputs

        For each diff image a copy will be saved with the IP correction applied and the "_ip" file suffix attached.


    Parameters
    ----------
    method : str
        IP correction method, one of `"photometry"`, `"satspots"`, or `"mueller"`. By default, `"photometry"`
    aper_rad : float
        For photometric-based methods, the aperture radius in pixels. By default, 6.
    force : bool
        If true, will force this processing step to occur.
    """

    method: str = "photometry"
    aper_rad: float = 6
    force: bool = field(default=False, skip_if_default=True)

    def __post_init__(self):
        if self.method not in ("photometry", "satspots", "mueller"):
            raise ValueError(f"Polarization calibration method not recognized: {self.method}")

    def to_toml(self) -> str:
        obj = {"polarimetry": {"ip": self}}
        return to_toml(obj)


@serialize
@dataclass
class PolarimetryOptions(OutputDirectory):
    """Polarimetric differential imaging (PDI) options

    .. admonition:: Warning: experimental
        :class: warning

        The polarimetric reduction in this pipeline is an active work-in-progress. Do not consider any outputs publication-ready without further vetting and consultation with the SCExAO team.

    PDI is processed after all of the individual file processing since it requires sorting the files into complete sets for the triple-differential calibration.

    .. admonition:: Outputs

        Diff images will be saved in the output directory. If IP options are set, the IP corrected frames will also be saved.

    Parameters
    ----------
    ip : Optional[IPOptions]
        Instrumental polarization (IP) correction options, by default None.
    N_per_hwp : int
        Number of cubes expected per HWP position, by default 1.
    derotate_pa : bool
        If true, will not assume the HWP is in pupil-tracking mode (the default) which requires additional rotation of the Stokes vectors by the parallactic angle. By defult, False.
    output_directory : Optional[Path]
        The diff images will be saved to the output directory. If not provided, will use the current working directory. By default None.
    force : bool
        If true, will force this processing step to occur.

    Examples
    --------
    >>> conf = PolarimetryOptions(ip=IPOptions(), output_directory="pdi")
    >>> print(conf.to_toml())

    .. code-block:: toml

        [polarimetry]
        output_directory = "pdi"

        [polarimetry.ip]
        method = "photometry"
        aper_rad = 6
    """

    ip: Optional[IPOptions] = field(default=None, skip_if_default=True)
    derotate_pa: bool = field(default=False, skip_if_default=True)

    def __post_init__(self):
        super().__post_init__()
        if self.ip is not None and isinstance(self.ip, dict):
            self.ip = IPOptions(**self.ip)

    def to_toml(self) -> str:
        obj = {"polarimetry": self}
        return to_toml(obj)


@serialize
@dataclass
class CamCtrOption:
    cam1: Optional[list[float]] = field(default=None, skip_if_default=True)
    cam2: Optional[list[float]] = field(default=None, skip_if_default=True)

    def __post_init__(self):
        if self.cam1 is not None:
            self.cam1 = list(self.cam1)
            if len(self.cam1) == 0:
                self.cam1 = None
        if self.cam2 is not None:
            self.cam2 = list(self.cam2)
            if len(self.cam2) == 0:
                self.cam2 = None


@serialize
@dataclass
class ProductOptions(OutputDirectory):
    """The output products from the processing pipeline.

    .. admonition:: Outputs

        **Header Table:**

        A table with the header information of all the input files will be saved to a CSV in the output directory.

        **ADI Outputs:**

        The ADI outputs will include a data cube and the corresponding derotation angles. If in PDI mode, there will be two cubes, one for each beam. For ADI analysis, you can either interleave the two cubes into one cube with double the frames, add the two camera frames before post-processing, or add the two ADI residuals from each camera after post-processing.

        **PDI Outputs:**

        If `polarimetry` is set, PDI outputs will be constructed from the double- or triple-differential method. This includes a cube with various Stokes quantities from each HWP cycle, and a derotated and collapsed cube of Stokes quantities. The Stokes quantities are listed in the "STOKES" header, and are

        #. Stokes I
        #. Stokes Q
        #. Stokes U
        #. Radial Stokes Qphi
        #. Radial Stokse Uphi
        #. Linear polarized intensity
        #. Angle of linear polarization

    Parameters
    ----------
    header_table : bool
        If true, saves a CSV with header information, by default true.
    adi_cubes : bool
        If true, saves ADI outputs
    pdi_cubes : bool
        If true, saves PDI triple-diff cubes
    output_directory : Optional[Path]
        The products will be saved to the output directory. If not provided, will use the current working directory. By default None.
    force : bool
        If true, will force all products to be recreated step to occur.

    Examples
    --------
    >>> conf = ProductOptions(output_directory="products")
    >>> print(conf.to_toml())

    .. code-block:: toml

        [products]
        output_directory = "products"
    """

    header_table: bool = field(default=True, skip_if_default=True)
    adi_cubes: bool = field(default=True, skip_if_default=True)
    pdi_cubes: bool = field(default=True, skip_if_default=True)

    def to_toml(self) -> str:
        obj = {"products": self}
        return to_toml(obj)


## Define classes for entire pipelines now
@serialize
@dataclass
class PipelineOptions:
    """Data Processing Pipeline options

    The processing configuration is all done through this class, which can easily be converted to and from TOML. The options will set the processing steps in the pipeline. An important paradigm in the processing pipeline is skipping unnecessary operations. That means if a file already exists, the pipeline will only reprocess it if the `force` flag is set, which will reprocess all files for that step (and subsequent steps), or if the input file or files are newer. You can try this out by deleting one calibrated file from a processed output and re-running the pipeline.

    Parameters
    ----------
    name : str
        filename-friendly name used for outputs from this pipeline. For example "20230101_ABAur"
    coordinate : Optional[CoordinateOptions]
    frame_centers : Optional[dict[str, Optional[list]]]
        Estimates of the star position in pixels (x, y) for each camera provided as a dict with "cam1" and "cam2" keys. If not provided, will use the geometric frame center, by default None.
    coronagraph : Optional[CoronagraphOptions]
        If provided, sets coronagraph-specific options and processing
    satspots : Optional[SatspotOptions]
        If provided, sets satellite-spot specific options and enable satellite spot processing for frame selection and image registration
    calibrate : Optional[CalibrateOptions]
        If set, provides options for basic image calibration
    frame_select : Optional[FrameSelectOptions]
        If set, provides options for frame selection
    register : Optional[RegisterOptions]
        If set, provides options for image registration
    collapse : Optional[CollapseOptions]
        If set, provides options for collapsing image cubes
    polarimetry : Optional[PolarimetryOptions]
        If set, provides options for polarimetric differential imaging (PDI)
    products : Optional[ProductOptions]
        If set, provides options for saving metadata, ADI, and PDI outputs.
    version : str
        The version of `fastpdi_dpp` that this configuration file is valid with. Typically not set by user.

    Notes
    -----
    **Frame Centers**

    In PDI mode frame centers need to be given as a dictionary of x, y pairs, like

    .. code-block:: python

        frame_centers = {
            "left": (127.5, 127.5),
            "right": (127.5, 127.5)
        }
    It is important to note that these frame centers are in the *raw* frames. If you open up the frames in DS9 and set the cross on the image center, you can copy the x, y coordinates directly into the configuration. We recommend doing this, especially for coronagraphic data since the satellite spot cutout indices depend on the frame centers and any off-center data may not register appropriately.

    Examples
    --------
    >>> conf = PipelineOptions(
            name="test_config",
            coronagraph=dict(iwa=113),
            satspots=dict(radius=11.2),
            calibrate=dict(output_directory="calibrated"),
            collapse=dict(output_directory="collapsed"),
            polarimetry=dict(output_directory="pdi"),
        )
    >>> print(conf.to_toml())

    .. code-block:: toml

        name = "test_config"
        version = "0.2.0"

        [coronagraph]
        iwa = 113

        [satspots]
        radius = 11.2
        angle = 84.6
        amp = 50

        [calibrate]
        output_directory = "calibrated"

        [collapse]
        output_directory = "collapsed"

        [polarimetry]
        output_directory = "pdi"

    """

    name: str
    coordinate: Optional[CoordinateOptions] = field(default=None, skip_if_default=True)
    frame_centers: Optional[CamCtrOption] = field(default=None, skip_if_default=True)
    coronagraph: Optional[CoronagraphOptions] = field(default=None, skip_if_default=True)
    satspots: Optional[SatspotOptions] = field(default=None, skip_if_default=True)
    calibrate: Optional[CalibrateOptions] = field(default=None, skip_if_default=True)
    frame_select: Optional[FrameSelectOptions] = field(default=None, skip_if_default=True)
    register: Optional[RegisterOptions] = field(default=None, skip_if_default=True)
    collapse: Optional[CollapseOptions] = field(default=None, skip_if_default=True)
    polarimetry: Optional[PolarimetryOptions] = field(default=None, skip_if_default=True)
    products: Optional[ProductOptions] = field(default=None, skip_if_default=True)
    version: str = vpp.__version__

    def __post_init__(self):
        if self.coordinate is not None and isinstance(self.coordinate, dict):
            self.coordinate = CoordinateOptions(**self.coordinate)
        if self.coronagraph is not None and isinstance(self.coronagraph, dict):
            self.coronagraph = CoronagraphOptions(**self.coronagraph)
        if self.satspots is not None and isinstance(self.satspots, dict):
            self.satspots = SatspotOptions(**self.satspots)
        if self.calibrate is not None and isinstance(self.calibrate, dict):
            self.calibrate = CalibrateOptions(**self.calibrate)
        if self.frame_select is not None and isinstance(self.frame_select, dict):
            self.frame_select = FrameSelectOptions(**self.frame_select)
        if self.register is not None and isinstance(self.register, dict):
            self.register = RegisterOptions(**self.register)
        if self.collapse is not None and isinstance(self.collapse, dict):
            self.collapse = CollapseOptions(**self.collapse)
        if self.polarimetry is not None and isinstance(self.polarimetry, dict):
            self.polarimetry = PolarimetryOptions(**self.polarimetry)
        if self.products is not None and isinstance(self.products, dict):
            self.products = ProductOptions(**self.products)

    def to_toml(self) -> str:
        return to_toml(self)
