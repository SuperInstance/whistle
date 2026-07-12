"""
Whistle — Intent DSL for Working Animal Architecture.

Public API:
    parse(source)     -> WhistleProgram
    compile(program)  -> dict
    validate(program) -> ValidationResult
"""

from .parser import parse, WhistleProgram, WhistleStatement
from .compiler import compile as compile_program, CompiledConfig
from .validator import validate, ValidationResult

__version__ = "0.1.0"
__all__ = [
    "parse",
    "compile_program",
    "compile",
    "validate",
    "WhistleProgram",
    "WhistleStatement",
    "CompiledConfig",
    "ValidationResult",
]

# Convenience alias so `from whistle import compile` works naturally.
compile = compile_program
