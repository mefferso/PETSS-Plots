# Water-level display datums

Both `index.html` (six-station PETSS viewer) and `surge.html` (New Canal
surge timeline) initially display heights in MHHW. MLLW remains selectable.
Selections survive redraws, station changes and dashboard refreshes; a fresh
page load starts in MHHW. CSVs, generated JSON, observations, forecast model
inputs, archives and training thresholds remain in their original MLLW datum.

## Pilots Station, East, Southwest Pass (8760922)

Base/minor flood threshold: **3.50 ft MLLW** (user-specified).

NOAA CO-OPS Metadata API, English units:
https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8760922/datums.json?units=english

Human-readable station reference:
https://tidesandcurrents.noaa.gov/datums.html?id=8760922

Retrieved October 19, 2026; response preserved in `pilots-station-noaa-datums.json`.
NOAA reports epoch **2012–2016**, accepted date **February 27, 2018**, with a
**NOTICE OF PROVISIONAL DATUM** disclaimer: these elevations remain subject to
revision. The metadata names Grand Isle as the control station; the elevations
used here are explicitly Pilots Station's own published values.

| Datum | Elevation above the same station datum (ft) |
| --- | ---: |
| MLLW | 30.84 |
| MHHW | 32.01 |

MHHW is 1.17 ft above MLLW. Thus the signed MLLW-to-MHHW display correction is
**−1.17 ft**, replacing the viewer's undocumented 1.08-ft offset.

`Threshold_MHHW = 3.50 + (30.84 - 32.01) = 2.33 ft MHHW`.

All height traces, uncertainty bounds, threshold lines and peak elevations use
the same station offset. Exceedance margins and tidal ranges are unchanged.
Other stations retain their existing offsets and flood thresholds. In the
New Canal surge timeline, its existing 0.41-ft offset applies to tide, total
water level, observations, extrema and tide markers; surge residuals, surge
bands, wind values and tidal ranges are differences and are not shifted.

## Audit and verification

The MLLW defaults in `config.yml`, CO-OPS Python functions, archive event
selection, forecast CLI and NOAA tide-fetch workflow are intentional storage
and model assumptions, not display defaults. The PETSS extraction workflow
copies source CSV values; the surge build workflow emits source heights and
surge differences. Neither needs data regeneration for a display change.
The new PR workflow runs `node --test tests/*.cjs`, which executes both pages'
actual inline code against checked-in station and dashboard data with DOM and
chart-library adapters. It verifies chart inputs rather than pixels. No test
framework dependencies are required. Production fetch/build/train workflows
remain unchanged and are not PR-triggered; training is unrelated to this change.
