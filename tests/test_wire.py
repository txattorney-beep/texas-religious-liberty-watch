import unittest
from pathlib import Path
from html.parser import HTMLParser
from scripts.wire_pages import section, wire_content

class WireTests(unittest.TestCase):
    def test_sections_and_no_duplicate_lead(self):
        items=[dict(title=t,publisher='Source',publishedAt='2026-11-17T12:00:00+00:00',scopes=s,url='https://example.com/'+str(i)) for i,(t,s) in enumerate([('Texas school dispute',['Texas']),('Fifth Circuit ruling',['Texas']),('Federal national policy',['National'])])]
        data={'items':items,'updatedAt':'2026-11-17T12:00:00+00:00','status':'ok','sources':[]}
        self.assertEqual([section(x) for x in items],['Texas','Fifth Circuit','National'])
        page=wire_content(data)
        for x in items:self.assertEqual(page.count('>'+x['title']+'</a>'),1)
        self.assertIn('wire-lead',page)
        self.assertNotIn('guest-voices',page)
    def test_home_has_single_ids_and_preserved_tracker(self):
        class IDs(HTMLParser):
            def __init__(self):super().__init__();self.ids=[]
            def handle_starttag(self,t,attrs):
                for k,v in attrs:
                    if k=='id':self.ids.append(v)
        root=Path(__file__).resolve().parents[1]
        page=(root/'dist/index.html').read_text()
        p=IDs();p.feed(page)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        for i in ['wire-front','legislative-desk','tracker-content','bill-dialog','bill-list','search','news-search']:
            self.assertIn(i,p.ids)
        self.assertIn('app.js',page)
        self.assertIn('frontpage.js',page)
        self.assertIn('href="/#tracker"',page)
