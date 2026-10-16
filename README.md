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

ds = ea.plugins.pydap.request(results, protocol="dap4").results()
# ds is a lazy xarray.Dataset; the data is fetched as you use it
subset = ds["chlor_a"].sel(lat=slice(40, 50)).mean()
```

`request()` returns a `Job`; `results()` blocks and returns the dataset. Because
that object is already lazy and usable, `ea.open(job)` returns it as-is:

```python
ds = ea.open(ea.plugins.pydap.request(results))
```

### Access pattern (important for speed)

A **single granule** is opened lazily (`xr.open_dataset`), so xarray pushes your
subset to the OPeNDAP server as a constraint expression and only the slice you
ask for is downloaded:

```python
ds = ea.plugins.pydap.request(one_granule).results()
ds["analysed_sst"].sel(lon=slice(-98, -80), lat=slice(18, 31)).plot()
```

For **several granules** the plugin concatenates them lazily with dask
(`combine="nested"`, `parallel=True`). Dask fetches whole chunks, so pass
`chunks` sized to your subset or you will download far more than you need:

```python
ds = ea.plugins.pydap.request(many_granules, chunks={"lat": 400, "lon": 400}).results()
```

### Inspect the remote file

`request()` takes an `engine`: `"xarray"` (default) returns a lazy
`xarray.Dataset`, `"pydap"` returns the native dataset from `pydap.open_url`
(one per granule URL; a list for several). Use the native dataset to list
variables and operations without downloading data:

```python
pyds = ea.plugins.pydap.request(results, engine="pydap").results()
pyds.tree()
list(pyds.keys())
```

### Options

| Option | Default | Meaning |
| --- | --- | --- |
| `engine` | `"xarray"` | `"xarray"` -> lazy `xarray.Dataset`; `"pydap"` -> native pydap dataset(s) |
| `protocol` | `"dap4"` | OPeNDAP scheme: `dap4` or `dap2` |
| `url_filter` | `None` | keep only hrefs containing this substring |
| `combine` | `"nested"` | how to combine several granules: `by_coords` or `nested` |
| `concat_dim` | `"time"` | concat dimension when `combine="nested"` |
| `chunks` | `None` | dask chunking for multi-granule opens (`"auto"` by default); pass e.g. `{"lat": 400, "lon": 400}` to fetch only your subset |

Combining several granules into one dataset:

```python
ds = ea.plugins.pydap.request(many_granules, concat_dim="time", chunks={"lat": 400, "lon": 400}).results()
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
is present. It reports OPeNDAP's operations (lazy reads, dimension/variable
subsetting):

```python
ea.plugins.pydap.supports(results)
# Capabilities('pydap supported C1996881146-POCLOUD', operations=3)
#   operations: lazy_read, subset_dimension, subset_variable

# By short name alone there are no granule links to confirm against:
ea.plugins.pydap.capabilities("MUR-JPL-L4-GLOB-v4.1")  # ok=None
```

## License

MIT.
