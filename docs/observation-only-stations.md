# Observation-only stations

These stations have **no PETSS forecasts in this viewer**. A free, independent
GitHub Actions workflow (`fetch-observations.yml`) retrieves static JSON every
30 minutes, separately from PETSS archive availability. The existing six PETSS
stations, raw forecast files, tide products and training pipeline are unchanged.

Observations are stored in their source datum, with UTC timestamps and feet.
The browser converts source observations into the threshold's datum, then applies
any selected display offset to both observations and threshold. The window is
72 hours ending at the latest valid observation. Nulls and intervals over 30
minutes break the line. Data older than three hours are labeled stale; retrieval
failures retain the last successful data and explicitly show an error. Neither
forecast nor missing observation values are manufactured. Thresholds below are
user-supplied base flood levels, not automatically imported flood categories.

## Verified references (retrieved 2026-10-19)

| ID | Official name | Source / source datum | Base flood | Supported display |
| --- | --- | --- | --- | --- |
| BSGL1 | Barataria Bay and Waterway at Bayou Segnette near Westwego | NOAA NWPS, Stage (ft), USACE/CPRA gauge zero 0 ft NAVD88 | 2.50 ft NAVD88 | NAVD88 |
| BYGL1 / 8762482 | West Bank 1, Bayou Gauche, LA | NOAA CO-OPS water_level, MSL | 1.20 ft MSL | MSL (default), NAVD88 |
| MAUL1 / USGS 07380215 | Amite River at Hwy 22 near Maurepas | NOAA NWPS Stage = USGS 00065 gauge height (ft) | 4.00 ft NAVD88 | NAVD88, after subtracting 1.38 ft from gauge height |

MHHW and MLLW are disabled for these three stations because no authoritative
station-specific tidal transformations were verified. The six PETSS stations
still start in MHHW; visiting an observation station does not replace the tidal
datum preference. The threshold always remains stored in the user's original
datum.

### BSGL1

- https://api.water.noaa.gov/nwps/v1/gauges/BSGL1
- https://api.water.noaa.gov/nwps/v1/gauges/BSGL1/stageflow
- NWPS attributes the observations to USACE station **82745**:
  https://rivergages.mvr.usace.army.mil/WaterControl/stationinfo2.cfm?sid=82745&fid=&dt=S
- That station page identifies **Bayou Segnette Sector Gate - Protected Side**,
  operated by CPRA, and explicitly states **Gage Zero: 0 Ft. NAVD88**. Thus
  `NAVD88 elevation = NWPS Stage + 0.00 ft`. NWPS itself has no vertical datum
  metadata for this gauge; the linked operator reference supplies it.

### BYGL1

- https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8762482/datums.json?units=english
- https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=water_level&station=8762482&date=recent&datum=MSL&units=english&time_zone=gmt&format=json
- CO-OPS lists MSL = **32.00 ft**, NAVD88 = **31.52 ft**, both above station
  datum, epoch **2012–2016**, accepted **Nov 9, 2020**. MSL means this station's
  published **Mean Sea Level**, not NAVD88 or a generic sea-level reference.
- `NAVD88 elevation = MSL height + (32.00 - 31.52) = MSL + 0.48 ft`.
  Therefore the threshold is **1.68 ft NAVD88**, or exactly **1.20 ft MSL**.
- Only STND, MSL and NAVD88 are returned; no MHHW/MLLW is inferred. The fetcher
  refreshes the CO-OPS datum difference on each retrieval.

### MAUL1: conflicting NOAA metadata, resolved using current USGS series

- https://api.water.noaa.gov/nwps/v1/gauges/MAUL1
- https://api.water.noaa.gov/nwps/v1/gauges/MAUL1/stageflow
- https://water.noaa.gov/gauges/MAUL1
- https://waterservices.usgs.gov/nwis/site/?format=rdb&sites=07380215&siteOutput=expanded
- https://waterservices.usgs.gov/nwis/iv/?format=json&sites=07380215&parameterCd=00065,63160&period=P1D

NWPS's API lists NAVD88 with value 0, while its HTML embeds an older local note:
“To convert to NAVD88, subtract 0.90 feet.” Neither agrees with the current
operator measurements. The USGS site file lists gauge-zero altitude **−1.38 ft
NAVD88**, accuracy **0.16 ft**. More decisively, simultaneous USGS **00065**
(gauge height) and **63160** (“Stream water level elevation above NAVD 1988,
in ft”, method **NAVD88 GEOID18**) differ by **−1.38 ft**. NWPS Stage matches
00065, not 63160. For example, at **2026-10-19 11:00 UTC**, NWPS and USGS gauge
height were **2.81 ft**, while the USGS NAVD88 series was **1.43 ft**.

The viewer therefore applies **−1.38 ft** to NWPS observations and leaves the
user's **4.00 ft NAVD88** threshold unchanged. This is equivalent to **5.38 ft
gauge height**. It never applies −1.38 to already converted elevations. The
fetcher checks overlapping NWPS/USGS observations against both USGS parameters
on every refresh (0.02-ft rounding tolerance). A disagreement or inability to
verify retains prior data with an error instead of silently changing datum.

Preserved source excerpts and paired observations are in
`docs/observation-references/`. NOAA's inconsistent MAUL1 metadata remains an
upstream issue; current USGS operator evidence is the reference used here.

## Validation

Run `python -m unittest discover -s tests -p 'test_*.py'`,
`node --test tests/*.cjs`, and `node tests/browser-smoke.js` (Playwright with
Chromium). The PR workflow runs these checks, including all nine stations,
threshold placement, supported and unavailable datums, forecast preservation,
mobile rendering, source failures, stale data and out-of-order station loads.
