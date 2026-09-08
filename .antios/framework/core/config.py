"""AntiOS Adapter Configuration Loader.

Decouples generic AntiOS governance mechanisms from project-specific domains.
Operates as a 100% domain-agnostic Universal Core.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from typing import Any, Dict, List, Optional

from framework.core.changeset import ChangesetPolicy


@dataclass
class RunnerConfig:
    name: str
    manifest: str = ""
    scripts: List[str] = field(default_factory=list)
    default_command: List[str] = field(default_factory=list)
    timeout_seconds: int = 60
    cwd: Optional[str] = None
    required: bool = True
    scope: str = "workspace"
    member: Optional[str] = None
    __test__: bool = False


# Alias for backward compatibility
TestRunnerConfig = RunnerConfig


@dataclass
class PoliciesConfig:
    fail_closed: bool = True
    enforce_working_tree_cleanliness: bool = True
    enforce_same_change_set: bool = True


@dataclass
class AntiOSConfig:
    version: str = "1.0"
    name: str = "AntiOS-Universal-Core"
    protected_zones: List[str] = field(default_factory=lambda: [".agents", "framework"])
    protected_domain_paths: List[str] = field(default_factory=list)
    forbidden_patterns: List[str] = field(default_factory=list)
    test_runners: List[RunnerConfig] = field(default_factory=list)
    linters: List[Dict[str, Any]] = field(default_factory=list)
    policies: PoliciesConfig = field(default_factory=PoliciesConfig)
    changeset: ChangesetPolicy = field(default_factory=ChangesetPolicy)
    manifest_fingerprint: str = ""
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    agent_topology: Dict[str, Any] = field(default_factory=dict)
    data_dir: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.policies, dict):
            self.policies = PoliciesConfig(**self.policies)
        if isinstance(self.changeset, dict):
            self.changeset = ChangesetPolicy(**self.changeset)


def load_config(repo_root: Optional[str] = None) -> AntiOSConfig:
    """Load antios.config.json from repo_root, falling back to secure universal defaults."""
    if not repo_root:
        repo_root = os.getcwd()

    config_path = os.path.join(repo_root, "antios.config.json")
    if not os.path.isfile(config_path):
        return AntiOSConfig()

    try:
        with open(config_path, "r", encoding="utf-8-sig") as f:
            data: Dict[str, Any] = json.load(f)

        test_runners = []
        for tr in data.get("test_runners", []):
            cmd = tr.get("default_command") or tr.get("command") or []
            test_runners.append(
                RunnerConfig(
                    name=tr.get("name", "unknown"),
                    manifest=tr.get("manifest", ""),
                    scripts=tr.get("scripts", []),
                    default_command=cmd,
                    timeout_seconds=tr.get("timeout_seconds", 60),
                    cwd=tr.get("cwd"),
                    required=tr.get("required", True),
                    scope=tr.get("scope", "workspace"),
                    member=tr.get("member"),
                )
            )

        raw_policies = data.get("policies", {})
        policies = PoliciesConfig(
            fail_closed=raw_policies.get("fail_closed", data.get("fail_closed", True)),
            enforce_working_tree_cleanliness=raw_policies.get("enforce_working_tree_cleanliness", True),
            enforce_same_change_set=raw_policies.get("enforce_same_change_set", True),
        )

        raw_cs = data.get("same_change_set", {})
        cs_policy = ChangesetPolicy(
            enabled=raw_cs.get("enabled", policies.enforce_same_change_set),
            code_patterns=raw_cs.get("code_patterns", ChangesetPolicy().code_patterns),
            doc_patterns=raw_cs.get("doc_patterns", ChangesetPolicy().doc_patterns),
            test_patterns=raw_cs.get("test_patterns", ChangesetPolicy().test_patterns),
            state_patterns=raw_cs.get("state_patterns", ChangesetPolicy().state_patterns),
            require_tests_on_code_change=raw_cs.get("require_tests_on_code_change", True),
            require_docs_on_code_change=raw_cs.get("require_docs_on_code_change", False),
            require_state_on_code_change=raw_cs.get("require_state_on_code_change", False),
        )

        return AntiOSConfig(
            version=data.get("version", "1.0"),
            name=data.get("name", "AntiOS-Adapter"),
            protected_zones=data.get("protected_zones", [".agents", "framework"]),
            protected_domain_paths=data.get("protected_domain_paths", []),
            forbidden_patterns=data.get("forbidden_patterns", []),
            test_runners=test_runners,
            linters=data.get("linters", []),
            policies=policies,
            changeset=cs_policy,
            manifest_fingerprint=data.get("manifest_fingerprint", ""),
            components=data.get("components", {}),
            capabilities=data.get("capabilities", {}),
            agent_topology=data.get("agent_topology", {}),
            data_dir=data.get("data_dir"),
        )
    except Exception:
        return AntiOSConfig()
