"""
Cliente Supabase para buscar pedidos novos e marcar como impresso.
URL e chave configuradas diretamente aqui.
"""
import urllib.request
import urllib.parse
import urllib.error
import json

SUPABASE_URL = "https://wihqlysyfdcakmuirdeu.supabase.co"
SUPABASE_KEY = "sb_publishable_bAoTS-Y_ooiKEZ9rKD1Dow__FeFlUhK"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}


def _request(method, path, body=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        print(f"[Supabase] HTTP {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"[Supabase] Erro: {e}")
        return None


def buscar_pedidos_novos():
    """
    Busca pedidos com status='novo' e impresso=false.
    Retorna lista ordenada por created_at.
    """
    params = "pedidos?status=eq.novo&impresso=eq.false&order=created_at.asc&select=*"
    resultado = _request("GET", params)
    if resultado is None:
        return []
    return resultado


def marcar_como_impresso(pedido_id):
    """
    Marca pedido como impresso no banco.
    """
    path = f"pedidos?id=eq.{pedido_id}"
    resultado = _request("PATCH", path, {"impresso": True})
    return resultado is not None


def testar_conexao():
    """
    Testa conectividade com Supabase.
    Retorna True se OK, False se falhou.
    """
    result = _request("GET", "pedidos?select=id&limit=1")
    return result is not None
