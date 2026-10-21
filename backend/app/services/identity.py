"""Applies persisted identity decisions to the engine's entity resolution on every build.

* `same_as` links merge the `from` entity into the `to` entity (the `to` key stays stable).
* `implementation_of` / `related_to` links are attached to both entities as `related_systems`.
* `entity_curation` rows override display fields (official docs URL, organization) with evidence.
* Field-level verification coverage is computed from `attribute_evidence`."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AttributeEvidence, EntityCuration, IdentityLink

# Attribute groups that must ALL carry official evidence before a system may be called fully "verified".
REQUIRED_ATTRIBUTES: dict[str, list[str]] = {
    "identity": ["identity.official_docs", "identity.repository"],
    "technical": ["technical.frameworks", "technical.packages"],
    "foundations": ["foundations.color", "foundations.typography", "foundations.spacing"],
    "tokens": ["tokens.documented"],
    "theming": ["theming.documented"],
    "components": ["components.inventory"],
    "accessibility": ["accessibility.documented"],
    "governance": ["governance.contribution", "governance.releases"],
    "license": ["license"],
}
ALL_REQUIRED = [a for v in REQUIRED_ATTRIBUTES.values() for a in v]


def _merge(into: dict[str, Any], other: dict[str, Any], evidence: list) -> None:
    for k in ("sources", "source_record_ids", "evidence_urls"):
        into[k] = sorted(set(into.get(k) or []) | set(other.get(k) or []))
    into["source_count"] = len(into["sources"])
    for k in ("documentation_url", "repository_url", "storybook_url", "design_resource_url", "styling_strategy", "token_architecture",
              "accessibility_documentation", "governance_documentation", "ai_readiness", "organization"):
        if not into.get(k) and other.get(k):
            into[k] = other[k]
    fe = into.setdefault("framework_evidence", {})
    for f, srcs in (other.get("framework_evidence") or {}).items():
        fe[f] = sorted(set(fe.get(f, [])) | set(srcs))
    into["supported_frameworks"] = sorted(fe)
    into["aliases"] = sorted(set(into.get("aliases") or [into["name"]]) | set(other.get("aliases") or [other["name"]]) - {into["name"]} | {into["name"]})
    rel = into.setdefault("related_urls", [])
    for u in [other.get("documentation_url"), other.get("storybook_url"), other.get("repository_url")] + list(other.get("related_urls") or []):
        if u and u not in rel:
            rel.append(u)
    into.setdefault("merged_from", []).append({"system_id": other["system_id"], "name": other["name"], "evidence": evidence[:5]})
    if other.get("deprecated_flag"):
        into["deprecated_flag"] = True


def apply(db: Session, entities: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Returns (entities_after_merges, merged_key_map from_key → to_key)."""
    by_key = {e["system_id"]: e for e in entities}
    links = db.scalars(select(IdentityLink).order_by(IdentityLink.id)).all()
    merged: dict[str, str] = {}

    def resolve(k: str) -> str:
        seen = set()
        while k in merged and k not in seen:
            seen.add(k)
            k = merged[k]
        return k

    for l in links:
        if l.relation != "same_as":
            continue
        src, dst = resolve(l.from_key), resolve(l.to_key)
        if src == dst or src not in by_key or dst not in by_key:
            continue
        _merge(by_key[dst], by_key[src], l.evidence or [])
        merged[src] = dst
        del by_key[src]
    for l in links:
        if l.relation in ("implementation_of", "related_to", "distinct_from"):
            a, b = resolve(l.from_key), resolve(l.to_key)
            for x, y, direction in ((a, b, "outgoing"), (b, a, "incoming")):
                if x in by_key:
                    by_key[x].setdefault("related_systems", []).append({"system_id": y, "relation": l.relation, "direction": direction})

    for c in db.scalars(select(EntityCuration)):
        e = by_key.get(resolve(c.entity_key))
        if not e:
            continue
        if c.field == "official_docs_url" and c.value:
            e["official_docs_url"] = c.value
            e["documentation_url"] = c.value
        elif c.field == "organization" and c.value:
            e["organization"] = c.value
        elif c.field == "organization_aliases" and c.value:
            e["organization_aliases"] = c.value
        elif c.field == "related_urls" and c.value:
            rel = e.setdefault("related_urls", [])
            rel.extend(u for u in c.value if u not in rel)
        e.setdefault("curated_fields", {})[c.field] = {"value": c.value, "evidence": (c.evidence or [])[:3]}

    # field-level verification coverage
    ev = defaultdict(lambda: defaultdict(lambda: {"verified": 0, "partially_verified": 0, "unverified": 0}))
    for key, path, status, n in db.execute(select(AttributeEvidence.system_key, AttributeEvidence.attribute_path, AttributeEvidence.verification_status,
                                                  func.count()).group_by(AttributeEvidence.system_key, AttributeEvidence.attribute_path,
                                                                         AttributeEvidence.verification_status)):
        ev[resolve(key)][path][status] += n
    for k, e in by_key.items():
        attrs = ev.get(k, {})
        present = {a for a, c in attrs.items() if c["verified"] or c["partially_verified"]}
        verified_req = [a for a in ALL_REQUIRED if attrs.get(a, {}).get("verified")]
        missing = [a for a in ALL_REQUIRED if a not in present]
        e["verification_coverage"] = {
            "required": len(ALL_REQUIRED), "verified_required": len(verified_req), "present_required": len(ALL_REQUIRED) - len(missing),
            "missing_required": missing, "attributes_with_evidence": len(attrs),
            "groups": {g: all(attrs.get(a, {}).get("verified") for a in v) for g, v in REQUIRED_ATTRIBUTES.items()},
        } if attrs else {}
        if attrs:
            if len(verified_req) == len(ALL_REQUIRED):
                e["verification_status"], e["verification_basis"] = "verified", "all required attribute groups verified against official sources"
            else:
                e["verification_status"] = "partially_verified"
                e["verification_basis"] = f"{len(verified_req)}/{len(ALL_REQUIRED)} required attributes verified against official sources"
        elif e.get("verification_status") == "verified":
            # Official library records exist but no field-level evidence has been recorded yet.
            e["verification_status"] = "partially_verified"
            e["verification_basis"] = "official documentation inspected; field-level evidence not yet recorded"
    return list(by_key.values()), merged
