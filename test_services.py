import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from services import add_subscription, should_run_now
from models import Search

class TestServices(unittest.TestCase):

    @patch('services.get_existing_search')
    @patch('services.create_search')
    @patch('services.create_subscription')
    def test_add_subscription_new_search(self, mock_create_sub, mock_create_search, mock_get_existing):
        # Test creating a new subscription when search doesn't exist
        mock_get_existing.return_value = None
        mock_create_search.return_value = Search(
            id=1, origin=7015400, destination=8727100, outbound_date=datetime(2026, 4, 8).date(),
            inbound_date=None, created_at=datetime.now(), last_checked=None, last_results=None
        )
        mock_create_sub.return_value = MagicMock()

        search_id, is_new = add_subscription(1, 7015400, 8727100, datetime(2026, 4, 8).date(), None)

        self.assertEqual(search_id, 1)
        self.assertTrue(is_new)
        mock_get_existing.assert_called_once()
        mock_create_search.assert_called_once()
        mock_create_sub.assert_called_once()

    @patch('services.get_existing_search')
    @patch('services.create_subscription')
    def test_add_subscription_existing_search(self, mock_create_sub, mock_get_existing):
        # Test subscribing to existing search
        existing_search = Search(
            id=2, origin=7015400, destination=8727100, outbound_date=datetime(2026, 4, 8).date(),
            inbound_date=None, created_at=datetime.now(), last_checked=None, last_results=None
        )
        mock_get_existing.return_value = existing_search
        mock_create_sub.return_value = MagicMock()

        search_id, is_new = add_subscription(1, 7015400, 8727100, datetime(2026, 4, 8).date(), None)

        self.assertEqual(search_id, 2)
        self.assertFalse(is_new)
        mock_get_existing.assert_called_once()
        mock_create_sub.assert_called_once()

    def test_should_run_now_no_last_checked(self):
        # Should run if never checked
        search = Search(
            id=1, origin=7015400, destination=8727100, outbound_date=datetime(2026, 4, 8).date(),
            inbound_date=None, created_at=datetime.now(), last_checked=None, last_results=None
        )
        self.assertTrue(should_run_now(search))

    def test_should_run_now_recently_checked(self):
        # Should not run if checked recently
        recent_time = datetime.now() - timedelta(minutes=5)
        search = Search(
            id=1, origin=7015400, destination=8727100, outbound_date=datetime(2026, 4, 8).date(),
            inbound_date=None, created_at=datetime.now(), last_checked=recent_time, last_results=None
        )
        self.assertFalse(should_run_now(search))

    def test_should_run_now_old_check(self):
        # Should run if checked more than 10 minutes ago
        old_time = datetime.now() - timedelta(minutes=15)
        search = Search(
            id=1, origin=7015400, destination=8727100, outbound_date=datetime(2026, 4, 8).date(),
            inbound_date=None, created_at=datetime.now(), last_checked=old_time, last_results=None
        )
        self.assertTrue(should_run_now(search))

if __name__ == '__main__':
    unittest.main()