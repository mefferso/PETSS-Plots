"""Fetch free NOAA observation products; retain last good data on station failures."""
import json
import math
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIONS = {
    'BSGL1': dict(name='Barataria Bay and Waterway at Bayou Segnette near Westwego',
                  source='NOAA NWPS (USACE / CPRA)', nativeDatum='Gauge height', datum='NAVD88',
                  nativeToDisplay=0.0, threshold=2.50, thresholdDatum='NAVD88', offsets={'NAVD88': 0.0}),
    'BYGL1': dict(name='West Bank 1, Bayou Gauche, LA', coopsId='8762482',
                  source='NOAA CO-OPS', nativeDatum='MSL', datum='MSL', nativeToDisplay=0.0,
                  threshold=1.20, thresholdDatum='MSL', offsets={'MSL': 0.0, 'NAVD88': 0.48}),
    'MAUL1': dict(name='Amite River at Hwy 22 near Maurepas',
                  source='NOAA NWPS (USGS 07380215)', nativeDatum='Gauge height', datum='NAVD88',
                  nativeToDisplay=-1.38, threshold=4.00, thresholdDatum='NAVD88', offsets={'NAVD88': 0.0}),
}

def get_json(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'PETSS-Plots observation collector'}), timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def normalize(rows, time_key, value_key):
    values = {}
    for row in rows:
        try:
            stamp = datetime.fromisoformat(row[time_key].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            stamp = stamp.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
        except (ValueError, KeyError, TypeError):
            continue
        try:
            value = float(row[value_key])
            if not math.isfinite(value) or value <= -999:
                value = None
        except (ValueError, KeyError, TypeError):
            value = None
        values[stamp] = value
    return [dict(time=t, value=v) for t,v in sorted(values.items())]

def collect(lid, config):
    if config.get('coopsId'):
        url = ('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'
               'product=water_level&station=8762482&date=recent&datum=MSL&units=english&time_zone=gmt&format=json')
        raw = get_json(url)
        if raw.get('metadata',{}).get('id') != config['coopsId']:
            raise ValueError('CO-OPS station mismatch or API error')
        rows = normalize(raw.get('data',[]), 't', 'v')
    else:
        url = f'https://api.water.noaa.gov/nwps/v1/gauges/{lid}/stageflow'
        raw = get_json(url)['observed']
        if raw.get('primaryUnits') != 'ft' or raw.get('primaryName') != 'Stage':
            raise ValueError('Unexpected NWPS variable or units')
        rows = normalize(raw.get('data',[]), 'validTime', 'primary')
    if lid == 'BYGL1':
        metadata = get_json('https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8762482/datums.json?units=english')
        elevations = {d['name']: d['value'] for d in metadata['datums']}
        if metadata['units'] != 'feet':
            raise ValueError('Unexpected datum metadata units')
        config = dict(config, offsets={'MSL': 0.0, 'NAVD88': round(elevations['MSL']-elevations['NAVD88'], 6)})
    if lid == 'MAUL1':
        # NWPS metadata/page notes disagree with current USGS measurements.
        # Verify the configured gauge-zero against simultaneous 00065/63160 values.
        paired = get_json('https://waterservices.usgs.gov/nwis/iv/?format=json&sites=07380215&parameterCd=00065,63160&period=P1D')
        series = {}
        for item in paired['value']['timeSeries']:
            code = item['variable']['variableCode'][0]['value']
            series[code] = normalize(item['values'][0]['value'], 'dateTime', 'value')
        heights = {r['time']:r['value'] for r in series.get('00065', []) if r['value'] is not None}
        navd = {r['time']:r['value'] for r in series.get('63160', []) if r['value'] is not None}
        overlaps = set(heights) & set(navd)
        nwps = {r['time']:r['value'] for r in rows if r['value'] is not None}
        matches = overlaps & set(nwps)
        if not matches or any(abs(nwps[t]-heights[t]) > .02 or
                              abs(navd[t]-heights[t]-config['nativeToDisplay']) > .02 for t in matches):
            raise ValueError('MAUL1 gauge-zero validation failed; review current USGS/NWPS datum')
    valid = [r for r in rows if r['value'] is not None]
    if not valid:
        raise ValueError('No valid water-level observations')
    latest = datetime.fromisoformat(valid[-1]['time'].replace('Z','+00:00'))
    cutoff = (latest-timedelta(hours=72)).isoformat().replace('+00:00','Z')
    return dict(id=lid, **config, units='ft', sourceUrl=url,
                fetchedAt=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
                error=None, observations=[r for r in rows if cutoff <= r['time'] <= valid[-1]['time']])

def main():
    directory = ROOT/'data/observations'
    directory.mkdir(parents=True, exist_ok=True)
    failures = []
    for lid, config in STATIONS.items():
        path = directory/f'{lid}.json'
        try:
            product = collect(lid, config)
            print(lid, len(product['observations']), product['observations'][-1])
        except Exception as exc:
            failures.append(lid)
            print(f'WARNING {lid}: {exc}')
            product = json.loads(path.read_text()) if path.exists() else dict(id=lid, **config, units='ft', observations=[])
            product['error'] = 'Observation retrieval failed; showing last successful data if available.'
            product['attemptedAt'] = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(product, separators=(',',':'))+'\n')
        temporary.replace(path)
    if len(failures) == len(STATIONS):
        raise SystemExit('All observation sources failed')

if __name__ == '__main__':
    main()
