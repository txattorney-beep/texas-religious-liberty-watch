import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync_tlo import parse_report, classify, guard_review

FIXTURE='''<span>90th Legislature Regular Session</span>Number of Bills: 2
<div class="row"><div><a>HB 236</a></div><div></div><div><b>Author</b>:</div><div>Lalani</div><div>Last Action:</div><div>11/09/2026 H Filed</div><div>Caption:</div><div>Relating to designating February 4 as Muslim Heritage Day.</div></div>
<div class="row"><div><a>HJR 47</a></div><div></div><div><b>Author</b>:</div><div>Vasut</div><div>Last Action:</div><div>11/09/2026 H Filed</div><div>Caption:</div><div>Proposing a constitutional amendment protecting private schools from state and local regulation.</div></div>'''

class IngestionTests(unittest.TestCase):
    def test_realistic_bill_and_resolution(self):
        bills=parse_report(FIXTURE)
        self.assertEqual([b['id'] for b in bills],['HB236','HJR47'])
        self.assertEqual(bills[0]['actionDate'],'2026-11-09')
        self.assertIn('LegSess=90R',bills[1]['historyUrl'])
    def test_reject_old_session(self):
        with self.assertRaises(ValueError):parse_report(FIXTURE.replace('90th','89th'))
    def test_reject_partial_source(self):
        with self.assertRaises(ValueError):parse_report(FIXTURE.replace('Number of Bills: 2','Number of Bills: 3'))
    def test_reject_missing_caption(self):
        with self.assertRaises(ValueError):parse_report(FIXTURE.replace('Caption:','Unknown:'))
    def test_broad_and_direct_matches(self):
        self.assertIn('Faith communities',classify('Designating Muslim Heritage Day.'))
        self.assertIn('Schools & education',classify('Repealing the education savings account program.'))
        self.assertEqual(classify('Relating to transportation project appropriations.'),[])
    def review(self):
        return dict(reviewState='Text reviewed',summary='Reviewed old text',relevance='An assessment',reviewedTextUrl='v1',textUrl='v1',reviewedTextHash='old',textHash='old')
    def test_changed_version_invalidates_summary(self):
        b=self.review();b['textUrl']='v2';guard_review(b)
        self.assertIsNone(b['summary']);self.assertIsNone(b['relevance'])
    def test_same_url_changed_content_invalidates(self):
        b=self.review();b['textHash']='new';guard_review(b)
        self.assertNotEqual(b['reviewState'],'Text reviewed')
    def test_old_editorial_cannot_restore_review_on_next_run(self):
        for _ in range(2):
            b=self.review();b['textHash']='new';guard_review(b)
            self.assertIsNone(b['summary'])
    def test_same_version_retains_review(self):
        b=self.review();guard_review(b);self.assertEqual(b['reviewState'],'Text reviewed')

if __name__=='__main__':unittest.main()
