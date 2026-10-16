# earthaccess-pydap

OPeNDAP access to Earthdata granules through
[PyDAP](https://www.pydap.org/) and xarray, via earthaccess.

## What OPeNDAP and PyDAP do

OPeNDAP (DAP2/DAP4) is a protocol for accessing remote scientific data without
downloading whole files. An OPeNDAP server reads a dataset natively and serves
slices of it, so you can request only the variables, coordinates and time range
you need. PyDAP is the Python client for that protocol, and xarray opens PyDAP
responses with `engine="pydap"`, giving you a lazy `xarray.Dataset` that pulls
data on demand.

This plugin is a **request**: it finds the OPeNDAP links in a granule's UMM and
returns a completed `Job`. Depending on `client`, `results()` gives you either
the OPeNDAP URLs to open with xarray, or the native pydap datasets. The plugin
deliberately does not open the data itself, because opening often needs xarray
kwargs tuned to the dataset.

## Install

```bash
pip install earthaccess-pydap
```

## Use with earthaccess

```python
import earthaccess as ea
import xarray as xr

results = ea.search_data(short_name="MUR-JPL-L4-GLOB-v4.1", ...)

# client="xarray" (default): assets are OPeNDAP DAP4 URLs with a variable
# constraint, ready for xarray.
assets = ea.plugins.pydap.request(
    results, variables=["analysed_sst", "lat", "lon", "time"]
).results()
urls = [asset.href for asset in assets]

session = ea.get_requests_https_session()
ds = xr.open_mfdataset(
    urls,
    engine="pydap",
    session=session,
    combine="nested",
    concat_dim="time",
    parallel=True,
    chunks={"lat": 400, "lon": 400},  # chunk to your subset
)
```

A single granule: `xr.open_dataset(urls[0], engine="pydap", session=session)`.

`client="pydap"` returns the native pydap datasets instead (metadata plus lazy
arrays), for navigating the file and its native operations:

```python
pyds = ea.plugins.pydap.request(results, client="pydap").results()[0]
pyds.tree()
list(pyds.keys())
```

### Options

| Option | Default | Meaning |
| --- | --- | --- |
| `client` | `"xarray"` | `"xarray"` -> asset URLs with a DAP4 constraint; `"pydap"` -> native pydap datasets |
| `protocol` | `"dap4"` | OPeNDAP scheme: `dap4` or `dap2` |
| `variables` | `[]` | variables for the constraint expression (`?dap4.ce=/lon;/lat;...`) |
| `url_filter` | `None` | keep only hrefs containing this substring |

The generated URL looks like:

```
dap4://opendap.earthdata.nasa.gov/collections/C.../granules/...?dap4.ce=/lon;/lat;/time
```

## Access pattern (important for speed)

xarray only pushes your subset to the server when the array is kept lazy. A
single granule opened with `xr.open_dataset(..., engine="pydap")` is lazy, so
`.sel(...)` becomes a server-side constraint and only the slice is fetched. For
several granules, dask is involved, so pass `chunks` sized to your subset (as
above) or it will fetch whole files.

## Authentication

OPeNDAP links on NASA DAACs require Earthdata Login. The plugin uses your
earthaccess EDL session (`auth = "edl"`); get one for xarray with
`session = ea.get_requests_https_session()`.

## Checking that a collection is supported

The plugin checks the granules' UMM for an OPeNDAP link and fails early if none
is present. It reports OPeNDAP's operations (lazy reads, dimension/variable
subsetting):

```python
ea.plugins.pydap.supports(results)
# Capabilities('pydap supported C1996881146-POCLOUD', operations=3)
#   operations: lazy_read, subset_dimension, subset_variable
```

## License

MIT.
