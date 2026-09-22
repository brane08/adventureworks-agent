def render_tree(header: dict, rows: list[dict]) -> str:
    lines = [f"#hdr cost={header['stmt_cost']} dop={header['dop']} optm={header['optm_level']} hash={header['plan_hash']}"]

    aliases: dict[str, int] = {}
    for row in rows:
        alias = row.get("table_alias")
        if alias and alias not in aliases:
            aliases[alias] = len(aliases) + 1
            lines.append(f"#t @{aliases[alias]}={alias}")

    any_act = any(row.get("act") is not None for row in rows)
    pruned_count = sum(1 for row in rows if row["prunable"])

    for row in rows:
        if row["prunable"]:
            continue
        indent = "  " * row["depth"]
        parts = [row["op_code"]]
        if row.get("mode"):
            parts[0] += f"[{row['mode']}]"
        if row.get("table_alias"):
            alias_ref = f"@{aliases[row['table_alias']]}"
            if row.get("access_kind"):
                alias_ref += f".{row['access_kind']}"
            parts.append(alias_ref)

        est = row["est"]
        est_str = f"est={int(est) if est == int(est) else est}"
        if any_act:
            act = row.get("act")
            act_str = f"act={int(act) if act == int(act) else act}" if act is not None else "act=?"
            est_str = f"{est_str}/{act_str}"
        parts.append(est_str)

        if row.get("cost_pct") and row["cost_pct"] >= 1:
            parts.append(f"cost={row['cost_pct']}%")
        if row.get("warning"):
            parts.append(f"!{row['warning']}")
        if row.get("predicate"):
            parts.append(f"?{row['predicate'][:60]}")

        lines.append(indent + " ".join(parts))

    lines.append(f"#pruned={pruned_count}")
    return "\n".join(lines)
