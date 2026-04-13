from docwright.codex.samples.attention_smoke import run_attention_fixture_smoke


def test_attention_fixture_smoke_uses_canonical_entry_path_and_tools() -> None:
    payload = run_attention_fixture_smoke()

    assert payload["fixture_path"].endswith("attention_is_all_you_need.document_ir.json")
    assert payload["contract"]["metadata"]["document_id"] == "attention_is_all_you_need.pdf"
    assert payload["contract"]["metadata"]["capability"] == "manual_task"
    assert [result["name"] for result in payload["tool_results"]] == [
        "get_node",
        "get_context",
        "search_text",
        "jump_to_node",
    ]
    assert payload["tool_results"][0]["output"]["node"]["node_id"] == "para_0001"
    assert payload["tool_results"][1]["output"]["focus_node_id"] == "para_0001"
    assert payload["tool_results"][2]["output"]["query"] == "attention"
    assert payload["tool_results"][3]["output"]["node"]["node_id"] == "sec_0001"
    assert payload["usage"]["step_exports"] == 1
    assert payload["usage"]["tool_calls_completed"] == 4
