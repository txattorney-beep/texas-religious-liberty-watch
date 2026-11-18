import datetime as dt
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('health',Path(__file__).resolve().parents[1]/'scripts/refresh_health.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
class RefreshHealth(unittest.TestCase):
 def test_winter(self):
  self.assertEqual(h.latest_window(dt.datetime.fromisoformat('2026-11-18T14:00:00+00:00')).hour,7)
 def test_summer(self):
  self.assertEqual(h.latest_window(dt.datetime.fromisoformat('2027-04-18T13:00:00+00:00')).utcoffset(),dt.timedelta(hours=-5))
 def test_missing(self):self.assertTrue(h.due({},dt.datetime.now(dt.timezone.utc)))
 def test_catchup(self):
  now=dt.datetime.fromisoformat('2026-11-18T14:00:00+00:00');data={'feeds':{n:{'status':'ok','lastSuccessAt':now.isoformat()} for n in h.FEEDS}}
  self.assertFalse(h.due(data,now));data['feeds']['news']['status']='partial';self.assertTrue(h.due(data,now))
