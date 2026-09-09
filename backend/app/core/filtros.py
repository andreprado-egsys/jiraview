# egSYS JiraView — Filtros personalizados do gestor (persistência local, por usuário/estado)
import json
import os
from pathlib import Path

_DATA = Path(os.environ.get("JIRAVIEW_DATA", Path(__file__).parent.parent.parent.parent / "data"))


class FiltroRepo:
    """Persiste filtros JQL personalizados por (gestor, estado) em data/filtros.json
    chmod 600 — sem credencial, sem exposição ao cliente."""

    def __init__(self):
        _DATA.mkdir(parents=True, exist_ok=True)
        self._file = _DATA / "filtros.json"

    def _load(self) -> dict:
        if not self._file.exists():
            return {}
        try:
            return json.loads(self._file.read_text())
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        try:
            os.chmod(self._file, 0o600)
        except OSError:
            pass

    def listar(self, user: str, estado: str) -> list[dict]:
        return self._load().get(user, {}).get(estado, [])

    def salvar(self, user: str, estado: str, filtro: dict) -> dict:
        data = self._load()
        filtros = data.setdefault(user, {}).setdefault(estado, [])
        fid = filtro.get("id") or f"f{len(filtros)+1}"
        filtro["id"] = fid
        filtros = [f for f in filtros if f.get("id") != fid]
        filtros.append(filtro)
        data[user][estado] = filtros
        self._save(data)
        return {"ok": True, "filtro": filtro}

    def apagar(self, user: str, estado: str, fid: str) -> dict:
        data = self._load()
        filtros = data.get(user, {}).get(estado, [])
        data[user][estado] = [f for f in filtros if f.get("id") != fid]
        self._save(data)
        return {"ok": True}
