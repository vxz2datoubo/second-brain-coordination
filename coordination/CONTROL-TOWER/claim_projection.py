from __future__ import annotations

from pathlib import Path
from typing import Any

from control_tower import PROJECTION, load_yaml
from lane_claims import CLAIMS_FILE, validate_claims

CLAIM_PROJECTION_START = "<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->"
CLAIM_PROJECTION_END = "<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->"


def _claims_by_lane(claims_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["lane_id"]): item
        for item in claims_doc.get("claims", []) or []
        if isinstance(item, dict) and item.get("lane_id")
    }


def _surface(paths: list[Any]) -> str:
    if not paths:
        return "NONE"
    if len(paths) == 1:
        return f"`{paths[0]}`"
    return f"{len(paths)} paths"


def render_claim_projection_block(repo_root: Path) -> str:
    root = repo_root.resolve()
    claims_doc = load_yaml(root / CLAIMS_FILE)
    claims = _claims_by_lane(claims_doc)
    report = validate_claims(root)
    lines = [
        CLAIM_PROJECTION_START,
        "## 自动同步作业领空（机器生成区）",
        "",
        f"- Work claims: `{claims_doc.get('claims_id')}`",
        f"- Claim structural check: **{report['claim_structural_check']}**",
        f"- Proposal-only release candidate: **{report['proposal_only_candidate']}**",
        "",
        "| Lane | claim state | agent | resource | write surface | route binding |",
        "|---|---|---|---|---|---|",
    ]
    for lane_id in sorted(claims):
        claim = claims[lane_id]
        binding = claim.get("route_binding") or {}
        binding_text = "NONE"
        if binding:
            binding_text = f"epoch {binding.get('route_epoch')} · #{binding.get('issue')}/#{binding.get('pr')}"
            slot_id = claim.get("worker_slot_id") or binding.get("worker_slot_id")
            if slot_id:
                binding_text += f" · slot `{slot_id}`"
        lines.append(
            f"| `{lane_id}` | `{claim.get('claim_state')}` | `{claim.get('execution_agent') or 'NONE'}` | "
            f"`{claim.get('resource_class')}` | {_surface(list(claim.get('write_paths', []) or []))} | {binding_text} |"
        )
    lines.extend(
        [
            "",
            "### Pairwise current-claim collision scan",
            "",
            "| Pair | level | reason |",
            "|---|---|---|",
        ]
    )
    for item in report["pairwise"]:
        pair = " ↔ ".join(item["pair"])
        lines.append(f"| `{pair}` | **{item['level']}** | `{item['reason']}` |")
    lines.extend(["", CLAIM_PROJECTION_END])
    return "\n".join(lines)


def claim_projection_matches(repo_root: Path) -> bool:
    root = repo_root.resolve()
    path = root / PROJECTION
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if CLAIM_PROJECTION_START not in text or CLAIM_PROJECTION_END not in text:
        return False
    start = text.index(CLAIM_PROJECTION_START)
    end = text.index(CLAIM_PROJECTION_END, start) + len(CLAIM_PROJECTION_END)
    return text[start:end] == render_claim_projection_block(root)


def replace_claim_projection_block(text: str, block: str) -> str:
    if CLAIM_PROJECTION_START in text and CLAIM_PROJECTION_END in text:
        start = text.index(CLAIM_PROJECTION_START)
        end = text.index(CLAIM_PROJECTION_END, start) + len(CLAIM_PROJECTION_END)
        return text[:start] + block + text[end:]
    anchor = "<!-- CONTROL_TOWER_AUTOGEN:END -->"
    if anchor in text:
        pos = text.index(anchor) + len(anchor)
        return text[:pos] + "\n\n" + block + text[pos:]
    return block + "\n\n" + text
