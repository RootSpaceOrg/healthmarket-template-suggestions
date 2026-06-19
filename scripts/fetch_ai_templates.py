#!/usr/bin/env python3
"""
Busca templates AI publicados no Supabase (ambiente prod por padrao) e retorna
uma amostra ALEATORIA para servir de base para novas sugestoes.

Filtros aplicados (conforme pedido):
    template_type = ai
    status        = published

Credenciais do Supabase vem do AWS SSM Parameter Store:
    /default/supabase-database-credentials   (JSON com url + key)

Retorna JSON em stdout: lista de {id, name, description}. A description e o
contexto que a IA usa para escrever a copy final da nova sugestao.

Uso:
    python scripts/fetch_ai_templates.py --count 5
    python scripts/fetch_ai_templates.py --count 5 --env prod
    python scripts/fetch_ai_templates.py --all          # devolve todos (sem amostrar)
"""

import argparse
import json
import random
import sys
import urllib.parse
import urllib.request

from aws_auth import AWS_REGION, get_session

PARAMETER_NAME = "/default/supabase-database-credentials"
# Supabase rejeita secret keys quando o request parece vir de browser.
# urllib ja nao manda UA de browser, mas fixamos um UA neutro por garantia.
HTTP_HEADERS_UA = "kultivai-template-suggester/1.0"


def _err(msg, code=1):
    sys.stdout.write(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.exit(code)


def load_supabase_credentials(session):
    ssm = session.client("ssm", region_name=AWS_REGION)
    raw = ssm.get_parameter(Name=PARAMETER_NAME, WithDecryption=True)["Parameter"]["Value"]
    data = json.loads(raw)
    url = data.get("url") or data.get("supabaseUrl") or data.get("SUPABASE_URL")
    key = (
        data.get("key")
        or data.get("anonKey")
        or data.get("publishableKey")
        or data.get("apiKey")
        or data.get("SUPABASE_ANON_KEY")
        or data.get("SUPABASE_PUBLISHABLE_KEY")
    )
    if not url or not key:
        _err(f"Credenciais incompletas em '{PARAMETER_NAME}'")
    return url.rstrip("/"), key


def fetch_templates(supabase_url, key):
    query = {
        "select": "id,name,description,business_type",
        "template_type": "eq.ai",
        "status": "eq.published",
    }
    req = urllib.request.Request(
        f"{supabase_url}/rest/v1/templates?{urllib.parse.urlencode(query)}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": HTTP_HEADERS_UA,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        rows = json.loads(res.read().decode("utf-8"))
    if not isinstance(rows, list):
        _err("Resposta inesperada do Supabase")
    out = []
    for t in rows:
        if not t.get("id") or not t.get("description"):
            continue
        out.append(
            {
                "id": t["id"],
                "name": t.get("name") or "Template sem nome",
                "description": str(t["description"]).strip(),
                "businessType": t.get("business_type") or "",
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser(description="Busca templates AI publicados (amostra aleatoria)")
    ap.add_argument("--count", type=int, default=5, help="quantos templates base retornar (amostra aleatoria)")
    ap.add_argument("--all", action="store_true", help="retorna todos, sem amostrar")
    ap.add_argument("--env", default="prod", choices=["prod", "dev"], help="ambiente AWS (default: prod)")
    ap.add_argument("--seed", type=int, help="seed opcional para amostragem reproduzivel")
    args = ap.parse_args()

    try:
        session = get_session(args.env)
        url, key = load_supabase_credentials(session)
        templates = fetch_templates(url, key)
    except Exception as exc:  # noqa: BLE001
        _err(f"{type(exc).__name__}: {exc}")

    if not templates:
        _err(
            "Nenhum template AI publicado encontrado no Supabase "
            "(template_type=ai, status=published).",
            code=2,
        )

    if args.all:
        sample = templates
    else:
        if args.seed is not None:
            random.seed(args.seed)
        n = max(1, min(args.count, len(templates)))
        # amostra aleatoria SEM repeticao quando ha templates suficientes
        sample = random.sample(templates, n)

    sys.stdout.write(
        json.dumps(
            {"ok": True, "env": args.env, "totalAvailable": len(templates), "templates": sample},
            ensure_ascii=False,
            indent=2,
        )
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
