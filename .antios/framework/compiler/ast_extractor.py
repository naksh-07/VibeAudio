"""
AntiOS 3.0 Project Environment Compiler — AST Symbol Outline Extractor

Extracts exact class, function, and method outlines with 1-indexed line ranges using the
Python standard library `ast` module.
Guarantees: Zero third-party dependencies, no synthetic AST fabrication for unsupported languages.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MethodSymbol:
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    signature: str = ""
    is_async: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "is_async": self.is_async,
        }


@dataclass
class ClassSymbol:
    name: str
    start_line: int
    end_line: int
    docstring: str = ""
    bases: List[str] = field(default_factory=list)
    methods: List[MethodSymbol] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "bases": self.bases,
            "methods": [m.to_dict() for m in self.methods],
        }


@dataclass
class FunctionSymbol:
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    signature: str = ""
    is_async: bool = False
    docstring: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "is_async": self.is_async,
            "docstring": self.docstring,
        }


@dataclass
class FileSymbolOutline:
    path: str  # POSIX relative path
    language: str
    extractor: str  # "python_ast" or "unsupported"
    confidence: float
    classes: List[ClassSymbol] = field(default_factory=list)
    functions: List[FunctionSymbol] = field(default_factory=list)
    parse_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "path": self.path,
            "language": self.language,
            "extractor": self.extractor,
            "confidence": self.confidence,
            "classes": [c.to_dict() for c in self.classes],
            "functions": [f.to_dict() for f in self.functions],
        }
        if self.parse_error:
            result["parse_error"] = self.parse_error
        return result


def _format_arg(arg: ast.arg) -> str:
    """Format an ast.arg with type annotation if present."""
    if arg.annotation is not None:
        try:
            return f"{arg.arg}: {ast.unparse(arg.annotation)}"
        except Exception:
            return arg.arg
    return arg.arg


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a human-readable argument signature from ast function definition."""
    try:
        args_list = []
        # positional-only args
        for a in getattr(node.args, "posonlyargs", []):
            args_list.append(_format_arg(a))
        if getattr(node.args, "posonlyargs", []):
            args_list.append("/")
        # standard args
        for a in node.args.args:
            args_list.append(_format_arg(a))
        # vararg *args
        if node.args.vararg:
            args_list.append(f"*{_format_arg(node.args.vararg)}")
        elif node.args.kwonlyargs:
            args_list.append("*")
        # kwonly args
        for a in node.args.kwonlyargs:
            args_list.append(_format_arg(a))
        # kwarg **kwargs
        if node.args.kwarg:
            args_list.append(f"**{_format_arg(node.args.kwarg)}")

        sig = f"{node.name}({', '.join(args_list)})"
        if node.returns:
            try:
                sig += f" -> {ast.unparse(node.returns)}"
            except Exception:
                pass
        return sig
    except Exception:
        return f"{node.name}(...)"


class ASTSymbolExtractor:
    """
    Zero-dependency AST extractor for Python source files.
    For non-Python files, explicitly yields unsupported metadata without fabrication.
    """

    @staticmethod
    def extract_file(filepath: Path, rel_posix_path: str) -> FileSymbolOutline:
        suffix = filepath.suffix.lower()
        if suffix != ".py":
            # Unsupported language: explicitly report without pretending to have AST precision
            lang = "unsupported"
            if suffix in (".ts", ".tsx"):
                lang = "typescript"
            elif suffix in (".js", ".jsx", ".mjs"):
                lang = "javascript"
            elif suffix == ".rs":
                lang = "rust"
            elif suffix == ".go":
                lang = "go"
            return FileSymbolOutline(
                path=rel_posix_path,
                language=lang,
                extractor="unsupported",
                confidence=0.0,
            )

        # Python AST parsing
        try:
            source = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                source = filepath.read_text(encoding="latin-1")
            except Exception as e:
                return FileSymbolOutline(
                    path=rel_posix_path,
                    language="python",
                    extractor="python_ast",
                    confidence=0.0,
                    parse_error=f"DecodeError: {e}",
                )
        except OSError as e:
            return FileSymbolOutline(
                path=rel_posix_path,
                language="python",
                extractor="python_ast",
                confidence=0.0,
                parse_error=f"IOError: {e}",
            )

        try:
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError as e:
            return FileSymbolOutline(
                path=rel_posix_path,
                language="python",
                extractor="python_ast",
                confidence=0.0,
                parse_error=f"SyntaxError at line {e.lineno}: {e.msg}",
            )

        classes: List[ClassSymbol] = []
        functions: List[FunctionSymbol] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                doc_summary = doc.strip().split("\n")[0][:100] if doc else ""
                bases: List[str] = []
                for b in node.bases:
                    try:
                        bases.append(ast.unparse(b))
                    except Exception:
                        if isinstance(b, ast.Name):
                            bases.append(b.id)

                methods: List[MethodSymbol] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(
                            MethodSymbol(
                                name=item.name,
                                qualified_name=f"{node.name}.{item.name}",
                                start_line=item.lineno,
                                end_line=getattr(item, "end_lineno", item.lineno),
                                signature=_format_signature(item),
                                is_async=isinstance(item, ast.AsyncFunctionDef),
                            )
                        )

                classes.append(
                    ClassSymbol(
                        name=node.name,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        docstring=doc_summary,
                        bases=bases,
                        methods=methods,
                    )
                )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                doc_summary = doc.strip().split("\n")[0][:100] if doc else ""
                functions.append(
                    FunctionSymbol(
                        name=node.name,
                        qualified_name=node.name,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        signature=_format_signature(node),
                        is_async=isinstance(node, ast.AsyncFunctionDef),
                        docstring=doc_summary,
                    )
                )

        return FileSymbolOutline(
            path=rel_posix_path,
            language="python",
            extractor="python_ast",
            confidence=1.0,
            classes=classes,
            functions=functions,
        )
