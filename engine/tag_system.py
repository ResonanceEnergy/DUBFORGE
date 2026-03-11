"""
DUBFORGE — Tag System  (Session 199)

Tagging and categorization for samples, presets,
and projects. Supports hierarchical tags, search,
and tag-based organization.
"""

import json
import os
import time
from dataclasses import dataclass, field

from engine.config_loader import PHI
# Built-in tag taxonomy for dubstep production
TAXONOMY = {
    "type": ["bass", "lead", "pad", "fx", "drum", "vocal",
             "texture", "riser", "impact", "loop"],
    "style": ["dubstep", "riddim", "melodic", "tearout",
              "hybrid", "experimental", "heavy", "chill"],
    "energy": ["low", "medium", "high", "extreme"],
    "mood": ["dark", "aggressive", "ethereal", "melodic",
             "mysterious", "powerful", "dreamy"],
    "key": ["C", "D", "E", "F", "G", "A", "B"],
    "tempo": ["slow", "medium", "fast", "halftime"],
    "texture": ["smooth", "gritty", "metallic", "organic",
                "digital", "warm", "cold"],
    "technique": ["wobble", "growl", "reese", "formant",
                  "granular", "additive", "fm", "wavetable"],
}


@dataclass
class TaggedItem:
    """An item with tags."""
    item_id: str
    name: str
    item_type: str  # "sample", "preset", "project"
    tags: set[str] = field(default_factory=set)
    metadata: dict = field(default_factory=dict)
    created: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.item_id,
            "name": self.name,
            "type": self.item_type,
            "tags": sorted(self.tags),
            "metadata": self.metadata,
        }


