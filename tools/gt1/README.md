# GT1 USA asset identifiers

`usa-car-codes.txt` contains the 344 day/night family codes in archive order.
It is a compact, lossless representation of the CAR portion of [GTExplorer's
USA retail map](https://github.com/JeevesGB/GTExplorer/blob/069ab96f8353637a9ffc5c9b23695650e288e8ea/src/gtarcexplorer/filelists/filelist_usa_retail.txt).

Original map SHA-256: `e9da7e42d2e643948fcd0c9ecca9635d635fa2299d20ffd0411ec5701f851c97`.
Compact file SHA-256: `f8796a0e9fcd77ba905c056ad22e8d606c75f06052ab02dbbba7776ad5080472`.

The original CAR map assigns 1,376 entries. Entries 0–687 are day assets and
688–1375 are the same ordered codes with `_night` appended. Each code has a
texture at the even ordinal and a model at the next odd ordinal. Reconstructing
these rules reproduces all 1,376 original assignments exactly. These codes are
community-recovered identifiers, not verified retail car display names. They
apply only when the boot configuration contains `SCUS_941.94;1`; other discs
retain archive ordinals. A boot identifier alone does not prove byte identity
with every release bearing that identifier.

The imported map is MIT licensed; its full notice is retained in `LICENSE`.
GTExplorer's algorithm documentation also informed the independently written,
strict parsers in `gt_archive.py`. Source archive bounds and decoded byte counts
are checked independently of this name map.
