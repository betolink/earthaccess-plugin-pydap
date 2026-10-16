# earthaccess-pydap

Lazy [OPeNDAP](https://www.opendap.org/) access to Earthdata granules through
[PyDAP](https://www.pydap.org/) and xarray, via earthaccess.

## What OPeNDAP and PyDAP do

OPeNDAP (DAP2/DAP4) is a protocol for accessing remote scientific data without
downloading whole files. An OPeNDAP server reads a dataset natively and serves
slices of it, so you can request only the variables, coordinates and time range
you need. PyDAP is the Python client for that protocol, and xarray can open
PyDAP responses directly (`engine="pydap"`), giving you a familiar lazy
`xarray.Dataset` that pulls data on demand.

This plugin finds the OPeNDAP links in a granule's UMM, opens one granule as a
dataset (or several combined), and returns a lazy dataset. Nothing is downloaded
until you actually compute with it.

## Install

```bash
pip install earthaccess-pydap
```

## Use with earthaccess

```python
import earthaccess as ea

results = ea.search_data(short_name="MODISA_L2_OC", ...)

ds = ea.plugins.pydap.open(results, protocol="dap4")
# ds is a lazy xarray.Dataset; the data is fetched as you use it
subset = ds["chlor_a"].sel(lat=slice(40, 50)).mean()
```

`open()` is a shortcut for `run()`. You can also work with the job explicitly,
or ask for the raw result:

```python
job = ea.plugins.pydap.request(results)
ds = job.results()          # blocks until the job settles, returns the Dataset
```

Because the result is already a lazy, usable object, it is returned as-is by
`ea.open(job)`:

```python
ds = ea.open(ea.plugins.pydap.request(results))
```

### Options

| Option | Default | Meaning |
| --- | --- | --- |
| `protocol` | `"dap4"` | OPeNDAP scheme: `dap4` or `dap2` |
| `url_filter` | `None` | keep only hrefs containing this substring |
| `combine` | `"by_coords"` | how to combine several granules: `by_coords` or `nested` |
| `concat_dim` | `None` | required when `combine="nested"` |

Combining several granules into one dataset:

```python
ds = ea.plugins.pydap.open(results, combine="nested", concat_dim="time")
```

## Authentication

OPeNDAP links on NASA DAACs require Earthdata Login. The plugin uses your
earthaccess EDL session (`auth = "edl"`), so log in first — the plugin does it
for you if you have not:

```python
ea.login(strategy="netrc")
```

## Checking that a collection is supported

The plugin checks the granules' UMM for an OPeNDAP link and fails early if none
is present:

```python
ea.plugins.pydap.supports(results)   # Support(ok=True/False/None, reason=...)
```

## License

MIT.
