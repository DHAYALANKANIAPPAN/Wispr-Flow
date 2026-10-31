"""Knowledge Graph management with NetworkX.

Purpose:
    Represents academic concepts and prerequisite dependencies as a Directed Acyclic Graph (DAG).
    Determines concept accessibility (unlocked/locked status) for individual students based on mastery.

Status:
    Active, Phase 1 implementation.

Fail-Closed Behavior:
    - Rejects prerequisite cycles at load time by raising ValueError.
    - Rejects references to non-existent concepts.
    - Raises KeyError when querying unknown concept IDs.
    - Default fail-closed policy: a concept is locked if prerequisite mastery cannot be confirmed.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import networkx as nx
from sqlalchemy.orm import Session

from backend.app.models import LearnerMastery

DEFAULT_CONCEPTS_PATH = Path(__file__).resolve().parent.parent.parent / "content" / "electricity" / "concepts.json"
DEFAULT_UNLOCK_THRESHOLD = 0.60


class KnowledgeGraph:
    """Manages the prerequisite Directed Acyclic Graph (DAG) for academic concepts."""

    def __init__(self, concepts_path: Optional[str | Path] = None, unlock_threshold: float = DEFAULT_UNLOCK_THRESHOLD):
        """Initialize and build the concept graph from JSON.

        Args:
            concepts_path: Optional file path to concepts JSON.
            unlock_threshold: Minimum mastery required in prerequisites to unlock a dependent concept.
        """
        self.path = Path(concepts_path) if concepts_path else DEFAULT_CONCEPTS_PATH
        self.unlock_threshold = unlock_threshold
        self.graph = nx.DiGraph()
        self.concept_metadata: Dict[str, Dict[str, Any]] = {}
        self.load_graph()

    def load_graph(self) -> None:
        """Load concepts and prerequisites from JSON and validate DAG structure.

        Raises:
            FileNotFoundError: If concepts file does not exist.
            ValueError: If cycles are detected or invalid concept IDs are referenced.
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Concepts specification not found at {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        concepts = data.get("concepts", [])
        self.graph.clear()
        self.concept_metadata.clear()

        # Add all concept nodes first
        for item in concepts:
            cid = item["id"]
            self.graph.add_node(cid, name=item.get("name", cid), description=item.get("description", ""))
            self.concept_metadata[cid] = item

        # Add prerequisite edges: prerequisite -> concept
        for item in concepts:
            cid = item["id"]
            prereqs = item.get("prerequisites", [])
            for p in prereqs:
                if p not in self.graph:
                    raise ValueError(f"Concept '{cid}' references unknown prerequisite '{p}'")
                self.graph.add_edge(p, cid)

        # Enforce DAG property: reject cycles
        if not nx.is_directed_acyclic_graph(self.graph):
            cycles = list(nx.simple_cycles(self.graph))
            raise ValueError(f"Cycle detected in concept prerequisites graph: {cycles}")

    def get_all_concepts(self) -> List[Dict[str, Any]]:
        """Return a list of all concepts with metadata and immediate prerequisites."""
        result = []
        for cid, meta in self.concept_metadata.items():
            prereqs = list(self.graph.predecessors(cid))
            result.append({
                "id": cid,
                "name": meta.get("name", cid),
                "description": meta.get("description", ""),
                "prerequisites": prereqs,
            })
        return result

    def prerequisites_of(self, concept_id: str) -> List[str]:
        """Return immediate prerequisites for a given concept.

        Args:
            concept_id: Target concept identifier.

        Returns:
            List[str]: List of prerequisite concept IDs.

        Raises:
            KeyError: If concept_id is not present in the graph.
        """
        if concept_id not in self.graph:
            raise KeyError(f"Unknown concept ID: {concept_id}")
        return list(self.graph.predecessors(concept_id))

    def is_unlocked(
        self,
        student_id: Optional[str],
        concept_id: str,
        db: Optional[Session] = None,
        mastery_map: Optional[Dict[str, float]] = None,
    ) -> bool:
        """Determine if a concept is unlocked for a student.

        Rules:
        - Root concepts (no prerequisites) are always unlocked.
        - Dependent concepts require every prerequisite to have mastery >= unlock_threshold.
        - If student has no recorded mastery for a prerequisite, it defaults to locked (0.0).

        Args:
            student_id: Target student identifier (optional).
            concept_id: Concept to evaluate.
            db: Optional database session to query LearnerMastery.
            mastery_map: Optional preloaded mapping of concept_id -> mastery.

        Returns:
            bool: True if unlocked, False otherwise.

        Raises:
            KeyError: If concept_id is not in the graph.
        """
        if concept_id not in self.graph:
            raise KeyError(f"Unknown concept ID: {concept_id}")

        prereqs = self.prerequisites_of(concept_id)
        if not prereqs:
            # Root concept: always unlocked
            return True

        if not student_id:
            # Dependent concepts without student context remain locked
            return False

        # Gather student mastery per prerequisite
        effective_mastery: Dict[str, float] = {}

        if mastery_map is not None:
            effective_mastery = mastery_map
        elif db is not None:
            records = (
                db.query(LearnerMastery)
                .filter(
                    LearnerMastery.student_id == student_id,
                    LearnerMastery.concept_id.in_(prereqs),
                )
                .all()
            )
            effective_mastery = {r.concept_id: r.mastery for r in records}

        # Check all prerequisites meet or exceed the threshold
        for p in prereqs:
            p_mastery = effective_mastery.get(p, 0.0)
            if p_mastery < self.unlock_threshold:
                return False

        return True


# Global default instance
knowledge_graph = KnowledgeGraph()
