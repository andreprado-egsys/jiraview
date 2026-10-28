from backend.app.core.cache import TTLCache


class RelogioFalso:
    def __init__(self) -> None:
        self.agora = 0.0

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


def test_miss_retorna_none():
    cache = TTLCache(ttl=5.0, now=RelogioFalso())
    assert cache.get("analise_dev") is None


def test_hit_dentro_do_ttl():
    relogio = RelogioFalso()
    cache = TTLCache(ttl=5.0, now=relogio)
    cache.set("analise_dev", {"total": 3})
    relogio.avancar(4.9)
    assert cache.get("analise_dev") == {"total": 3}


def test_expiracao_apos_ttl_remove_chave():
    relogio = RelogioFalso()
    cache = TTLCache(ttl=5.0, now=relogio)
    cache.set("cert", {"resumo": {}})
    relogio.avancar(5.0)
    assert cache.get("cert") is None
    assert cache._store == {}


def test_set_reescreve_valor_e_renova_ttl():
    relogio = RelogioFalso()
    cache = TTLCache(ttl=5.0, now=relogio)
    cache.set("triagem_n1n2", {"total": 1})
    relogio.avancar(3.0)
    cache.set("triagem_n1n2", {"total": 2})
    relogio.avancar(2.9)
    assert cache.get("triagem_n1n2") == {"total": 2}


def test_ttl_padrao_e_positivo():
    relogio = RelogioFalso()
    cache = TTLCache(now=relogio)
    cache.set("k", 1)
    assert cache.get("k") == 1
    relogio.avancar(5.0)
    assert cache.get("k") is None
