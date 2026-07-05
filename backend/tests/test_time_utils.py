import unittest
from datetime import date, datetime
from unittest.mock import patch


class TimeUtilsTests(unittest.TestCase):
    def test_local_today_uses_shanghai_timezone(self):
        from time_utils import LOCAL_TIMEZONE, local_today

        with patch("time_utils.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2026, 7, 6, 0, 30)

            self.assertEqual(local_today(), date(2026, 7, 6))
            mocked_datetime.now.assert_called_once_with(LOCAL_TIMEZONE)


if __name__ == "__main__":
    unittest.main()
