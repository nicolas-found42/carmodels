# Redline native car extraction

`cars/index.json` records the extracted car configuration variants and their source
hashes. Base game cars live under `cars/shared/base/assets/`. Add-on cars live in
separate `cars/addons/` namespaces, with the original car envelope under `source/`,
unwrapped files under `unpacked/`, and decoded packed resources under
`packages/<number>/assets/`. Loose native plug-ins keep their resource files under
`unpacked/`.

The extraction retains native `.car` configuration files, `.mdl` models,
textures, sounds and support resources. It keeps the entire base resource package
because plug-ins refer to shared resources, including wheels. That base directory
also contains non-car resources. The SketchUp Lotus Exige authoring file is retained
as an additional source artifact. Counts in the index describe configuration
variants; they do not identify unique real-world vehicles.

The index includes literal `carName` declarations and quoted configuration fields,
their source line numbers, and candidate local/base resource matches. Resource
lookup uses the native ASCII case folding and suffix order (`.txr`, `.ima`, exact
name). The candidate list does not assert plug-in loading precedence or resolve
every transitive dependency. Original native packages retain their complete tables,
including unreadable slots whose runtime meaning remains unknown.

Finder icon carriage returns are encoded as `%0D` in output filenames. Literal
percent signs are encoded as `%25`; original resource names remain in the index.
Original add-on archives retain metadata and resource-fork carriers, while unpacked
outputs represent their regular data forks and embedded metadata sidecars.

## Reproduce and verify

The native reader requires Python 3.9 or newer and no third-party packages. The
HFS/StuffIt staging step was performed with a read-only raw HFS image and the
installed XADMaster framework from The Unarchiver. This tool accepts that staged
base package and add-on manifest; it does not implement HFS or StuffIt itself.
The original DMG and StuffIt hashes, staging evidence, framework coverage limits,
and native decoder evidence are documented in
[`research/redline-extraction.md`](../research/redline-extraction.md).

The retained staging for this run is in `.scratch/redline/`. To rederive and check
the existing extraction without overwriting it:

```sh
python3 tools/extract_redline_cars.py \
  --base-package redline/cars/shared/base/data.redplug \
  --addons-manifest .scratch/redline/addons/car-assets-manifest.json \
  --addons-root .scratch/redline/addons \
  --check
```

For a fresh extraction, supply the independently staged base package and use
`--output <empty-or-absent-directory>` without `--check`. A nonempty destination
is refused. All staged artifact hashes and configuration coverage are checked
before writing, and the complete output is staged before publication. `--check`
rederives all expected native bytes and rejects missing, extra, changed or linked
output files. A fresh clone needs the locally supplied installers and regenerated
HFS/StuffIt staging; the scratch working set is not committed.

An optional `--assess-output <new-receipt-path-outside-cars>` screens and sends a
bounded sample of car configuration inventory to Jev. Its Choice, Noul and Score
judgments are advisory and cannot rename, discard or modify native files. Review,
failure and warning outcomes accept no automatic semantic labels. Credentials stay
in the local process environment. Offline extraction and verification require no API
key or network access.

Native mesh/texture conversion and library import now publish 128 drawable cars
from 129 configurations into both source and dealership catalogs. See
[conversion and library evidence](../research/redline-library.md) for rebuilding,
verified checks and per-car omissions. Extraction and static conversion have not
established game execution or game-render fidelity.
