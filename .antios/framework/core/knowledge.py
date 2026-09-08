"""AntiOS Agent-Native Project Knowledge & Intelligent Wayfinding Core.

Provides deterministic in-memory relationship graphs, progressive context
disclosure (L0-L5), file->component intelligence, change-intent analysis,
ownership derivation, and documentation infrastructure classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from framework.core.subsystem import SubsystemDeclaration


# =============================================================================
# 1. Epistemic Authority & Relationship Types
# =============================================================================

class KnowledgeEpistemicTier(str, Enum):
    """Epistemic certainty tiers for project knowledge facts and edges."""
    OBSERVED = "OBSERVED"     # Directly witnessed on physical disk / manifest
    INFERRED = "INFERRED"     # Deterministically derived heuristic with confidence
    UNKNOWN = "UNKNOWN"       # Unverified or missing evidence


class RelationshipType(str, Enum):
    """Canonical directed relationship types between project entities."""
    DEPENDS_ON = "DEPENDS_ON"                   # Component -> Component
    CONSUMED_BY = "CONSUMED_BY"                 # Component -> Component
    TESTED_BY = "TESTED_BY"                     # Component -> Test File / Runner
    GOVERNED_BY = "GOVERNED_BY"                 # Component -> Rule
    REQUIRES_SKILL = "REQUIRES_SKILL"           # Component -> Skill
    IMPLEMENTED_THROUGH = "IMPLEMENTED_THROUGH" # Component -> Workflow
    OWNED_BY = "OWNED_BY"                       # Component -> Person / Team
    DOCUMENTED_BY = "DOCUMENTED_BY"             # Component -> Document


@dataclass(frozen=True)
class KnowledgeEdge:
    """A directed, typed relationship edge between two entities."""
    source: str
    target: str
    relation: RelationshipType
    authority: KnowledgeEpistemicTier = KnowledgeEpistemicTier.INFERRED
    confidence: float = 1.0
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation.value,
            "authority": self.authority.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }


# =============================================================================
# 2. Ownership Derivation Model
# =============================================================================

@dataclass(frozen=True)
class OwnershipResolution:
    """Resolved ownership details for a path or component."""
    owner: Optional[str]
    source: str          # "CODEOWNERS", "MANIFEST", "MAINTAINER_FILE", "UNKNOWN"
    confidence: float    # 0.0 to 1.0
    pattern_matched: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OwnershipDeriver:
    """Deterministic repository ownership scanner and resolver.
    
    Zero fabricated certainty: only returns owners substantiated by physical
    files on disk.
    """

    CODEOWNERS_LOCATIONS = [
        ".github/CODEOWNERS",
        "CODEOWNERS",
        "docs/CODEOWNERS",
        ".gitlab/CODEOWNERS",
    ]

    MAINTAINER_FILES = [
        "MAINTAINERS",
        "MAINTAINERS.md",
        "AUTHORS",
        "AUTHORS.md",
        "CONTRIBUTORS",
        "CONTRIBUTORS.md",
    ]

    def __init__(self, workspace_root: str = ""):
        self.workspace_root = os.path.normcase(os.path.abspath(workspace_root)) if workspace_root else ""
        self._codeowners_rules: List[Tuple[str, str]] = []  # (pattern, owner)
        self._manifest_owners: Dict[str, str] = {}         # dir_rel_path -> owner
        self._maintainer_fallback: Optional[str] = None
        self._scanned = False

    def scan(self) -> None:
        """Scans workspace for authoritative ownership files."""
        if not self.workspace_root or not os.path.isdir(self.workspace_root):
            self._scanned = True
            return

        self._scan_codeowners()
        self._scan_manifests()
        self._scan_maintainer_files()
        self._scanned = True

    def _scan_codeowners(self) -> None:
        """Parses git CODEOWNERS file into rules if present."""
        for rel_loc in self.CODEOWNERS_LOCATIONS:
            full_loc = os.path.join(self.workspace_root, rel_loc)
            if os.path.isfile(full_loc):
                try:
                    with open(full_loc, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            clean = line.strip()
                            if not clean or clean.startswith("#"):
                                continue
                            parts = clean.split()
                            if len(parts) >= 2:
                                pattern = parts[0].replace("\\", "/").strip("/")
                                owner = parts[1]
                                self._codeowners_rules.append((pattern, owner))
                    if self._codeowners_rules:
                        break
                except Exception:
                    pass

    def _scan_manifests(self) -> None:
        """Extracts author/maintainer metadata from package manifests."""
        import json
        for root, dirs, files in os.walk(self.workspace_root):
            # Prune noisy directories
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "node_modules", "target", "build", "dist", ".agents"}]
            rel_dir = os.path.relpath(root, self.workspace_root).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""

            # package.json
            if "package.json" in files:
                try:
                    with open(os.path.join(root, "package.json"), "r", encoding="utf-8", errors="replace") as f:
                        pkg = json.load(f)
                        author = pkg.get("author")
                        if isinstance(author, str) and author.strip():
                            self._manifest_owners[rel_dir] = author.strip()
                        elif isinstance(author, dict) and author.get("name"):
                            self._manifest_owners[rel_dir] = str(author["name"]).strip()
                except Exception:
                    pass

            # Cargo.toml
            if "Cargo.toml" in files:
                try:
                    with open(os.path.join(root, "Cargo.toml"), "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        m = re.search(r'authors\s*=\s*\[\s*"([^"]+)"', content)
                        if m:
                            self._manifest_owners[rel_dir] = m.group(1).strip()
                except Exception:
                    pass

            # pyproject.toml
            if "pyproject.toml" in files:
                try:
                    with open(os.path.join(root, "pyproject.toml"), "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        m = re.search(r'name\s*=\s*"([^"]+)"', content)
                        # Look for authors in pyproject
                        m_auth = re.search(r'authors\s*=\s*\[\s*\{\s*name\s*=\s*"([^"]+)"', content)
                        if m_auth:
                            self._manifest_owners[rel_dir] = m_auth.group(1).strip()
                except Exception:
                    pass

    def _scan_maintainer_files(self) -> None:
        """Extracts top maintainer from project-level maintainer documents."""
        for rel_loc in self.MAINTAINER_FILES:
            full_loc = os.path.join(self.workspace_root, rel_loc)
            if os.path.isfile(full_loc):
                try:
                    with open(full_loc, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            clean = line.strip()
                            if clean and not clean.startswith("#"):
                                # Extract first name or handle
                                clean_owner = clean.lstrip("-* ").split("<")[0].split("(")[0].strip()
                                if clean_owner:
                                    self._maintainer_fallback = clean_owner
                                    return
                except Exception:
                    pass

    def resolve_path(self, file_path: str) -> OwnershipResolution:
        """Resolves ownership for a given file path."""
        import fnmatch
        if not self._scanned:
            self.scan()

        clean_path = file_path.replace("\\", "/").strip("/")

        # 1. Check CODEOWNERS (highest authority, last matching rule wins)
        fallback_wildcard_owner = None
        for pattern, owner in reversed(self._codeowners_rules):
            if pattern == "*" or pattern == "":
                if not fallback_wildcard_owner:
                    fallback_wildcard_owner = owner
                continue
            # Strip trailing wildcards for prefix checks
            base_pattern = pattern.rstrip("*").rstrip("/")
            if fnmatch.fnmatch(clean_path, pattern) or clean_path.startswith(base_pattern + "/") or clean_path == base_pattern:
                return OwnershipResolution(owner=owner, source="CODEOWNERS", confidence=0.95, pattern_matched=pattern)

        if fallback_wildcard_owner:
            return OwnershipResolution(owner=fallback_wildcard_owner, source="CODEOWNERS", confidence=0.95, pattern_matched="*")

        # 2. Check Package Manifest Owners
        parts = clean_path.split("/")
        for i in range(len(parts), -1, -1):
            sub_dir = "/".join(parts[:i])
            if sub_dir in self._manifest_owners:
                return OwnershipResolution(
                    owner=self._manifest_owners[sub_dir],
                    source="MANIFEST",
                    confidence=0.80,
                    pattern_matched=sub_dir or "[root]",
                )

        # 3. Maintainer fallback
        if self._maintainer_fallback:
            return OwnershipResolution(
                owner=self._maintainer_fallback,
                source="MAINTAINER_FILE",
                confidence=0.50,
                pattern_matched="[project-maintainers]",
            )

        # 4. Unknown
        return OwnershipResolution(
            owner=None,
            source="UNKNOWN",
            confidence=0.0,
            pattern_matched="",
        )


# =============================================================================
# 3. Documentation as Agent Infrastructure
# =============================================================================

class DocCategory(str, Enum):
    """Categorization of project documentation for agent utility."""
    AUTHORITATIVE = "authoritative"   # Constitutions, rules, root specs (e.g. AGENTS.md)
    ARCHITECTURE = "architecture"     # System architecture, topology, ADRs
    COMPONENT = "component"           # Subsystem or package level guides
    SETUP = "setup"                   # Installation, environment, toolchain guides
    TESTING = "testing"               # Testing instructions, test harness specs
    CONTRIBUTION = "contribution"     # Contribution guidelines, workflow rules
    GENERAL = "general"               # Other documentation


@dataclass(frozen=True)
class DocArtifactFact:
    """Structured assessment of a documentation file."""
    path: str
    category: DocCategory
    is_authoritative: bool
    is_clean: bool                    # Checked against Staleguard Layer 1
    broken_references_count: int
    covering_subsystems: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "category": self.category.value,
            "is_authoritative": self.is_authoritative,
            "is_clean": self.is_clean,
            "broken_references_count": self.broken_references_count,
            "covering_subsystems": list(self.covering_subsystems),
        }


class DocKnowledgeClassifier:
    """Classifies repository documentation into agent-functional categories."""

    AUTHORITATIVE_NAMES = {
        "agents.md",
        "antios_constitution.md",
        "architecture.md",
        "readme.md",
    }

    @classmethod
    def classify_file(cls, rel_path: str) -> DocCategory:
        """Determines the functional documentation category of a file."""
        norm_p = rel_path.replace("\\", "/").lower()
        basename = os.path.basename(norm_p)

        if basename in cls.AUTHORITATIVE_NAMES:
            return DocCategory.AUTHORITATIVE
        if "adr" in norm_p or "architecture" in norm_p or "arch." in norm_p or "arch/" in norm_p or "blueprint" in norm_p:
            return DocCategory.ARCHITECTURE
        if "test" in norm_p or "verify" in norm_p:
            return DocCategory.TESTING
        if "setup" in norm_p or "install" in norm_p or "getting-started" in norm_p:
            return DocCategory.SETUP
        if "contribut" in norm_p or "workflow" in norm_p:
            return DocCategory.CONTRIBUTION
        if "subsystem" in norm_p or "component" in norm_p or "packages/" in norm_p:
            return DocCategory.COMPONENT

        return DocCategory.GENERAL


# =============================================================================
# 4. In-Memory Indexed Knowledge Graph
# =============================================================================

class KnowledgeGraph:
    """Deterministic in-memory indexed relationship graph for AntiOS.
    
    Zero external database dependencies. Represents and queries relationships
    between subsystems, components, tests, rules, skills, workflows, owners,
    and documentation.
    """

    def __init__(self):
        self._components: Dict[str, SubsystemDeclaration] = {}
        # Forward edges: source -> list of KnowledgeEdge
        self._forward_edges: Dict[str, List[KnowledgeEdge]] = {}
        # Reverse edges: target -> list of KnowledgeEdge
        self._reverse_edges: Dict[str, List[KnowledgeEdge]] = {}
        # Typed relationship index: (source, relation) -> list of targets
        self._typed_forward: Dict[Tuple[str, RelationshipType], List[KnowledgeEdge]] = {}
        self._typed_reverse: Dict[Tuple[str, RelationshipType], List[KnowledgeEdge]] = {}

    def add_component(self, decl: SubsystemDeclaration) -> None:
        """Registers a component/subsystem and derives canonical relationship edges."""
        sub_id = decl.subsystem_id.lower()
        self._components[sub_id] = decl

        # Ensure container keys exist
        if sub_id not in self._forward_edges:
            self._forward_edges[sub_id] = []
        if sub_id not in self._reverse_edges:
            self._reverse_edges[sub_id] = []

        # 1. Component -> DEPENDS_ON -> Dependency Subsystem
        for dep in decl.dependencies:
            dep_id = dep.lower()
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=dep_id,
                relation=RelationshipType.DEPENDS_ON,
                authority=KnowledgeEpistemicTier.OBSERVED if decl.epistemic_state == "OBSERVED" else KnowledgeEpistemicTier.INFERRED,
                rationale=f"Declared dependency of subsystem '{sub_id}'",
            ))

        # 2. Component -> CONSUMED_BY -> Consumer Subsystem
        for cons in decl.consumers:
            cons_id = cons.lower()
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=cons_id,
                relation=RelationshipType.CONSUMED_BY,
                authority=KnowledgeEpistemicTier.INFERRED,
                rationale=f"Declared consumer of subsystem '{sub_id}'",
            ))

        # 3. Component -> TESTED_BY -> Test Files
        for test_file in decl.covering_tests:
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=test_file,
                relation=RelationshipType.TESTED_BY,
                authority=KnowledgeEpistemicTier.OBSERVED,
                rationale=f"Covering test file for subsystem '{sub_id}'",
            ))

        # 4. Component -> GOVERNED_BY -> Rules
        for rule in decl.governing_rules:
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=rule,
                relation=RelationshipType.GOVERNED_BY,
                authority=KnowledgeEpistemicTier.OBSERVED,
                rationale=f"Governing invariant rule for subsystem '{sub_id}'",
            ))

        # 5. Component -> REQUIRES_SKILL -> Skills
        for skill in decl.applicable_skills:
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=skill,
                relation=RelationshipType.REQUIRES_SKILL,
                authority=KnowledgeEpistemicTier.INFERRED,
                rationale=f"Required engineering capability for subsystem '{sub_id}'",
            ))

        # 6. Component -> IMPLEMENTED_THROUGH -> Workflows
        for wf in decl.applicable_workflows:
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=wf,
                relation=RelationshipType.IMPLEMENTED_THROUGH,
                authority=KnowledgeEpistemicTier.INFERRED,
                rationale=f"Standard task execution workflow for subsystem '{sub_id}'",
            ))

        # 7. Component -> OWNED_BY -> Owner
        if decl.owner:
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=decl.owner,
                relation=RelationshipType.OWNED_BY,
                authority=KnowledgeEpistemicTier.OBSERVED if decl.owner_source == "CODEOWNERS" else KnowledgeEpistemicTier.INFERRED,
                confidence=decl.owner_confidence,
                rationale=f"Subsystem owner derived from {decl.owner_source}",
            ))

        # 8. Component -> DOCUMENTED_BY -> Documents
        for doc in decl.documentation_paths:
            self.add_edge(KnowledgeEdge(
                source=sub_id,
                target=doc,
                relation=RelationshipType.DOCUMENTED_BY,
                authority=KnowledgeEpistemicTier.OBSERVED,
                rationale=f"Reference documentation for subsystem '{sub_id}'",
            ))

    def add_edge(self, edge: KnowledgeEdge) -> None:
        """Adds a directed knowledge edge and indexes it."""
        # Forward
        self._forward_edges.setdefault(edge.source, []).append(edge)
        # Reverse
        self._reverse_edges.setdefault(edge.target, []).append(edge)

        # Typed indices
        t_fwd_key = (edge.source, edge.relation)
        self._typed_forward.setdefault(t_fwd_key, []).append(edge)

        t_rev_key = (edge.target, edge.relation)
        self._typed_reverse.setdefault(t_rev_key, []).append(edge)

    def get_component(self, component_id: str) -> Optional[SubsystemDeclaration]:
        """Retrieves a registered component declaration."""
        return self._components.get(component_id.lower())

    def list_components(self) -> List[SubsystemDeclaration]:
        """Lists all registered component declarations."""
        return list(self._components.values())

    def get_related(self, entity_id: str, relation: RelationshipType, direction: str = "forward") -> List[KnowledgeEdge]:
        """Queries typed edges for an entity in the specified direction."""
        key = (entity_id.lower(), relation)
        if direction == "forward":
            return list(self._typed_forward.get(key, []))
        return list(self._typed_reverse.get(key, []))

    def get_dependencies(self, component_id: str, transitive: bool = False) -> List[str]:
        """Returns direct or transitive dependencies of a component."""
        cid = component_id.lower()
        if not transitive:
            edges = self.get_related(cid, RelationshipType.DEPENDS_ON, direction="forward")
            return [e.target for e in edges]

        # Cycle-safe BFS traversal for transitive dependencies
        visited: Set[str] = set()
        queue: List[str] = [cid]
        results: List[str] = []

        while queue:
            curr = queue.pop(0)
            edges = self.get_related(curr, RelationshipType.DEPENDS_ON, direction="forward")
            for e in edges:
                target = e.target.lower()
                if target not in visited and target != cid:
                    visited.add(target)
                    results.append(target)
                    queue.append(target)

        return results

    def get_consumers(self, component_id: str, transitive: bool = False) -> List[str]:
        """Returns direct or transitive consumers of a component."""
        cid = component_id.lower()
        # Direct consumers from CONSUMED_BY forward edges or DEPENDS_ON reverse edges
        direct_consumers: Set[str] = set()
        for e in self.get_related(cid, RelationshipType.CONSUMED_BY, direction="forward"):
            direct_consumers.add(e.target.lower())
        for e in self.get_related(cid, RelationshipType.DEPENDS_ON, direction="reverse"):
            direct_consumers.add(e.source.lower())

        if not transitive:
            return sorted(list(direct_consumers))

        # Cycle-safe BFS for transitive consumers (Downstream Blast Radius)
        visited: Set[str] = set(direct_consumers)
        queue: List[str] = list(direct_consumers)
        results: List[str] = list(direct_consumers)

        while queue:
            curr = queue.pop(0)
            next_consumers: Set[str] = set()
            for e in self.get_related(curr, RelationshipType.CONSUMED_BY, direction="forward"):
                next_consumers.add(e.target.lower())
            for e in self.get_related(curr, RelationshipType.DEPENDS_ON, direction="reverse"):
                next_consumers.add(e.source.lower())

            for nc in next_consumers:
                if nc not in visited and nc != cid:
                    visited.add(nc)
                    results.append(nc)
                    queue.append(nc)

        return sorted(results)

    def calculate_blast_radius(self, component_id: str) -> Dict[str, Any]:
        """Computes comprehensive downstream blast radius for a component."""
        cid = component_id.lower()
        decl = self._components.get(cid)
        direct_cons = self.get_consumers(cid, transitive=False)
        transitive_cons = self.get_consumers(cid, transitive=True)

        # Collect covering tests across all affected components
        affected_tests: Set[str] = set()
        affected_commands: Set[str] = set()
        if decl:
            affected_tests.update(decl.covering_tests)
            affected_commands.update(decl.test_commands)

        for cons_id in transitive_cons:
            cons_decl = self._components.get(cons_id)
            if cons_decl:
                affected_tests.update(cons_decl.covering_tests)
                affected_commands.update(cons_decl.test_commands)

        # Calculate risk score
        total_consumers = len(transitive_cons)
        if total_consumers > 4 or (decl and decl.risk_tier == "CRITICAL"):
            risk_tier = "CRITICAL"
        elif total_consumers > 1 or (decl and decl.risk_tier == "HIGH"):
            risk_tier = "HIGH"
        elif total_consumers > 0 or (decl and decl.risk_tier == "MEDIUM"):
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        summary = (
            f"{risk_tier}: {len(direct_cons)} direct, {len(transitive_cons)} transitive consumers "
            f"({', '.join(transitive_cons[:3]) if transitive_cons else 'Leaf'})"
        )

        return {
            "component_id": cid,
            "risk_tier": risk_tier,
            "direct_consumers": direct_cons,
            "transitive_consumers": transitive_cons,
            "total_consumers_count": total_consumers,
            "affected_tests": sorted(list(affected_tests)),
            "affected_commands": sorted(list(affected_commands)),
            "blast_radius_summary": summary,
        }


# =============================================================================
# 5. Change-Intent Intelligence
# =============================================================================

@dataclass(frozen=True)
class ChangeIntent:
    """Detailed architectural impact assessment of planned code changes."""
    target_files: List[str]
    affected_subsystems: List[str]
    risk_tier: str                           # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    direct_consumers: List[str]
    transitive_consumers: List[str]
    applicable_skills: List[str]
    governing_rules: List[str]
    applicable_workflows: List[str]
    covering_tests: List[str]
    test_commands: List[str]
    required_verification: List[str]
    protected_invariants_at_risk: List[str]
    owners: List[str]
    blast_radius_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ChangeIntentAnalyzer:
    """Deterministic change-intent impact analyzer."""

    def __init__(self, knowledge_graph: KnowledgeGraph, path_resolver: Any):
        self.graph = knowledge_graph
        self.path_resolver = path_resolver

    def analyze_change(self, target_files: List[str]) -> ChangeIntent:
        """Evaluates the systemic blast radius and requirements for changing files."""
        if not target_files:
            return ChangeIntent(
                target_files=[],
                affected_subsystems=[],
                risk_tier="LOW",
                direct_consumers=[],
                transitive_consumers=[],
                applicable_skills=["antios-engineer"],
                governing_rules=[],
                applicable_workflows=["FEATURE"],
                covering_tests=[],
                test_commands=[],
                required_verification=["Working tree cleanliness check"],
                protected_invariants_at_risk=[],
                owners=[],
                blast_radius_summary="ISOLATED: Empty change set",
            )

        matched_sub_ids: Set[str] = set()
        for f in target_files:
            sub = self.path_resolver.resolve_file(f)
            if sub:
                matched_sub_ids.add(sub.matched_subsystem_id.lower())

        if not matched_sub_ids:
            # Files not mapped to any known subsystem
            return ChangeIntent(
                target_files=target_files,
                affected_subsystems=["UNKNOWN"],
                risk_tier="MEDIUM",
                direct_consumers=[],
                transitive_consumers=[],
                applicable_skills=["antios-engineer"],
                governing_rules=["Verify no breakage to unknown components"],
                applicable_workflows=["FEATURE", "BUG"],
                covering_tests=[],
                test_commands=[],
                required_verification=["Project root test runner", "Working tree cleanliness check"],
                protected_invariants_at_risk=[],
                owners=[],
                blast_radius_summary="UNKNOWN: Files belong outside registered subsystems",
            )

        # Aggregate across matched subsystems
        all_direct_consumers: Set[str] = set()
        all_transitive_consumers: Set[str] = set()
        all_skills: Set[str] = set()
        all_rules: Set[str] = set()
        all_workflows: Set[str] = set()
        all_tests: Set[str] = set()
        all_commands: Set[str] = set()
        all_invariants: Set[str] = set()
        all_owners: Set[str] = set()
        highest_risk = "LOW"
        risk_weights = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        for sub_id in matched_sub_ids:
            decl = self.graph.get_component(sub_id)
            blast = self.graph.calculate_blast_radius(sub_id)

            all_direct_consumers.update(blast["direct_consumers"])
            all_transitive_consumers.update(blast["transitive_consumers"])
            all_tests.update(blast["affected_tests"])
            all_commands.update(blast["affected_commands"])

            if risk_weights.get(blast["risk_tier"], 1) > risk_weights.get(highest_risk, 1):
                highest_risk = blast["risk_tier"]

            if decl:
                all_skills.update(decl.applicable_skills)
                all_rules.update(decl.governing_rules)
                all_workflows.update(decl.applicable_workflows)
                all_invariants.update(decl.protected_invariants)
                if decl.owner:
                    all_owners.add(decl.owner)

        # Determine verification requirements
        verification_steps: List[str] = ["Working tree cleanliness check", "Same Change Set audit"]
        if all_commands:
            verification_steps.append(f"Execute affected test runners: {'; '.join(sorted(all_commands)[:3])}")
        else:
            verification_steps.append("Execute default project test runner")

        if highest_risk in ("HIGH", "CRITICAL"):
            verification_steps.append("Independent Maker-Checker audit (fresh context)")
            verification_steps.append("Downstream consumer integration regression check")

        summary = (
            f"Risk: {highest_risk} | Subsystems: {', '.join(sorted(matched_sub_ids))} | "
            f"Consumers: {len(all_transitive_consumers)} transitive | Tests: {len(all_tests)} covering"
        )

        return ChangeIntent(
            target_files=list(target_files),
            affected_subsystems=sorted(list(matched_sub_ids)),
            risk_tier=highest_risk,
            direct_consumers=sorted(list(all_direct_consumers)),
            transitive_consumers=sorted(list(all_transitive_consumers)),
            applicable_skills=sorted(list(all_skills)) or ["antios-engineer"],
            governing_rules=sorted(list(all_rules)),
            applicable_workflows=sorted(list(all_workflows)) or ["FEATURE", "BUG"],
            covering_tests=sorted(list(all_tests)),
            test_commands=sorted(list(all_commands)),
            required_verification=verification_steps,
            protected_invariants_at_risk=sorted(list(all_invariants)),
            owners=sorted(list(all_owners)),
            blast_radius_summary=summary,
        )

    def format_change_intent_card(self, intent: ChangeIntent) -> str:
        """Renders a token-bounded (<= 25 lines) change intent impact card."""
        files_str = ", ".join(intent.target_files[:3])
        if len(intent.target_files) > 3:
            files_str += f" (+{len(intent.target_files) - 3} more)"

        sub_str = ", ".join(intent.affected_subsystems)
        cons_str = ", ".join(intent.transitive_consumers[:4]) if intent.transitive_consumers else "None (Leaf)"
        if len(intent.transitive_consumers) > 4:
            cons_str += f" (+{len(intent.transitive_consumers) - 4} more)"

        tests_str = ", ".join(intent.covering_tests[:3]) if intent.covering_tests else "Default runner"
        cmds_str = "; ".join(intent.test_commands[:2]) if intent.test_commands else "tests/run_all.py"
        skills_str = ", ".join(intent.applicable_skills[:2])
        rules_str = "; ".join(intent.governing_rules[:2]) if intent.governing_rules else "Standard project rules"
        verif_str = "; ".join(intent.required_verification[:2])

        card = [
            "=== ANTIOS CHANGE INTENT CARD ===",
            f"Target:       {files_str}",
            f"Subsystem:    {sub_str} [Risk: {intent.risk_tier}]",
            f"Blast Radius: {intent.blast_radius_summary}",
            f"Consumers:    {cons_str}",
            f"CoveringTests:{tests_str}",
            f"Runners:      {cmds_str}",
            f"Capabilities: Skills: {skills_str} | Workflows: {', '.join(intent.applicable_workflows[:2])}",
            f"Rules:        {rules_str}",
            f"Verification: {verif_str}",
            "==================================",
        ]
        return "\n".join(card)


# =============================================================================
# 6. Progressive Context Disclosure
# =============================================================================

class ProgressiveDisclosureLevel(int, Enum):
    """Layered context retrieval levels (L0 to L5)."""
    L0_PROJECT_IDENTITY = 0             # Project identity & high-level architecture
    L1_SUBSYSTEM_LOCATOR = 1            # Bounded subsystem locator card
    L2_COMPONENT_KNOWLEDGE = 2          # Detailed component & interface specifications
    L3_RELATIONSHIPS_AND_BLAST_RADIUS = 3 # Dependencies, consumers, and blast radius
    L4_CAPABILITIES = 4                 # Skills, rules, workflows, and verifiers
    L5_DETAILED_EVIDENCE = 5            # Complete manifest evidence & doc references

    # Short convenient aliases
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5


class ProgressiveDisclosureEngine:
    """Formats strictly bounded context cards according to requested depth."""

    @classmethod
    def render(
        cls,
        level: ProgressiveDisclosureLevel,
        data: Any,
        graph: Optional[KnowledgeGraph] = None,
    ) -> str:
        """Renders the appropriate context string for the specified disclosure level."""
        try:
            lvl = ProgressiveDisclosureLevel(level)
        except Exception:
            raise ValueError(f"Invalid progressive disclosure level: {level}")

        if lvl == ProgressiveDisclosureLevel.L0_PROJECT_IDENTITY:
            return cls._render_l0(data)
        elif lvl == ProgressiveDisclosureLevel.L1_SUBSYSTEM_LOCATOR:
            return cls._render_l1(data)
        elif lvl == ProgressiveDisclosureLevel.L2_COMPONENT_KNOWLEDGE:
            return cls._render_l2(data)
        elif lvl == ProgressiveDisclosureLevel.L3_RELATIONSHIPS_AND_BLAST_RADIUS:
            return cls._render_l3(data, graph)
        elif lvl == ProgressiveDisclosureLevel.L4_CAPABILITIES:
            return cls._render_l4(data)
        elif lvl == ProgressiveDisclosureLevel.L5_DETAILED_EVIDENCE:
            return cls._render_l5(data)
        return str(data)

    @classmethod
    def _render_l0(cls, project_info: Dict[str, Any]) -> str:
        """Level 0: Ultra-compact project identity (<= 5 lines)."""
        name = project_info.get("name", "Unknown-Project")
        arch = project_info.get("archetype", "standalone")
        subs = project_info.get("total_subsystems", 0)
        tech = project_info.get("primary_tech", "universal")
        return (
            f"[AntiOS L0 Project] Name: {name} | Archetype: {arch} | "
            f"Tech: {tech} | Subsystems: {subs}"
        )

    @classmethod
    def _render_l1(cls, resolution: Any) -> str:
        """Level 1: Subsystem locator card (<= 15 lines)."""
        ep_str = ", ".join(resolution.entrypoints[:2]) if resolution.entrypoints else "None"
        return "\n".join([
            "=== ANTIOS L1 LOCATOR ===",
            f"Subsystem:   {resolution.matched_subsystem_id} ({resolution.name}) [Area: {resolution.area}]",
            f"Description: {resolution.description}",
            f"Purpose:     {getattr(resolution, 'purpose', '') or resolution.description}",
            f"Entrypoints: {ep_str}",
            "==========================",
        ])

    @classmethod
    def _render_l2(cls, resolution: Any) -> str:
        """Level 2: Component knowledge (<= 20 lines)."""
        key_str = ", ".join(resolution.authoritative_files[:3]) if resolution.authoritative_files else "None"
        test_str = ", ".join(resolution.covering_tests[:2]) if resolution.covering_tests else "None"
        cmd_str = "; ".join(resolution.test_commands[:2]) if resolution.test_commands else "None"
        inv_str = ", ".join(resolution.protected_invariants[:2]) if resolution.protected_invariants else "None"

        return "\n".join([
            "=== ANTIOS L2 COMPONENT KNOWLEDGE ===",
            f"Component:    {resolution.matched_subsystem_id} ({resolution.name})",
            f"Area/Risk:    {resolution.area} | Risk: {getattr(resolution, 'risk_tier', 'MEDIUM')}",
            f"Key Files:    {key_str}",
            f"CoveringTests:{test_str}",
            f"TestRunners:  {cmd_str}",
            f"Invariants:   {inv_str}",
            "======================================",
        ])

    @classmethod
    def _render_l3(cls, resolution: Any, graph: Optional[KnowledgeGraph] = None) -> str:
        """Level 3: Relationships & blast radius (<= 25 lines)."""
        sub_id = resolution.matched_subsystem_id
        direct_cons = resolution.consumers
        trans_cons = graph.get_consumers(sub_id, transitive=True) if graph else direct_cons

        deps_str = ", ".join(resolution.dependencies) if resolution.dependencies else "None"
        cons_str = ", ".join(trans_cons[:4]) if trans_cons else "None (Leaf component)"

        return "\n".join([
            "=== ANTIOS L3 RELATIONSHIPS & BLAST RADIUS ===",
            f"Target:       {sub_id} ({resolution.name})",
            f"Depends On:   {deps_str}",
            f"Consumed By:  {cons_str}",
            f"Blast Radius: {resolution.blast_radius_summary}",
            f"Transitive:   {len(trans_cons)} downstream components affected",
            "==============================================",
        ])

    @classmethod
    def _render_l4(cls, resolution: Any) -> str:
        """Level 4: Capabilities, rules, and workflows (<= 25 lines)."""
        if hasattr(resolution, "format_card"):
            return resolution.format_card(max_lines=25)
        skills_str = ", ".join(resolution.applicable_skills) if hasattr(resolution, "applicable_skills") and resolution.applicable_skills else "antios-engineer"
        wf_str = ", ".join(resolution.applicable_workflows) if hasattr(resolution, "applicable_workflows") and resolution.applicable_workflows else "FEATURE"
        rules_str = "; ".join(resolution.governing_rules[:3]) if hasattr(resolution, "governing_rules") and resolution.governing_rules else "None specified"
        sub_id = getattr(resolution, "matched_subsystem_id", getattr(resolution, "subsystem_id", "UNKNOWN"))

        return "\n".join([
            "=== ANTIOS L4 CAPABILITIES & GOVERNANCE ===",
            f"Subsystem:    {sub_id}",
            f"Skills:       {skills_str}",
            f"Workflows:    {wf_str}",
            f"Rules:        {rules_str}",
            "Verification: Maker-Checker fresh context verification required on non-trivial diffs",
            "===========================================",
        ])

    @classmethod
    def _render_l5(cls, decl: Any) -> str:
        """Level 5: Exhaustive evidence & provenance."""
        import json
        if hasattr(decl, "to_dict"):
            data = decl.to_dict()
        elif isinstance(decl, dict):
            data = decl
        else:
            data = asdict(decl) if hasattr(decl, "__dataclass_fields__") else str(decl)
        return json.dumps(data, indent=2)
