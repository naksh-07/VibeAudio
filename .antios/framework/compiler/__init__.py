"""
AntiOS 3.0 Project Environment Compiler

Static compiler package for building compact, deterministic, agent-native project environments.
"""

from .ast_extractor import ASTSymbolExtractor, ClassSymbol, FileSymbolOutline, FunctionSymbol, MethodSymbol
from .compiler import CompilationResult, ProjectEnvironmentCompiler, compile_project
from .emit import CANONICAL_SIGNATURE, ArtifactEmitter, EmissionRecord
from .project_model import Confidence, DiscoveredSignal, ProjectInspector, ProjectModel, SignalKind, SubsystemCandidate
from .routes import RouteMapGenerator

__all__ = [
    "ProjectEnvironmentCompiler",
    "compile_project",
    "CompilationResult",
    "ProjectModel",
    "ProjectInspector",
    "RouteMapGenerator",
    "ASTSymbolExtractor",
    "ArtifactEmitter",
    "EmissionRecord",
    "CANONICAL_SIGNATURE",
    "SignalKind",
    "Confidence",
    "DiscoveredSignal",
    "SubsystemCandidate",
    "FileSymbolOutline",
    "ClassSymbol",
    "FunctionSymbol",
    "MethodSymbol",
]
