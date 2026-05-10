import unittest

from service.qa_service import normalize_question, validate_sql


class QaServiceTest(unittest.TestCase):
    def test_normalize_question_maps_channel_names(self):
        self.assertEqual(normalize_question("구글 채널 매출"), "google 채널 매출")
        self.assertEqual(normalize_question("Facebook revenue"), "facebook revenue")

    def test_validate_sql_accepts_select_from_dw_table(self):
        sql = "select channel, sum(revenue) from dw.meta_ads_daily group by channel"

        self.assertEqual(validate_sql(sql), sql)

    def test_validate_sql_blocks_non_select(self):
        with self.assertRaises(ValueError) as exc:
            validate_sql("delete from dw.meta_ads_daily")

        self.assertIn("Only SELECT queries are allowed.", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
