from app.tools import calculate_expense_approval as calc, parse_question, tool_context


def test_over_25000_needs_dept_head_and_cfo():
    assert calc(30000)["approvers"] == ["Department head", "CFO"]
    assert calc(25000)["approvers"][0].startswith("Team lead if")  # not above 25,000, type unknown


def test_within_and_above_limit_by_type():
    assert calc(1500, "transport")["approvers"] == ["Team lead"]
    assert calc(1501, "transport")["approvers"] == ["Department head"]
    assert calc(12000, "hotel", 2)["approvers"] == ["Team lead"]      # 2 nights x 6,000
    assert calc(12001, "hotel", 2)["approvers"] == ["Department head"]
    assert any("pre-approval" in n for n in calc(5000, "hotel")["notes"])


def test_parse_question():
    assert parse_question("I claimed BDT 30,000, who approves?") == (30000.0, None, 1)
    assert parse_question("Who approves a 3 night hotel claim of 20000 taka?") == (20000.0, "hotel", 3)
    assert parse_question("What is the hotel limit outside Dhaka?") is None
    assert parse_question("How many days of annual leave?") is None
    assert parse_question("Plan costs BDT 2,500 per agent") is None  # no approval/claim wording


def test_tool_context_text():
    r, fact = tool_context("I claimed BDT 30,000, who approves?")
    assert r["approvers"] == ["Department head", "CFO"] and "CFO" in fact and "30,000" in fact
    assert tool_context("What are office hours?") is None
