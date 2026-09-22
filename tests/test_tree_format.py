from adventureworks_agent.tree_format import render_tree


def test_render_tree_basic_two_node_plan():
    header = {"stmt_cost": 1.23, "dop": 1, "optm_level": "FULL", "plan_hash": "0xABCD"}
    rows = [
        {
            "node_id": 1, "depth": 0, "op_code": "NL", "mode": None,
            "table_alias": None, "access_kind": None, "est": 100.0, "act": None,
            "cost_pct": 80, "warning": None, "predicate": None, "prunable": False,
        },
        {
            "node_id": 2, "depth": 1, "op_code": "IS", "mode": None,
            "table_alias": "Sales.SalesOrderHeader", "access_kind": "seek", "est": 100.0, "act": None,
            "cost_pct": 20, "warning": None, "predicate": "SalesOrderID = 43659", "prunable": False,
        },
    ]

    text = render_tree(header, rows)

    assert text.startswith("#hdr cost=1.23 dop=1 optm=FULL hash=0xABCD\n")
    assert "#t @1=Sales.SalesOrderHeader" in text
    assert "NL est=100 cost=80%" in text
    assert " @1.seek est=100 cost=20% ?SalesOrderID = 43659" in text
    assert text.rstrip().endswith("#pruned=0")


def test_render_tree_omits_cost_under_1_percent():
    header = {"stmt_cost": 1.0, "dop": 1, "optm_level": "FULL", "plan_hash": "0x1"}
    rows = [
        {
            "node_id": 1, "depth": 0, "op_code": "CS", "mode": None, "table_alias": None,
            "access_kind": None, "est": 1.0, "act": None, "cost_pct": 0, "warning": None,
            "predicate": None, "prunable": False,
        }
    ]

    text = render_tree(header, rows)

    assert "cost=" not in text.split("\n")[1]


def test_render_tree_counts_pruned_rows():
    header = {"stmt_cost": 1.0, "dop": 1, "optm_level": "FULL", "plan_hash": "0x1"}
    rows = [
        {"node_id": 1, "depth": 0, "op_code": "NL", "mode": None, "table_alias": None,
         "access_kind": None, "est": 1.0, "act": None, "cost_pct": 90, "warning": None,
         "predicate": None, "prunable": False},
        {"node_id": 2, "depth": 1, "op_code": "CMP", "mode": None, "table_alias": None,
         "access_kind": None, "est": 1.0, "act": None, "cost_pct": 0, "warning": None,
         "predicate": None, "prunable": True},
    ]

    text = render_tree(header, rows)

    assert "#pruned=1" in text
    assert "CMP" not in text.split("#pruned")[0].split("\n")[-2]


def test_render_tree_shows_act_on_all_nodes_when_any_has_actuals():
    header = {"stmt_cost": 1.0, "dop": 1, "optm_level": "FULL", "plan_hash": "0x1"}
    rows = [
        {"node_id": 1, "depth": 0, "op_code": "NL", "mode": None, "table_alias": None,
         "access_kind": None, "est": 10.0, "act": 12.0, "cost_pct": 100, "warning": None,
         "predicate": None, "prunable": False},
    ]

    text = render_tree(header, rows)

    assert "est=10/act=12" in text
