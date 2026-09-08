"""AntiOS 2.0 Project-Specific Skill Generator.

Phase 57: Evidence-driven project-specific skill compilation.
Generates:
1. Primary entrypoint: `.agents/skills/antios/SKILL.md` (bounded <= 80 lines).
2. Project-specific specialist skills only when strictly justified by evidence.

Justification Criteria:
1. Capability is materially relevant (observed in anatomy/profile).
2. Not adequately covered by canonical skills (antios, antios-engineer, antios-debug, antios-verifier).
3. Contains meaningful project-specific knowledge (components, tokens, migrations).
4. Provides measurable value and reduces agent friction.
5. Does not duplicate or conflict with user-authored skills.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple

from framework.core.anatomy import ProjectAnatomy, ProjectArchetype


@dataclass
class SkillGenerationSpec:
    """Specification for an evidence-justified project skill."""
    name: str
    description: str
    purpose: str
    scope: List[str]
    triggers: List[str]
    project_evidence: List[str]
    authoritative_sources: List[str]
    allowed_operations: List[str]
    verification_expectations: List[str]
    related_specialist: Optional[str] = None


class SkillGenerator:
    """Evidence-driven generator for Antigravity-native project skills."""

    VERSION = "2.0.0"

    @classmethod
    def compile_main_skill(cls, anatomy: ProjectAnatomy) -> str:
        """Compiles the primary user-facing entrypoint (.agents/skills/antios/SKILL.md).
        
        Strictly respects token budget (<= 80 lines) and achieves complete runtime closure.
        """
        runners = anatomy.test_runners
        if runners:
            cmd_item = runners[0].get("command") or runners[0].get("default_command") or []
            primary_cmd = " ".join(cmd_item) if isinstance(cmd_item, list) else str(cmd_item)
        elif anatomy.archetype in ("FULLSTACK_WEB", "FRONTEND_WEB", "NODE_SERVICE"):
            primary_cmd = "npm test"
        elif anatomy.archetype == "RUST_SYSTEMS":
            primary_cmd = "cargo test"
        elif anatomy.archetype == "GO_SERVICE":
            primary_cmd = "go test ./..."
        elif anatomy.project_name in ("AntiOS-Universal-Self-Adapter", "AntiOS"):
            primary_cmd = "python tests/run_all.py"
        else:
            primary_cmd = "pytest"

        arch = anatomy.archetype
        roots = ", ".join(anatomy.source_roots[:3]) if anatomy.source_roots else "."
        tests = ", ".join(anatomy.test_roots[:2]) if anatomy.test_roots else "tests"

        lines = [
            "---",
            "name: antios",
            f"description: Universal project-native control plane for {anatomy.project_name} under AntiOS 2.0 governance.",
            "---",
            "",
            f"# {anatomy.project_name} — Project Operating Interface (`/antios`)",
            "",
            f"You are operating under **AntiOS 2.0 (Project Agent OS)** governance for `{anatomy.project_name}` ({arch}).",
            "This skill is your **single authoritative control plane** (`/antios`). Follow the canonical 9-step execution pipeline.",
            "",
            "## 1. Operating Axioms & Ground Rules",
            "- **Platform (Antigravity)**: Owns execution primitives (`invoke_subagent`, `manage_subagents`), tool transport, and planning mode.",
            "- **Project Instance**: Sovereign application governed by instance runtime (`.antios/`, `antios.config.json`).",
            "- **Protected Zones**: `.agents/`, `.antios/`, `antios.config.json`, `.git/` are strictly immutable.",
            f"- **Source Roots**: `{roots}` | **Test Roots**: `{tests}`",
            f"- **Primary Test Command**: `{primary_cmd}` (must exit code 0 before completing turn).",
            "- **Single Authority**: Physical manifests and test suite ground truth supersede prose.",
            "",
            "## 2. Canonical 9-Step Dispatch Pipeline",
            "1. `UNDERSTAND`: Clarify user objective, scope, constraints, and non-goals.",
            "2. `CHECK STATE`: Read `.antios/knowledge.json` and `docs/ACTIVE_CONTEXT.md` (must be <= 60 lines).",
            "3. `LOCATE`: Query wayfinding via `python .antios/runtime/inspect_instance.py --query \"<query>\"` or native search (`grep_search`, `find_by_name`).",
            "4. `CLASSIFY`: Classify TaskClass (`FEATURE`|`BUG`|`REFACTOR`|`INVESTIGATION`|`DOCS`|`RELEASE`) and RiskTier.",
            "5. `SELECT WORKFORCE`: Sizing: SOLO (0 workers), FOCUSED (1 specialist), SMALL/PARALLEL (2–4 workers), STAGED.",
            "   - Hard Limits: <= 10 active subagents per wave, <= 20 lifetime launches per mission, depth <= 2.",
            "6. `EXECUTE`: Single controlled writer default. Parallel writes require disjoint paths and `Workspace='branch'`.",
            f"7. `VERIFY`: Run physical test suite (`{primary_cmd}`). On High-Risk tasks, dispatch independent Checker.",
            "8. `STOP GATE`: Confirms zero git conflict markers and clean test pass (exit 0) before turn completion.",
            "9. `REMEMBER`: Record lessons in `docs/ACTIVE_CONTEXT.md` and `.antios/learning_observations.json`.",
            "",
            "## 3. Internal Specialist Procedures (Selected by /antios)",
            "- **Feature Engineering & Refactoring**: Locate subsystem -> plan surgical edits -> verify clean diff -> Same Change Set docs.",
            "- **Root-Cause Debugging**: Reproduce failure with covering test -> formulate hypothesis -> minimal patch -> verify test exit 0.",
            "- **Independent Verification (Maker-Checker)**: Dispatch fresh-context Checker via `invoke_subagent(TypeName='self')`. Checker audits diff, runs test suite, verifies zero regressions, and emits structured JSON verdict:",
            f'  `{{"status": "PASS"|"FAIL", "tests": [{{"command": "{primary_cmd}", "exit_code": 0}}], "summary": "..."}}`.',
            "",
            "## 4. Tool Tier Preference",
            "`NATIVE (1) -> SCRIPT (2) -> PROJECT (3) -> EXTERNAL (4) -> SERVICE (5) -> MCP (6)`",
            "",
            "AntiOS operates natively within Antigravity. Execute tasks cleanly with minimum context friction.",
        ]
        content = "\n".join(lines)
        return content

    @classmethod
    def evaluate_skill_justification(
        cls, anatomy: ProjectAnatomy, existing_skills: Optional[List[str]] = None
    ) -> List[SkillGenerationSpec]:
        """Evaluates whether project-specific specialist skills are justified by evidence.
        
        Refuses generation if:
        - Technology exists without dedicated architectural subsystem.
        - Existing user-authored or canonical skill already covers the capability.
        """
        existing = set(existing_skills or [])
        specs: List[SkillGenerationSpec] = []

        # 1. Frontend / Design System Skill Justification
        # Requires: Frontend framework + (components dir or design tokens or styles dir)
        has_frontend = any(f.lower() in ["react", "vue", "svelte", "next", "vite", "angular"] for f in anatomy.frameworks)
        has_ui_dirs = any(d in anatomy.important_directories for d in ["components", "styles", "views", "pages"])
        if has_frontend and has_ui_dirs:
            skill_name = "frontend-design"
            if skill_name not in existing and "frontend" not in existing and "design-system" not in existing:
                fe_cmd = "npm test"
                if anatomy.test_runners:
                    c = anatomy.test_runners[0].get("command", [])
                    fe_cmd = " ".join(c) if isinstance(c, list) else str(c)
                for m in anatomy.package_manifests:
                    scripts = m.get("declared_scripts", {})
                    if "test" in scripts and "vitest" in scripts["test"]:
                        fe_cmd = f"{fe_cmd} ({scripts['test']})"
                        break
                specs.append(SkillGenerationSpec(
                    name=skill_name,
                    description=f"Project-specific UI component and design token guidance for {anatomy.project_name}.",
                    purpose=f"Governs modifications to UI components, style tokens, and frontend views in {anatomy.project_name}.",
                    scope=["components/", "styles/", "pages/", "views/"],
                    triggers=["modify UI component", "update styles", "add design token", "frontend view change"],
                    project_evidence=[
                        f"Frontend frameworks: {anatomy.frameworks}",
                        f"UI directories witnessed: {[d for d in anatomy.important_directories if d in ['components', 'styles', 'views', 'pages']]}",
                    ],
                    authoritative_sources=["components/", "styles/"],
                    allowed_operations=["Edit component files", "Update CSS/Tailwind classes", "Execute component tests"],
                    verification_expectations=[
                        f"Run frontend tests: {fe_cmd}",
                        "Verify no visual or responsive regressions",
                    ],
                    related_specialist="frontend-specialist",
                ))

        # 2. Database / Migration Skill Justification
        # Requires: migrations/ directory or prisma/sqlx/alembic in configs
        has_migrations = "migrations" in anatomy.important_directories or any("migration" in d for d in anatomy.important_directories)
        has_db_config = any("prisma" in c or "alembic" in c or "sql" in c for c in anatomy.configuration_surfaces)
        if has_migrations or has_db_config:
            skill_name = "database-migrations"
            if skill_name not in existing and "database" not in existing and "db" not in existing:
                specs.append(SkillGenerationSpec(
                    name=skill_name,
                    description=f"Database schema and migration safety guidance for {anatomy.project_name}.",
                    purpose=f"Ensures safe database schema migrations and query invariants in {anatomy.project_name}.",
                    scope=["migrations/", "models/", "schema/"],
                    triggers=["database migration", "schema change", "alter table", "update ORM models"],
                    project_evidence=[
                        f"Migration directories witnessed: {[d for d in anatomy.important_directories if 'migration' in d]}",
                        f"Database configs witnessed: {[c for c in anatomy.configuration_surfaces if any(k in c for k in ['prisma', 'alembic', 'sql'])]}",
                    ],
                    authoritative_sources=["migrations/", "models/"],
                    allowed_operations=["Generate migration files", "Validate schema constraints", "Execute db tests"],
                    verification_expectations=["Verify forward and rollback migration integrity", "Run test suite"],
                    related_specialist="database-specialist",
                ))

        return specs

    @classmethod
    def generate_skill_content(cls, spec: SkillGenerationSpec, anatomy: ProjectAnatomy) -> str:
        """Renders an Antigravity-native skill markdown file from a specification.
        
        Strictly concise (< 70 lines).
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        lines = [
            "---",
            f"name: {spec.name}",
            f"description: {spec.description}",
            "---",
            "",
            f"# {spec.name.title()} Skill",
            "",
            f"**Purpose**: {spec.purpose}",
            "",
            "## 1. Scope & Boundaries",
            f"- **Governed Paths**: {', '.join(spec.scope)}",
            f"- **Triggers**: {', '.join(spec.triggers)}",
            "",
            "## 2. Project Evidence",
        ]
        for ev in spec.project_evidence:
            lines.append(f"- {ev}")

        lines.extend([
            "",
            "## 3. Authoritative Sources",
            f"- {', '.join(spec.authoritative_sources)}",
            "",
            "## 4. Allowed Operations",
        ])
        for op in spec.allowed_operations:
            lines.append(f"- {op}")

        lines.extend([
            "",
            "## 5. Verification Expectations",
        ])
        for ve in spec.verification_expectations:
            lines.append(f"- {ve}")

        lines.extend([
            "",
            "## 6. Provenance & Lifecycle",
            f"- **Generator**: AntiOS SkillGenerator v{cls.VERSION}",
            f"- **Generated At**: {now_ts}",
            f"- **Manifest Fingerprint**: {anatomy.manifest_fingerprint[:16]}...",
            "- **Regenerable**: Yes (re-evaluated during project adaptation)",
        ])

        return "\n".join(lines)
