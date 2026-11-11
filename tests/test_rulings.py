import json
from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import unittest
from scripts import sync_rulings as court
from scripts.ruling_pages import ruling_card


NOW = datetime(2026,11,11,20,tzinfo=timezone.utc)
START, END = date(2026,5,15), date(2026,11,11)


def atom(court_name='Court of Appeals for the Fifth Circuit', day='2026-10-09', name='Example v. State', url='https://www.courtlistener.com/opinion/123/example/'):
    return f'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Opinion search</title><entry><title>{name}</title><link href="{url}"/><published>{day}T00:00:00-07:00</published><author><name>{court_name}</name></author><summary type="html">&lt;p&gt;A free exercise search excerpt.&lt;/p&gt;</summary></entry></feed>'''


class CourtTests(unittest.TestCase):
    def test_jurisdiction_and_url_guards(self):
        feed={'id':'fifth'}
        self.assertEqual(len(court.parse_feed(atom(),feed,START,END)[0]),1)
        for raw in [atom('Court of Appeals for the Fourth Circuit'),atom('Court of Appeals of Mississippi'),atom(url='javascript:alert(1)'),atom(url='https://evil.example/opinion/123')]:
            self.assertEqual(court.parse_feed(raw,feed,START,END)[0],[])
        self.assertEqual(court.scope('District Court, Northern District of Texas'),('Federal district','Texas'))
        self.assertEqual(court.scope('Court of Appeal of Louisiana'),('State court','Louisiana'))

    def test_dates_empty_feed_and_invalid_response(self):
        for day in ['2026-05-14','2026-11-12','invalid']:
            self.assertEqual(court.parse_feed(atom(day=day),{'id':'fifth'},START,END)[0],[])
        self.assertEqual(len(court.parse_feed(atom(day='2026-05-15'),{'id':'fifth'},START,END)[0]),1)
        self.assertEqual(court.parse_feed('<feed xmlns="http://www.w3.org/2005/Atom"/>',{'id':'fifth'},START,END),([],0))
        with self.assertRaises(ValueError):court.parse_feed('<html>Unavailable</html>',{'id':'fifth'},START,END)

    def test_snippet_is_never_promoted_to_holding(self):
        item=court.parse_feed(atom(),{'id':'fifth'},START,END)[0][0]
        self.assertEqual(item['reviewState'],'Opinion match')
        self.assertNotIn('summary',item)
        item['firstSeenAt']=NOW.isoformat()
        html=ruling_card(item)
        self.assertIn('not a summary of the holding',html)
        self.assertIn('data-review="match"',html)
        self.assertIn('hidden',html)

    def test_curated_dedup_requires_same_date_and_court(self):
        item=court.parse_feed(atom(),{'id':'fifth'},START,END)[0][0]
        record={'name':'Example versus State','matchNames':['Example v. State'],'date':item['date'],'group':'Fifth Circuit'}
        self.assertTrue(court.curated_match(item,[record]))
        self.assertFalse(court.curated_match({**item,'date':'2026-10-08'},[record]))
        self.assertFalse(court.curated_match({**item,'group':'State court'},[record]))

    def test_failure_retains_recent_data_and_freshness_not_advanced(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'dist/data').mkdir(parents=True)
            (root/'court_editorial.json').write_text(json.dumps({'checkedAt':'2026-11-11','rulings':[]}))
            item=court.parse_feed(atom(),{'id':'fifth'},START,END)[0][0]
            item['firstSeenAt']='2026-10-10T00:00:00+00:00'
            old={**item,'id':'expired','date':'2026-01-01'}
            path=root/'dist/data/rulings.json';path.write_text(json.dumps({'updatedAt':'2026-11-10T20:00:00+00:00','matches':[item,old],'sources':[]}))
            def fail(_):raise RuntimeError('offline')
            result=court.sync(root,NOW,fail)
            self.assertEqual(result['status'],'stale')
            self.assertEqual(result['updatedAt'],'2026-11-10T20:00:00+00:00')
            self.assertEqual([i['id'] for i in result['matches']],[item['id']])

    def test_empty_feed_does_not_erase_prior_discovery(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'dist/data').mkdir(parents=True)
            (root/'court_editorial.json').write_text(json.dumps({'checkedAt':'2026-11-11','rulings':[]}))
            item=court.parse_feed(atom(),{'id':'fifth'},START,END)[0][0];item['firstSeenAt']=NOW.isoformat()
            path=root/'dist/data/rulings.json';path.write_text(json.dumps({'matches':[item],'sources':[]}))
            result=court.sync(root,NOW,lambda _: '<feed xmlns="http://www.w3.org/2005/Atom"/>')
            self.assertEqual(len(result['matches']),1)
            self.assertEqual(result['status'],'ok')


if __name__=='__main__':unittest.main()
