"""Stats service layer — band/mode/DXCC aggregation for operator stats page."""
from __future__ import annotations

import pycountry
from app.callsign.prefixes import lookup_prefix


async def _aggregate_to_list(collection, pipeline: list[dict]) -> list[dict]:
    cursor = collection.aggregate(pipeline)
    if hasattr(cursor, "__await__"):
        cursor = await cursor
    return await cursor.to_list(length=None)


async def get_stats(callsign: str, collection) -> dict:
    """Compute band counts, mode counts, DXCC entity counts for one operator.

    Returns same dict shape for empty and non-empty logs (STATS-07).
    All pipelines begin with $match guard (STATS-06).
    """
    match_stage = {"$match": {"_operator": callsign, "_deleted": False}}

    # --- Band counts ---
    band_pipeline = [
        match_stage,
        {"$group": {"_id": "$BAND", "count": {"$sum": 1}}},
    ]
    band_results = await _aggregate_to_list(collection, band_pipeline)
    band_counts = {doc["_id"]: doc["count"] for doc in band_results if doc["_id"]}

    # --- Mode counts ---
    mode_pipeline = [
        match_stage,
        {"$group": {"_id": "$MODE", "count": {"$sum": 1}}},
    ]
    mode_results = await _aggregate_to_list(collection, mode_pipeline)
    mode_counts = {doc["_id"]: doc["count"] for doc in mode_results if doc["_id"]}

    # --- Total QSO count (includes QSOs with null BAND/MODE — WR-02) ---
    # Use a dedicated $count pipeline so total_qsos is independent of BAND/MODE
    # completeness. band_counts and mode_counts already exclude null-field docs
    # via their `if doc["_id"]` guards, so computing total from call_pipeline
    # (which groups by CALL and sums all docs) would include null-BAND QSOs and
    # create a discrepancy. A $count pipeline makes the intent explicit.
    count_pipeline = [
        match_stage,
        {"$count": "total"},
    ]
    count_result = await _aggregate_to_list(collection, count_pipeline)
    total_qsos = count_result[0]["total"] if count_result else 0

    # --- CALL-level counts for DXCC rollup (kept separate from total_qsos) ---
    call_pipeline = [
        match_stage,
        {"$group": {"_id": "$CALL", "count": {"$sum": 1}}},
    ]
    call_results = await _aggregate_to_list(collection, call_pipeline)

    # Early return for empty log (STATS-07)
    if total_qsos == 0:
        return {
            "band_counts": {},
            "mode_counts": {},
            "entity_counts": [],
            "unique_entity_count": 0,
            "total_qsos": 0,
        }

    # --- Python-side DXCC rollup (D-01, D-02) ---
    entity_totals: dict[str, int] = {}
    iso_seen: set[str] = set()
    for doc in call_results:
        iso = lookup_prefix(doc["_id"])
        if iso is None:
            name = "Unknown"  # D-02: unresolvable callsigns grouped as "Unknown"
        else:
            iso_seen.add(iso)
            country = pycountry.countries.get(alpha_2=iso)
            name = country.name if country else iso  # D-01: pycountry for full names

        entity_totals[name] = entity_totals.get(name, 0) + doc["count"]

    # Count unique countries from iso_seen, then add 1 if "Unknown" bucket exists
    # so that non-country ITU entities (UN, WMO, ICAO) and unresolvable callsigns
    # are represented in the count — not silently excluded (WR-01).
    unique_entity_count = len(iso_seen)
    if "Unknown" in entity_totals:
        unique_entity_count += 1  # WR-01: Unknown/Other bucket counts as one entity

    # Sort and truncate to top-8 + optional "Other"
    sorted_entities = sorted(entity_totals.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_entities) <= 8:
        entity_counts = [{"name": k, "count": v} for k, v in sorted_entities]
    else:
        top8 = sorted_entities[:8]
        remainder = sum(v for _, v in sorted_entities[8:])
        entity_counts = [{"name": k, "count": v} for k, v in top8]
        entity_counts.append({"name": "Other", "count": remainder})

    return {
        "band_counts": band_counts,
        "mode_counts": mode_counts,
        "entity_counts": entity_counts,
        "unique_entity_count": unique_entity_count,
        "total_qsos": total_qsos,
    }
