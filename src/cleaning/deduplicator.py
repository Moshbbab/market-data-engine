"""
Deduplicator
============

Detects and removes (or merges) duplicate property records originating
from different extraction sources or repeated ingestion runs.

Deduplication strategy
----------------------
1. **Exact match** – records sharing the same MLS ID or parcel ID are
   guaranteed duplicates; the freshest one is kept.
2. **Fuzzy address match** – records whose normalised address and city are
   identical (after stripping punctuation / case) are treated as duplicates;
   their numeric fields are merged using the first-non-null rule.

Author: Hemmah Valuation Systems
License: MIT
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _canonical_address(address: Optional[str], city: Optional[str] = None) -> str:
    """Return a lowercase, punctuation-stripped address key."""
    parts = [address or "", city or ""]
    combined = " ".join(p for p in parts if p)
    # Collapse internal whitespace before stripping non-alphanumeric characters
    combined = re.sub(r"\s+", " ", combined).strip()
    return re.sub(r"[^a-z0-9 ]", "", combined.lower()).strip()


def _merge_records(base: Dict, incoming: Dict) -> Dict:
    """
    Merge *incoming* into *base* using first-non-null rule.

    For string fields the base value is preferred; for numeric fields the
    non-null value is preferred (incoming wins only when base is None).
    """
    merged = dict(base)
    for key, value in incoming.items():
        if merged.get(key) is None and value is not None:
            merged[key] = value
    # If incoming has a more recent normalised_at, update it
    incoming_ts = incoming.get("normalised_at", "")
    base_ts = merged.get("normalised_at", "")
    if incoming_ts > base_ts:
        merged["normalised_at"] = incoming_ts
    return merged


class Deduplicator:
    """
    Identify and remove duplicate property records.

    Attributes:
        merge (bool): When True, merge duplicate records rather than
            discarding them. Default is True.
    """

    def __init__(self, merge: bool = True) -> None:
        self.merge = merge
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deduplicate(self, records: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Remove duplicate records from *records*.

        Args:
            records: Normalised property records.

        Returns:
            Tuple of (deduplicated records, number of duplicates removed).
        """
        by_mls: Dict[str, Dict] = {}
        by_parcel: Dict[str, Dict] = {}
        by_address: Dict[str, Dict] = {}
        duplicates_removed = 0

        for record in records:
            canonical, existing_key = self._find_existing(record, by_mls, by_parcel, by_address)

            if existing_key is not None:
                # Duplicate found
                duplicates_removed += 1
                if self.merge:
                    existing = by_address.get(existing_key) or by_mls.get(existing_key) or by_parcel.get(existing_key)
                    if existing is not None:
                        merged = _merge_records(existing, record)
                        self._index_record(merged, by_mls, by_parcel, by_address)
                # When not merging, simply skip the incoming record
            else:
                self._index_record(record, by_mls, by_parcel, by_address)

        # Collect unique records (by_address is the authoritative index when
        # an address key is present; fall back to ID-only indexes).
        seen_ids: set = set()
        result: List[Dict] = []
        for index in (by_address, by_mls, by_parcel):
            for key, rec in index.items():
                uid = id(rec)
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    result.append(rec)

        self.logger.info(
            "Deduplication complete: %d unique records, %d duplicates removed",
            len(result),
            duplicates_removed,
        )
        return result, duplicates_removed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_existing(
        self,
        record: Dict,
        by_mls: Dict[str, Dict],
        by_parcel: Dict[str, Dict],
        by_address: Dict[str, Dict],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return (canonical_address_key, existing_key) if a duplicate exists."""
        # Check MLS ID
        mls_id = record.get("mls_id")
        if mls_id and mls_id in by_mls:
            return None, mls_id

        # Check parcel ID
        parcel_id = record.get("parcel_id")
        if parcel_id and parcel_id in by_parcel:
            return None, parcel_id

        # Check normalised address
        addr_key = _canonical_address(record.get("address"), record.get("city"))
        if addr_key and addr_key in by_address:
            return addr_key, addr_key

        return addr_key, None

    @staticmethod
    def _index_record(
        record: Dict,
        by_mls: Dict[str, Dict],
        by_parcel: Dict[str, Dict],
        by_address: Dict[str, Dict],
    ) -> None:
        mls_id = record.get("mls_id")
        if mls_id:
            by_mls[mls_id] = record

        parcel_id = record.get("parcel_id")
        if parcel_id:
            by_parcel[parcel_id] = record

        addr_key = _canonical_address(record.get("address"), record.get("city"))
        if addr_key:
            by_address[addr_key] = record
