"""Presentation/accounting checks, not certification of the underlying models."""
from pathlib import Path
import json, re, unittest
import numpy as np
import pandas as pd
import nbformat
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'
def summary(rel):return pd.read_csv(D/rel/'summary.csv',index_col=0).economic
class SnapshotChecks(unittest.TestCase):
    def test_enermap_release_and_population(self):
        record=json.loads((D/'enermap/completion.json').read_text())
        self.assertTrue(record['completed'])
        self.assertTrue(record['completed_utc'].startswith('2026-09-23'))
        self.assertFalse(record['calibration'])
        c=pd.read_csv(D/'enermap/cluster_summary.csv')
        self.assertEqual(c.dwelling_count.sum(),57300)
        self.assertEqual(len(c),2386)
        self.assertEqual(c.electricity_zone_id.nunique(),320)
    def test_hourly_annual_reconciliation(self):
        a=pd.read_csv(D/'enermap/cluster_annual_totals.csv')
        h=pd.read_csv(D/'enermap/hourly_totals.csv')
        self.assertTrue(h.groupby('package_id').size().eq(8760).all())
        self.assertFalse(h.duplicated(['package_id','timestamp_utc']).any())
        av=a.groupby('package_id')[['space_heat_kWh','hot_water_kWh','non_heating_elec_kWh']].sum()
        hv=h.groupby('package_id')[['space_heat_kw','hot_water_heat_kw','non_heating_electricity_kw']].sum()
        np.testing.assert_allclose(hv,av,rtol=1e-5)
    def test_adoption_and_network_population(self):
        for case,pop,zones in [('residential/westborough',2974,33),('dh/C',2534,15)]:
            s=summary(case);u=pd.read_csv(D/case/'uptake.csv');z=pd.read_csv(D/case/'zone_table.csv')
            self.assertAlmostEqual(s.dwellings,pop,places=3)
            self.assertAlmostEqual(u.dwellings.sum(),pop,places=2)
            self.assertEqual(len(z),zones)
    def test_dh_pipe_cost_is_included(self):
        for case in ['A','B','C']:
            s=summary('dh/'+case)
            self.assertAlmostEqual(s.objective_mgbp,s.objective_excl_committed_dh_mgbp+s.committed_dh_pipe_cost_mgbp,places=8)
        self.assertGreater(summary('dh/B').objective_mgbp,summary('dh/A').objective_mgbp)
        self.assertLess(summary('dh/B').emissions_kt,summary('dh/A').emissions_kt)
    def test_known_replay_failure_is_not_hidden(self):
        r=pd.read_csv(D/'dh/C/replay_report.csv',index_col=0)
        self.assertGreater(r.loc['unmet_elec_mwh','replay'],.001)
        self.assertIn('not a passed feasibility test',(ROOT/'docs/scope.md').read_text())
        r=pd.read_csv(D/'residential/westborough/replay_report.csv',index_col=0)
        self.assertEqual(r.loc['zones','replay'],3)
    def test_guildford_is_not_jointly_feasible(self):
        h=pd.read_csv(D/'residential/guildford/borough_import_hourly.csv')
        self.assertGreater(h.borough_import_mw.max(),40)
        self.assertEqual(int((h.borough_import_mw>40).sum()),307)
    def test_executed_notebooks(self):
        paths=list((ROOT/'notebooks').glob('*.ipynb'));self.assertEqual(len(paths),3)
        for p in paths:
            nb=nbformat.read(p,as_version=4); nbformat.validate(nb)
            codes=[c for c in nb.cells if c.cell_type=='code']
            self.assertTrue(all(c.execution_count is not None for c in codes),p.name)
            outputs=[o for c in codes for o in c.outputs]
            self.assertFalse(any(o.output_type=='error' for o in outputs),p.name)
            self.assertGreaterEqual(sum('image/png' in o.get('data',{}) for o in outputs),4,p.name)
            self.assertTrue((ROOT/'reports'/f'{p.stem}.html').exists())
    def test_portable_no_raw_building_identifiers(self):
        for p in (ROOT/'data').rglob('*'):
            if not p.is_file():continue
            content=p.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'[A-Za-z]:[/\\]Users[/\\]',content),str(p))
            self.assertIsNone(re.search(r'osgb\d{10,}',content),str(p))
            self.assertNotIn('UPRN',content,str(p))
    def test_source_manifest_complete(self):
        manifest=json.loads((ROOT/'docs/source_manifest.json').read_text())
        self.assertEqual(len(manifest['sources']),53)
        for item in manifest['sources']:
            self.assertRegex(item['sha256'],r'^[0-9a-f]{64}$')
            self.assertTrue((ROOT/item['output']).exists())
if __name__=='__main__':unittest.main()