class TagSystem:
    """Tag-based organization system."""

    def __init__(self, data_dir: str = "output/tags"):
        self.data_dir = data_dir
        self.items: dict[str, TaggedItem] = {}
        self.tag_index: dict[str, set[str]] = {}  # tag → item_ids
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    def add_item(self, item_id: str, name: str,
                 item_type: str = "sample",
                 tags: list[str] = None,
                 metadata: dict = None) -> TaggedItem:
        """Add or update a tagged item."""
        if item_id in self.items:
            item = self.items[item_id]
            if tags:
                for tag in tags:
                    item.tags.add(tag.lower())
            if metadata:
                item.metadata.update(metadata)
        else:
            item = TaggedItem(
                item_id=item_id,
                name=name,
                item_type=item_type,
                tags=set(t.lower() for t in (tags or [])),
                metadata=metadata or {},
                created=time.time(),
            )
            self.items[item_id] = item

        # Update index
        for tag in item.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(item_id)

        self._save()
        return item

    def remove_item(self, item_id: str) -> bool:
        """Remove an item."""
        item = self.items.pop(item_id, None)
        if not item:
            return False

        for tag in item.tags:
            if tag in self.tag_index:
                self.tag_index[tag].discard(item_id)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]

        self._save()
        return True

    def add_tags(self, item_id: str, tags: list[str]) -> bool:
        """Add tags to an item."""
        item = self.items.get(item_id)
        if not item:
            return False

        for tag in tags:
            tag = tag.lower()
            item.tags.add(tag)
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(item_id)

        self._save()
        return True

    def remove_tags(self, item_id: str, tags: list[str]) -> bool:
        """Remove tags from an item."""
        item = self.items.get(item_id)
        if not item:
            return False

        for tag in tags:
            tag = tag.lower()
            item.tags.discard(tag)
            if tag in self.tag_index:
                self.tag_index[tag].discard(item_id)

        self._save()
        return True

    def search_by_tags(self, tags: list[str],
                       match_all: bool = True) -> list[TaggedItem]:
        """Search items by tags."""
        tags = [t.lower() for t in tags]

        if match_all:
            # All tags must match
            result_ids: set[str] | None = None
            for tag in tags:
                ids = self.tag_index.get(tag, set())
                if result_ids is None:
                    result_ids = set(ids)
                else:
                    result_ids &= ids
            item_ids = result_ids or set()
        else:
            # Any tag matches
            item_ids: set[str] = set()
            for tag in tags:
                item_ids |= self.tag_index.get(tag, set())

        return [self.items[iid] for iid in item_ids
                if iid in self.items]

    def search_by_type(self, item_type: str) -> list[TaggedItem]:
        """Search items by type."""
        return [item for item in self.items.values()
                if item.item_type == item_type]

    def search_text(self, query: str) -> list[TaggedItem]:
        """Full text search across names and tags."""
        query = query.lower()
        results: list[TaggedItem] = []
        for item in self.items.values():
            if query in item.name.lower():
                results.append(item)
            elif any(query in tag for tag in item.tags):
                results.append(item)
        return results

    def get_all_tags(self) -> dict[str, int]:
        """Get all tags with usage counts."""
        return {tag: len(ids) for tag, ids in self.tag_index.items()
                if ids}

    def get_related_tags(self, tag: str, limit: int = 10) -> list[tuple[str, int]]:
        """Find tags that co-occur with given tag."""
        tag = tag.lower()
        item_ids = self.tag_index.get(tag, set())
        co_counts: dict[str, int] = {}

        for iid in item_ids:
            item = self.items.get(iid)
            if item:
                for t in item.tags:
                    if t != tag:
                        co_counts[t] = co_counts.get(t, 0) + 1

        sorted_tags = sorted(co_counts.items(),
                              key=lambda x: x[1], reverse=True)
        return sorted_tags[:limit]

    def auto_tag(self, name: str) -> list[str]:
        """Auto-suggest tags based on name."""
        name_lower = name.lower()
        suggested: list[str] = []

        for category, tags in TAXONOMY.items():
            for tag in tags:
                if tag in name_lower:
                    suggested.append(tag)

        # PHI-related auto-tags
        if "phi" in name_lower or "golden" in name_lower:
            suggested.append("phi")
        if "432" in name_lower:
            suggested.append("432hz")

        return list(set(suggested))

    def get_taxonomy(self) -> dict:
        """Get the built-in taxonomy."""
        return dict(TAXONOMY)

    def get_summary(self) -> dict:
        """Get tag system summary."""
        type_counts: dict[str, int] = {}
        for item in self.items.values():
            type_counts[item.item_type] = (
                type_counts.get(item.item_type, 0) + 1
            )

        return {
            "total_items": len(self.items),
            "total_tags": len(self.tag_index),
            "types": type_counts,
            "top_tags": sorted(
                self.get_all_tags().items(),
                key=lambda x: x[1], reverse=True
            )[:10],
        }

    def _save(self) -> None:
        """Persist to disk."""
        data = {
            "items": {
                k: {**v.to_dict(), "created": v.created}
                for k, v in self.items.items()
            },
        }
        with open(os.path.join(self.data_dir, "tags.json"), "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Load from disk."""
        path = os.path.join(self.data_dir, "tags.json")
        if not os.path.exists(path):
            return

        with open(path) as f:
            data = json.load(f)

        for iid, idata in data.get("items", {}).items():
            item = TaggedItem(
                item_id=iid,
                name=idata["name"],
                item_type=idata["type"],
                tags=set(idata.get("tags", [])),
                metadata=idata.get("metadata", {}),
                created=idata.get("created", 0),
            )
            self.items[iid] = item
            for tag in item.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(iid)


def main() -> None:
    print("Tag System")

    tags = TagSystem()

    # Add samples
    tags.add_item("s001", "Heavy Wobble Bass", "sample",
                  ["bass", "wobble", "heavy", "dubstep"])
    tags.add_item("s002", "Dark Pad Texture", "sample",
                  ["pad", "dark", "texture", "ethereal"])
    tags.add_item("s003", "Riddim Growl Bass", "sample",
                  ["bass", "growl", "riddim", "aggressive"])
    tags.add_item("s004", "PHI Golden Riser", "sample",
                  ["riser", "phi", "ethereal", "dubstep"])
    tags.add_item("p001", "Tearout Lead", "preset",
                  ["lead", "tearout", "aggressive", "gritty"])

    # Search
    bass_samples = tags.search_by_tags(["bass"])
    print(f"  Bass: {[i.name for i in bass_samples]}")

    dark = tags.search_by_tags(["dark", "ethereal"], match_all=False)
    print(f"  Dark/ethereal: {[i.name for i in dark]}")

    # Auto-tag
    suggested = tags.auto_tag("heavy wobble bass dubstep growl")
    print(f"  Auto-tags: {suggested}")

    # Related
    related = tags.get_related_tags("bass")
    print(f"  Related to 'bass': {related}")

    # Summary
    print(f"\n  Summary: {tags.get_summary()}")
    print("Done.")


if __name__ == "__main__":
    main()
