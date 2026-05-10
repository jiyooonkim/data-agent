import unittest

from service.router_service import route_question


class RouterServiceTest(unittest.TestCase):
    def test_route_question_prefers_document_for_doc_keywords(self):
        self.assertEqual(route_question("정책 문서 기준으로 절차 설명해줘"), "document")

    def test_route_question_prefers_structured_for_metric_keywords(self):
        self.assertEqual(route_question("최근 7일 채널별 매출 합계 보여줘"), "structured")

    def test_route_question_returns_hybrid_when_both_signals_exist(self):
        self.assertEqual(route_question("정책 문서 기준으로 최근 7일 매출을 설명해줘"), "hybrid")


if __name__ == "__main__":
    unittest.main()
