import json

from agent import run_agent
from domain_tools import MemoryStore, execute_tool
from src.model_client import ModelResponse

SUPPLIERS = [
    {"id": 1, "name": "Green Valley Farms", "region": "California"},
    {"id": 2, "name": "Dairy Fresh Co-op", "region": "Wisconsin"},
]
NOTICES = [
    {"id": 1, "productName": "Organic baby spinach 5 oz", "noticeCode": "RN-000001", "noticeSource": "FDA recall bulletin", "affectedUnits": 120, "supplierId": 1},
    {"id": 2, "productName": "Fresh whole milk 1 gallon", "noticeCode": "RN-000002", "noticeSource": "State health department", "affectedUnits": 0, "supplierId": 2},
    {"id": 3, "productName": "Bagged baby spinach 1 lb", "noticeCode": "RN-000003", "noticeSource": "Retailer recall page", "affectedUnits": 40, "supplierId": 1},
]
store = MemoryStore(NOTICES, SUPPLIERS)


def call(name, inputs):
    return json.loads(execute_tool(name, inputs, store))


class MockModel:
    model = "mock"

    def complete(self, messages, tools=None):
        call = {"function": {"name": "search_notices", "arguments": {"query": "spinach", "limit": 2}}}
        return ModelResponse("", 0, 0, 0, {"message": {"content": "", "tool_calls": [call]}})


def test_search_valid():
    result = call("search_notices", {"query": "spinach", "limit": 5})
    assert result["ok"] and result["error"] is None
    assert [n["id"] for n in result["data"]["notices"]] == [3, 1]


def test_search_blank_query_rejected():
    result = call("search_notices", {"query": "   ", "limit": 5})
    assert result == {"ok": False, "data": None, "error": "query must be a non-empty string"}


def test_search_limit_out_of_range_rejected():
    result = call("search_notices", {"query": "milk", "limit": 500})
    assert not result["ok"] and "between 1 and 50" in result["error"]


def test_detail_valid():
    result = call("notice_detail", {"notice_id": 2})
    assert result["ok"] and result["data"]["noticeCode"] == "RN-000002"


def test_detail_unknown_id_rejected():
    result = call("notice_detail", {"notice_id": 999999})
    assert result == {"ok": False, "data": None, "error": "notice 999999 not found"}


def test_summary_valid():
    result = call("supplier_summary", {"supplier_id": 1})
    assert result["ok"] and result["data"]["noticeCount"] == 2 and result["data"]["totalAffectedUnits"] == 160


def test_summary_zero_id_rejected():
    result = call("supplier_summary", {"supplier_id": 0})
    assert result == {"ok": False, "data": None, "error": "supplier_id must be a positive integer"}


def test_unknown_tool_rejected():
    result = call("drop_table", {})
    assert not result["ok"] and result["error"].startswith("unknown tool")


def test_safety_rule_blocks_medication_search():
    result = call("search_notices", {"query": "ibuprofen tablets"})
    assert result["ok"] is False and result["data"] is None
    assert result["error"].startswith("Safety rule")


def test_agent_stops_at_max_steps():
    run = run_agent("find spinach notices", model=MockModel(), max_steps=3, store=store, log_path=None)
    assert run["stop_reason"] == "max_steps"
    assert run["steps_used"] == 3 and run["tool_calls"] == 3


TESTS = [
    test_search_valid, test_search_blank_query_rejected, test_search_limit_out_of_range_rejected,
    test_detail_valid, test_detail_unknown_id_rejected, test_summary_valid, test_summary_zero_id_rejected,
    test_unknown_tool_rejected, test_safety_rule_blocks_medication_search, test_agent_stops_at_max_steps,
]

if __name__ == "__main__":
    passed = 0
    for test in TESTS:
        try:
            test()
            passed += 1
            print(f"PASS {test.__name__}")
        except AssertionError as error:
            print(f"FAIL {test.__name__}: {error}")
    print(f"{passed}/{len(TESTS)} tests passed")
    raise SystemExit(0 if passed == len(TESTS) else 1)
