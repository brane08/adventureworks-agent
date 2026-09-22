import pytest
from adventureworks_agent.keys import DmvKey, QsKey, encode_dmv_key, encode_qs_key, key_source, parse_key


def test_encode_dmv_key():
    assert encode_dmv_key("0x0500070068C1", 0, 120) == "dmv:0x0500070068C1:0:120"


def test_encode_qs_key():
    assert encode_qs_key(42, 7) == "qs:42:7"


def test_parse_dmv_key_roundtrip():
    key = encode_dmv_key("0x0500070068C1", 0, 120)
    assert parse_key(key) == DmvKey(plan_handle="0x0500070068C1", start_offset=0, end_offset=120)


def test_parse_qs_key_roundtrip():
    key = encode_qs_key(42, 7)
    assert parse_key(key) == QsKey(query_id=42, plan_id=7)


def test_key_source():
    assert key_source(encode_dmv_key("0x01", 0, 10)) == "DMV"
    assert key_source(encode_qs_key(1, 1)) == "QS"


@pytest.mark.parametrize(
    "bad_key",
    [
        "dmv:not-hex:0:10",
        "dmv:0x01:abc:10",
        "qs:not-int:1",
        "qs:1:not-int",
        "bogus:1:2",
        "dmv:0x01:0",
    ],
)
def test_parse_key_rejects_malformed(bad_key):
    with pytest.raises(ValueError):
        parse_key(bad_key)
