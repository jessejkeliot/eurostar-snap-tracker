import sys
import os
from datetime import date

# Add src to sys.path
sys.path.append(os.getcwd())

from src.core.models import Search
from src.workers.scheduler import check_for_search_updates
from unittest.mock import MagicMock, patch

def test_check_for_search_updates():
    # Create a mock Search object (without inbound_date)
    search = Search(
        id=1,
        origin=7015400,
        destination=8727100,
        outbound_date=date(2026, 5, 1),
        created_at=date(2026, 4, 1),
        last_checked=None,
        last_results=None
    )
    
    print("Testing check_for_search_updates with Search object...")
    
    # Mock run_search to avoid actual web requests
    with patch('src.workers.scheduler.run_search') as mock_run_search:
        mock_run_search.return_value = ("http://test.url", [])
        
        try:
            url, results, results_string, has_changed = check_for_search_updates(search)
            print("✅ Success! check_for_search_updates ran without AttributeError.")
            print(f"URL: {url}")
            print(f"Results: {results}")
        except AttributeError as e:
            print(f"❌ Failed! Caught AttributeError: {e}")
        except Exception as e:
            print(f"❌ Failed! Caught unexpected exception: {e}")

if __name__ == "__main__":
    test_check_for_search_updates()
