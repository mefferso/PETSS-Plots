import importlib.util
from pathlib import Path
import unittest
import json
from unittest.mock import patch

class Observations(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('obs','scripts/fetch_observations.py')
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)

    def test_station_thresholds_and_references(self):
        for lid, threshold, datum in [('BSGL1',2.5,'NAVD88'),('BYGL1',1.2,'MSL'),('MAUL1',4.0,'NAVD88')]:
            config=self.m.STATIONS[lid]
            self.assertEqual((config['threshold'],config['thresholdDatum']),(threshold,datum))
        ref=json.loads(Path('docs/observation-references/bygl1-datums.json').read_text())
        elevations={d['name']:d['value'] for d in ref['datums']}
        self.assertAlmostEqual(elevations['MSL']-elevations['NAVD88'],self.m.STATIONS['BYGL1']['offsets']['NAVD88'])
        pairs=json.loads(Path('docs/observation-references/maul1-usgs-paired.json').read_text())
        for a,b in zip(pairs[0]['observations'],pairs[1]['observations']):
            self.assertEqual(a['dateTime'],b['dateTime'])
            self.assertAlmostEqual(float(b['value'])-float(a['value']),self.m.STATIONS['MAUL1']['nativeToDisplay'])

    def test_nwps_window_preserves_raw_values_and_nulls(self):
        raw={'observed':{'primaryUnits':'ft','primaryName':'Stage','data':[
            {'validTime':'2026-10-15T00:00:00Z','primary':9},
            {'validTime':'2026-10-16T00:00:00Z','primary':1.0},
            {'validTime':'2026-10-18T00:00:00Z','primary':-999},
            {'validTime':'2026-10-19T00:00:00Z','primary':2.0}]}}
        with patch.object(self.m,'get_json',return_value=raw):
            product=self.m.collect('BSGL1',self.m.STATIONS['BSGL1'])
        self.assertEqual([r['value'] for r in product['observations']],[1.0,None,2.0])
        self.assertEqual(product['units'],'ft')
        raw['observed']['primaryUnits']='m'
        with patch.object(self.m,'get_json',return_value=raw),self.assertRaises(ValueError):
            self.m.collect('BSGL1',self.m.STATIONS['BSGL1'])

    def test_maul1_refuses_unverified_gauge_zero(self):
        raw={'observed':{'primaryUnits':'ft','primaryName':'Stage','data':[{'validTime':'2026-10-19T00:00:00Z','primary':2.81}]}}
        def item(code,value):
            return {'variable':{'variableCode':[{'value':code}]},'values':[{'value':[{'dateTime':'2026-10-19T00:00:00Z','value':str(value)}]}]}
        paired={'value':{'timeSeries':[item('00065',2.81),item('63160',1.91)]}}
        with patch.object(self.m,'get_json',side_effect=[raw,paired]),self.assertRaisesRegex(ValueError,'gauge-zero validation failed'):
            self.m.collect('MAUL1',self.m.STATIONS['MAUL1'])
        paired['value']['timeSeries'][1]=item('63160',1.43)
        with patch.object(self.m,'get_json',side_effect=[raw,paired]):
            product=self.m.collect('MAUL1',self.m.STATIONS['MAUL1'])
        self.assertEqual(product['observations'][0]['value'],2.81)
        self.assertAlmostEqual(product['observations'][0]['value']+product['nativeToDisplay'],1.43)

    def test_source_retry_and_exhaustion(self):
        with patch('urllib.request.urlopen',side_effect=OSError('outage')) as request,patch('time.sleep'):
            with self.assertRaises(OSError):self.m.get_json('https://example.invalid')
            self.assertEqual(request.call_count,3)
    def test_normalization(self):
        if not Path('scripts/fetch_observations.py').exists():
            self.skipTest('fetcher not yet implemented')
        spec=importlib.util.spec_from_file_location('obs','scripts/fetch_observations.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        rows=[{'validTime':'2026-10-19T00:00:00Z','primary':1.2},{'validTime':'bad','primary':2},{'validTime':'2026-10-19T00:15:00Z','primary':-999},{'validTime':'2026-10-19T00:30:00Z','primary':None}]
        result=m.normalize(rows,'validTime','primary')
        self.assertEqual(result,[{'time':'2026-10-19T00:00:00Z','value':1.2},{'time':'2026-10-19T00:15:00Z','value':None},{'time':'2026-10-19T00:30:00Z','value':None}])

if __name__=='__main__':unittest.main()
