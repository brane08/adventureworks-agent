import re
from typing import Literal, NamedTuple, Union

_HEX_RE = re.compile(r"^0x[0-9A-Fa-f]+$")


class DmvKey(NamedTuple):
    plan_handle: str
    start_offset: int
    end_offset: int


class QsKey(NamedTuple):
    query_id: int
    plan_id: int


Key = Union[DmvKey, QsKey]


def encode_dmv_key(plan_handle: str, start_offset: int, end_offset: int) -> str:
    return f"dmv:{plan_handle}:{start_offset}:{end_offset}"


def encode_qs_key(query_id: int, plan_id: int) -> str:
    return f"qs:{query_id}:{plan_id}"


def parse_key(key: str) -> Key:
    parts = key.split(":")
    if parts[0] == "dmv" and len(parts) == 4:
        _, plan_handle, start_offset, end_offset = parts
        if not _HEX_RE.match(plan_handle):
            raise ValueError(f"Invalid plan_handle in key: {key!r}")
        try:
            return DmvKey(plan_handle=plan_handle, start_offset=int(start_offset), end_offset=int(end_offset))
        except ValueError as exc:
            raise ValueError(f"Invalid offsets in key: {key!r}") from exc
    if parts[0] == "qs" and len(parts) == 3:
        _, query_id, plan_id = parts
        try:
            return QsKey(query_id=int(query_id), plan_id=int(plan_id))
        except ValueError as exc:
            raise ValueError(f"Invalid ids in key: {key!r}") from exc
    raise ValueError(f"Unrecognized key format: {key!r}")


def key_source(key: str) -> Literal["DMV", "QS"]:
    parsed = parse_key(key)
    return "DMV" if isinstance(parsed, DmvKey) else "QS"
