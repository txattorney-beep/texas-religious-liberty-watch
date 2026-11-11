from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from scripts import sync_hearings as hearings

NOW=datetime(2026,11,11,22,0,tzinfo=timezone.utc)
URL='https://capitol.texas.gov/tlodocs/90R/schedules/html/C4502027030913001.HTM'
def notice(body='HB 236 Public benefit proposal.', time='1:00 PM or upon adjournment, Tuesday, March 9, 2027', place='E2.010'):
 return '<html><body>HOUSE OF REPRESENTATIVES NOTICE OF PUBLIC HEARING COMMITTEE: State Affairs TIME &amp; DATE: '+time+' PLACE: '+place+' CHAIR: Rep. Example '+body+'</body></html>'
def rss(url=URL):
 return '<rss><channel><title>Texas Legislature - Upcoming House Committee Meetings</title><item><guid>'+url+'</guid></item></channel></rss>'

class HearingTests(unittest.TestCase):
 def test_discovery_rejects_other_sessions_and_hosts(self):
  source={'kind':'rss'}
  self.assertEqual(hearings.discover(rss(),source),[URL])
  self.assertEqual(hearings.discover(rss(URL.replace('90R','89R')),source),[])
  self.assertIsNone(hearings.notice_url(URL.replace('capitol.texas.gov','example.com')))
  self.assertEqual(hearings.discover('<rss><channel><title>Upcoming House Committee Meetings</title><item><title>No committee meetings scheduled.</title></item></channel></rss>',source),[])
 def test_empty_feeds_differ_from_invalid_responses(self):
  with self.assertRaises(ValueError):hearings.discover('<html>maintenance</html>',{'kind':'rss'})
  with self.assertRaises(ValueError):hearings.discover('<html>maintenance</html>',{'kind':'html'})
 def test_conditional_time_and_exact_bill_match(self):
  event=hearings.parse_notice(notice('HB 236 and HB 2360'),URL,NOW)
  self.assertEqual(event['date'],'2027-03-09')
  self.assertIn('or upon adjournment',event['timeAndDate'])
  self.assertEqual(event['billIds'],['HB236','HB2360'])
  self.assertEqual(event['location'],'E2.010')
 def test_cancellation_and_removed_bills_are_not_scheduled(self):
  event=hearings.parse_notice(notice('** MEETING CANCELED ** Bills deleted after last posting: HB 236 ** See Committee Coordinator'),URL,NOW)
  self.assertEqual(event['status'],'Canceled');self.assertEqual(event['billIds'],[]);self.assertEqual(event['removedBillIds'],['HB236'])
 def test_revision_retains_removed_bill_and_change_history(self):
  old=hearings.merge_notice(hearings.parse_notice(notice(),URL,NOW),None,{'HB236'},NOW)
  updated=hearings.parse_notice(notice('HB 100','2:00 PM, Tuesday, March 9, 2027','E2.012'),URL,NOW)
  merged=hearings.merge_notice(updated,old,{'HB236'},NOW)
  self.assertEqual(merged['relatedBills'],['HB236']);self.assertEqual(merged['removedBillIds'],['HB236'])
  self.assertIn('Location',merged['changes'][-1]['detail']);self.assertIn('Tracked bills removed',merged['changes'][-1]['detail'])
 def test_fetch_failure_retains_last_verified_notice(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'dist/data').mkdir(parents=True)
   (root/'dist/data/bills.json').write_text(json.dumps({'session':'90R','bills':[{'id':'HB236'}]}))
   def initial(url):
    if url==URL:return notice()
    if '/RSS/' in url:return rss()
    return '<html>Committee Meetings <a href="'+URL+'">Notice</a></html>'
   before=hearings.sync(root,NOW,initial)
   def broken(url):raise RuntimeError('Unavailable')
   after=hearings.sync(root,NOW,broken)
   self.assertEqual(after['status'],'stale');self.assertEqual(after['updatedAt'],before['updatedAt'])
   self.assertEqual(after['events'][0]['timeAndDate'],before['events'][0]['timeAndDate'])
   self.assertIn('retrievalError',after['events'][0])
 def test_disappearance_does_not_create_cancellation(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'dist/data').mkdir(parents=True)
   (root/'dist/data/bills.json').write_text(json.dumps({'session':'90R','bills':[{'id':'HB236'}]}))
   event=hearings.merge_notice(hearings.parse_notice(notice(),URL,NOW),None,{'HB236'},NOW)
   (root/'dist/data/hearings.json').write_text(json.dumps({'session':'90R','events':[event]}))
   def get(url):
    if url==URL:return notice()
    if '/RSS/' in url:return rss('https://capitol.texas.gov/Committees/MeetingsUpcoming.aspx')
    return '<html>Committee Meetings No meetings have been scheduled.</html>'
   after=hearings.sync(root,NOW,get)
   self.assertEqual(after['events'][0]['status'],'Scheduled');self.assertFalse(after['events'][0]['listedInUpcoming'])

if __name__=='__main__':unittest.main()
