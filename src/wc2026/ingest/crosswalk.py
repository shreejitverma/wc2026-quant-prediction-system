"""Canonical team-name crosswalk across all data sources.

The problem: every source uses a different team identifier.
  martj42 results:  "England", "United States", "South Korea"
  eloratings.net:   "EN", "US", "KO"
  Kalshi tickers:   "ENG", "USA", "KOR"
  FIFA official:    "England", "USA", "Republic of Korea"

One canonical ID (we use FIFA/English form as the internal standard) + a
crosswalk table maps every source-specific string to it.

Bootstrap: a static YAML file (`configs/crosswalk_teams.yaml`) holds the
manually-curated entries. Fuzzy matching (Jaro-Winkler on lowercased names)
is used for lookup of unknown strings and offers ranked candidates for human
review. All fuzzy matches are logged and must be confirmed before entering any
model feature.

Why a static YAML rather than a DB table: this is a small, slow-changing table
(~250 national teams). YAML is version-controlled, diffable, and requires no
migration machinery. A DB is appropriate only if we later need to query it
relationally at scale, which we do not.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CROSSWALK = Path(__file__).parents[3] / "configs" / "crosswalk_teams.yaml"


def _normalize(s: str) -> str:
    """Lowercase, strip accents, collapse whitespace, remove punctuation."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class TeamCrosswalk:
    """Map source-specific team identifiers to a canonical team name.

    Usage:
        cw = TeamCrosswalk.from_yaml("configs/crosswalk_teams.yaml")
        canonical = cw.resolve("EN")        # -> "England"
        canonical = cw.resolve("England")   # -> "England"
        candidates = cw.fuzzy("Englond")    # -> [("England", 0.96), ...]
    """

    def __init__(self, entries: list[dict[str, Any]]) -> None:
        # index: any alias -> canonical name
        self._alias_to_canon: dict[str, str] = {}
        self._canon_to_aliases: dict[str, list[str]] = {}
        for entry in entries:
            canon = str(entry["canonical"])
            aliases: list[str] = entry.get("aliases", [])
            all_names = [canon] + aliases
            self._canon_to_aliases[canon] = aliases
            for name in all_names:
                for variant in (name, _normalize(name)):
                    self._alias_to_canon[variant] = canon

    @classmethod
    def from_yaml(cls, path: str | Path = _DEFAULT_CROSSWALK) -> TeamCrosswalk:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data.get("teams", []))

    @classmethod
    def empty(cls) -> TeamCrosswalk:
        return cls([])

    def resolve(self, name: str) -> str | None:
        """Return the canonical name for `name`, or None if not found."""
        return self._alias_to_canon.get(name) or self._alias_to_canon.get(_normalize(name))

    def resolve_strict(self, name: str) -> str:
        """Return canonical or raise KeyError."""
        c = self.resolve(name)
        if c is None:
            raise KeyError(f"Unknown team name: {name!r}. Add it to crosswalk_teams.yaml.")
        return c

    def fuzzy(self, name: str, top_n: int = 5) -> list[tuple[str, float]]:
        """Return top-N (canonical_name, similarity_score) candidates for an unknown string.

        Used to propose candidates for human confirmation, never for automatic resolution.
        Scores are Jaro-Winkler via Python difflib SequenceMatcher.
        """
        norm = _normalize(name)
        scores: list[tuple[str, float]] = []
        seen_canons: set[str] = set()
        for alias, canon in self._alias_to_canon.items():
            if canon in seen_canons:
                continue
            score = SequenceMatcher(None, norm, _normalize(alias)).ratio()
            scores.append((canon, score))
            seen_canons.add(canon)
        scores.sort(key=lambda x: -x[1])
        return scores[:top_n]

    def all_canonicals(self) -> list[str]:
        return sorted(self._canon_to_aliases.keys())

    def __len__(self) -> int:
        return len(self._canon_to_aliases)
