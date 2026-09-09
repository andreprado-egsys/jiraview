# Carregador de estados (config interna do ÚNICO container)
# Multi-estado = dados em runtime, nunca múltiplos serviços/containers.
import os
from functools import lru_cache
from typing import Optional

import yaml

_ESTADOS_PATH = os.environ.get(
    "JIRAVIEW_ESTADOS", os.path.join(os.path.dirname(__file__), "..", "..", "..", "deploy", "estados.yaml")
)


@lru_cache
def carregar_estados() -> dict:
    with open(os.path.abspath(_ESTADOS_PATH)) as f:
        data = yaml.safe_load(f)
    return data.get("estados", {})


def estado_por_sigla(sigla: str) -> Optional[dict]:
    return carregar_estados().get(sigla.lower())


def projeto_em_estado(projeto: str) -> list[str]:
    """Retorna as siglas de estados que incluem o projeto passado."""
    out = []
    for sigla, cfg in carregar_estados().items():
        if projeto.upper() in [p.upper() for p in cfg.get("projects", [])]:
            out.append(sigla)
    return out


def clientes_do_estado(sigla: str) -> list[dict]:
    return (carregar_estados().get(sigla.lower()) or {}).get("clientes", [])
