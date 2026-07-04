import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from routers import ai_router
from schemas import AIGeneratePlanRequest


class FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def scalar(self):
        return 0


class FakeDb:
    def query(self, *args, **kwargs):
        return FakeQuery()


class HighCountQuery:
    def filter(self, *args, **kwargs):
        return self

    def scalar(self):
        return 999


class HighCountDb:
    def query(self, *args, **kwargs):
        return HighCountQuery()


class AiGeneratePlanTests(unittest.IsolatedAsyncioTestCase):
    def test_ai_rate_limit_is_disabled_for_mvp_testing(self):
        user = SimpleNamespace(id=1)

        ai_router.check_ai_rate_limit(user, HighCountDb())

    async def test_generate_plan_accepts_canonical_tasks_fields(self):
        async def fake_call_deepseek(prompt):
            return {
                "summary": "one day plan",
                "tasks": [
                    {
                        "name": "背单词",
                        "task_date": date.today().isoformat(),
                        "subject": "英语",
                        "suggested_duration": 20,
                        "difficulty": "medium",
                        "knowledge_tags": ["vocabulary"],
                    }
                ],
            }

        req = AIGeneratePlanRequest(content="每天背单词", mode="daily")
        user = SimpleNamespace(id=1)

        with patch.object(ai_router, "call_deepseek", fake_call_deepseek):
            response = await ai_router.generate_plan(req, user=user, db=FakeDb())

        self.assertEqual(response.total_days, 1)
        self.assertEqual(len(response.tasks), 1)
        self.assertEqual(response.tasks[0].name, "背单词")
        self.assertEqual(response.tasks[0].task_date, date.today())
        self.assertEqual(response.tasks[0].source, "ai")


if __name__ == "__main__":
    unittest.main()
