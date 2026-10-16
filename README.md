# earthaccess-pydap

Lazy [OPeNDAP](https://www.opendap.org/) access to Earthdata granules through
[PyDAP](https://www.pydap.org/) and xarray, via the earthaccess plugin contract.

```python
import earthaccess

results = earthaccess.search_data(short_name="MODISA_L2_OC", ...)

ds = earthaccess.plugins.pydap.open(results, protocol="dap4")
```

## Contract

- `output = "xarray"`, `auth = "edl"`, `needs = {"umm"}`.
- Returns a **lazy** `xarray.Dataset`; authentication happens on the caller's
  thread, the open itself runs in a background job.
- Options: `protocol` (`dap4`/`dap2`), `url_filter`, `combine`
  (`by_coords`/`nested`), `concat_dim`.

## Verification points

`src/earthaccess_pydap/plugin.py` isolates every unverified xarray/pydap detail
in `_open` and `with_scheme`. RelatedUrls parsing (`opendap_urls`) is pure
Python and tested directly.

## License

MIT.
