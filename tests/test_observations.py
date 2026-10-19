import importlib.util
from pathlib import Path
import unittest

class Observations(unittest.TestCase):
    def test_fetcher_exists(self):
        self.assertTrue(Path('scripts/fetch_observations.py').exists(), 'observation acquisition is missing')
    def test_normalization(self):
        if not Path('scripts/fetch_observations.py').exists():
            self.skipTest('fetcher not yet implemented')
        spec=importlib.util.spec_from_file_location('obs','scripts/fetch_observations.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        rows=[{'validTime':'2026-10-19T00:00:00Z','primary':1.2},{'validTime':'bad','primary':2},{'validTime':'2026-10-19T00:15:00Z','primary':-999},{'validTime':'2026-10-19T00:30:00Z','primary':None}]
        result=m.normalize(rows,'validTime','primary')
        self.assertEqual(result,[{'time':'2026-10-19T00:00:00Z','value':1.2},{'time':'2026-10-19T00:15:00Z','value':None},{'time':'2026-10-19T00:30:00Z','value':None}])

if __name__=='__main__':unittest.main()
