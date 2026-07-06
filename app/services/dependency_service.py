"""Fachada de verificação de dependências para a camada de UI (Seção 12).

A lógica de sondagem vive em app.infrastructure.dependency_checker; este
módulo expõe a API estável consumida pelas views e por módulos futuros.
"""

from __future__ import annotations

from app.infrastructure.dependency_checker import (
    DEPENDENCIES,
    Criticality,
    DependencySpec,
    DependencyStatus,
    ModuleReport,
    check_all,
    check_dependency,
)

__all__ = [
    "DEPENDENCIES",
    "Criticality",
    "DependencySpec",
    "DependencyStatus",
    "ModuleReport",
    "check_all",
    "check_dependency",
]
