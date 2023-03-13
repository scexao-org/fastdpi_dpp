# Pipeline

The FastPDI data processing pipeline uses a configuration file to automate the bulk reduction of FastPDI data. To run the pipeline, use the `dpp run` script

{{dpprun_help}}

or create a `Pipeline` object and call the `run` method.

## Processing steps

The pipeline will reduce the data in the following order
1. Calibration
2. Frame Selection
3. Image Registration
4. Collapsing
6. Polarimetric differential imaging

```{admonition} Warning: Large data volume
:class: warning
The data volumes associated with typical FastPDI observations can easily balloon into the terabyte (TB) range when using this pipeline. It is strongly recommended to work with a large attached storage.

As an example, a half-night of coronagraphic data can easily produce 200 GB of raw data. The calibration, frame selection, and image-registration steps will *each* make a copy, leading to a data volume three to four times larger (600 GB to 800 GB). After the individual frames are collapsed the data size reduces by about two orders of magnitude, making them negligible in comparison.

An easy way to reclaim storage space is to delete the intermediate data products after you have finalized a reduction. You can always rerun the pipeline later to reproduce the files.
```

```{admonition} Troubleshooting
:class: tip
If you run into problems, take a look at the debug file, which will be saved to the same directory as the input config file with `_debug.log` appended to the file name as well as in the output directory.

    vpp run config.toml VMPA*.fits
    tail config_debug.log
```


## Configuration

The configuration file uses the [TOML](https://toml.io) format. There are many options that have defaults, sometimes even sensible ones. In general, if an entire section is missing, the operation will be excluded. Note that sections for the configuration (e.g., `[calibration]`, `[frame_selection]`) can be in any order, although keeping them in the same order as the pipeline execution may be clearer.

We use [semantic versioning](https://semver.org/), so there are certain guarantees about the backwards compatibility of the pipeline, which means you don't have to have the exact same version of `fastpdi_dpp` as in the configuration- merely a version that is compatible.

### General Options


```{eval-rst}
.. autoclass:: fastpdi_dpp.pipeline.pipeline.Pipeline
    :members:
.. autoclass:: vampires_dpp.pipeline.config.CoordinateOptions
.. autoclass:: vampires_dpp.pipeline.config.ProductOptions
```

### Coronagraph Options

```{eval-rst}
.. autoclass:: fastpdi_dpp.pipeline.config.CoronagraphOptions
.. autoclass:: fastpdi_dpp.pipeline.config.SatspotOptions
```

### Calibration Options

```{eval-rst}
.. autoclass:: fastpdi_dpp.pipeline.config.CalibrateOptions
.. autoclass:: fastpdi_dpp.pipeline.config.DistortionOptions
```

### Frame Selection Options

```{eval-rst}
.. autoclass:: fastpdi_dpp.pipeline.config.FrameSelectOptions
```

### Image Registration Options

```{eval-rst}
.. autoclass:: fastpdi_dpp.pipeline.config.RegisterOptions
```
### Collapsing Options

```{eval-rst}
.. autoclass:: fastpdi_dpp.pipeline.config.CollapseOptions
```

### Polarimetry Options

```{eval-rst}
.. autoclass:: fastpdi_dpp.pipeline.config.PolarimetryOptions
.. autoclass:: fastpdi_dpp.pipeline.config.IPOptions
```


## Templates

### Polarimetric Differential Imaging (PDI)

{{pdi_toml}}

### Single-cam

For single-cam data you can elude all of the `cam2` keys in the configuration.

{{singlecam_toml}}

### Spectral Differential Imaging (SDI)

```{admonition} Warning: WIP
:class: warning

The full functionality for SDI is not implemented, but the collapsed data can be used as inputs to manual reductions, for now.
```

SDI reduction looks a lot like PDI reduction without the polarimetry.

{{sdi_toml}}
