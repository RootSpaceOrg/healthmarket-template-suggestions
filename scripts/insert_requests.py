#!/usr/bin/env python3
"""
Insere sugestoes (copies geradas pela IA) chamando a Lambda `ai-requests-manager`
(mesmo caminho do POST /ai_requests da API), com `executeOnCreate: true` para
que cada item ja dispare a fase de planejamento (idea-to-brief) e apareca como
`plan_review` na tela de request-workflow do frontend.

A IA (skill) e responsavel por ESCREVER a copy. Este script so faz I/O: recebe
um JSON com a lista de sugestoes, monta um evento API-Gateway-proxy e invoca a
Lambda diretamente (lambda:InvokeFunction). Assim toda a logica de negocio
(criacao + start da Step Function idea-to-brief) e reaproveitada do backend.

> Por que invocar a Lambda em vez de gravar no DynamoDB?
> `executeOnCreate` so e honrado pela Lambda (create_single_request ->
> start_generation_workflow). Um put_item direto na tabela NAO dispara nada.

Cada item enviado (CreateAIRequestModel):
    idea, templateId, businessType, copyTone, imageStyle, copyLLM, imageLLM
tenantId / verticalId / ownerUserId vao no authorizer (requestContext), pois o
backend os le de la (nunca do body) e ignora se vierem no item.

Entrada (--input arquivo.json OU stdin):
{
  "tenantId": "kultivai",
  "verticalId": "health",
  "businessType": "Laserterapia",          # LABEL do tenantConfig (frontend exibe o label)
  "ownerUserId": "gustavo.reis20000@gmail.com",
  "createdBy": "Template Suggester (AI)",
  "suggestions": [
    {
      "idea": "<copy final escrita pela IA>",
      "templateId": "<id do template AI base no Supabase>",
      "copyTone": "inspiracional",
      "imageStyle": "fotorrealista"
    }
  ]
}

Campos opcionais por sugestao sobrescrevem os defaults do topo
(businessType, copyTone, imageStyle). copyLLM/imageLLM usam os defaults do env
salvos abaixo, a menos que venham no JSON.

Uso:
    python scripts/insert_requests.py --input batch.json
    python scripts/insert_requests.py --input batch.json --env prod
    python scripts/insert_requests.py --input batch.json --no-execute   # cria sem disparar
    python scripts/insert_requests.py --input batch.json --dry-run
    cat batch.json | python scripts/insert_requests.py
"""

import argparse
import json
import sys
import os

from aws_auth import get_session

# Nome da Lambda manager (mesma usada pela Step Function: app-lambda-ai-requests-manager).
LAMBDA_FUNCTION = os.environ.get("AI_REQUESTS_LAMBDA", "app-lambda-ai-requests-manager")

# Defaults observados nos items reais da tabela (mantidos em sincronia com o backend).
DEFAULT_COPY_LLM = {
    "provider": "bedrock",
    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "imageQuality": None,
}
# OpenAI direct (Images API) — quality="low" actually reduces cost here.
# OpenRouter's chat-completions route ignored the quality knob and always
# billed gpt-image at high tier (~$0.22/img); direct low is ~$0.008/img.
DEFAULT_IMAGE_LLM = {
    "provider": "openai",
    "model": "gpt-image-2",
    "imageQuality": "low",
}

VALID_TONES = {
    "formal",
    "casual",
    "educativo",
    "inspiracional",
    "autoritativo",
    "empatico",
    "urgente",
    "divertido",
    "storytelling",
    "minimalista",
}

VALID_STYLES = {
    "fotorrealista",
    "ilustracao",
    "minimalista",
    "corporativo",
    "bold_vibrante",
    "flat_design",
    "moderno_tech",
    "organico_natural",
    "elegante_premium",
    "energetico",
}


def _fail(msg, code=1):
    sys.stderr.write(f"ERRO: {msg}\n")
    sys.exit(code)


def build_item(payload, sug):
    """Monta um CreateAIRequestModel (item do body do POST /ai_requests).

    tenantId/verticalId/ownerUserId NAO vao aqui — o backend os le do
    authorizer (ver build_authorizer). requestId/status/timestamps sao
    gerados pela Lambda.
    """
    idea = (sug.get("idea") or "").strip()
    if not idea:
        _fail("sugestao sem 'idea' (copy obrigatoria)")
    template_id = sug.get("templateId") or payload.get("templateId")
    if not template_id:
        _fail("sugestao sem 'templateId' (template AI base obrigatorio)")

    tone = sug.get("copyTone") or payload.get("copyTone")
    style = sug.get("imageStyle") or payload.get("imageStyle")
    if tone and tone not in VALID_TONES:
        _fail(f"copyTone invalido: {tone}")
    if style and style not in VALID_STYLES:
        _fail(f"imageStyle invalido: {style}")

    return {
        "idea": idea,
        "templateId": template_id,
        "businessType": sug.get("businessType") or payload.get("businessType") or "",
        "copyTone": tone or "educativo",
        "imageStyle": style or "fotorrealista",
        "copyLLM": sug.get("copyLLM") or payload.get("copyLLM") or DEFAULT_COPY_LLM,
        "imageLLM": sug.get("imageLLM") or payload.get("imageLLM") or DEFAULT_IMAGE_LLM,
    }


def build_authorizer(payload):
    """Contexto do authorizer (requestContext) lido pelo backend (get_user_info).

    O backend confia em tenantId/verticalId/userId daqui, nunca do body.
    """
    tenant_id = payload.get("tenantId")
    vertical_id = payload.get("verticalId")
    if not tenant_id or not vertical_id:
        _fail(
            "tenantId e verticalId sao obrigatorios (item ficaria invisivel no frontend)"
        )

    owner_user_id = payload.get("ownerUserId") or ""
    if not owner_user_id:
        _fail("ownerUserId e obrigatorio (backend exige userId autenticado)")

    return {
        "userId": owner_user_id,
        "email": owner_user_id,
        "name": payload.get("createdBy") or "Template Suggester (AI)",
        "tenantId": tenant_id,
        "verticalId": vertical_id,
        "expireOn": -1,
    }


def build_event(items, authorizer, execute):
    """Evento API-Gateway-proxy equivalente a POST /ai_requests."""
    body = {"executeOnCreate": bool(execute), "items": items}
    return {
        "httpMethod": "POST",
        "path": "/ai_requests",
        "headers": {"Content-Type": "application/json"},
        "requestContext": {"authorizer": authorizer},
        "body": json.dumps(body, ensure_ascii=False),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Insere sugestoes via Lambda ai-requests-manager (POST /ai_requests)"
    )
    ap.add_argument("--input", help="arquivo JSON de entrada (default: stdin)")
    ap.add_argument(
        "--env",
        default="prod",
        choices=["prod", "dev"],
        help="ambiente AWS (default: prod)",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="preview sem invocar a Lambda"
    )
    ap.add_argument(
        "--no-execute",
        dest="execute",
        action="store_false",
        help="cria as requests sem disparar a geracao (executeOnCreate=false). "
        "Default: executeOnCreate=true (dispara idea-to-brief)",
    )
    ap.set_defaults(execute=True)
    args = ap.parse_args()

    # utf-8-sig tolera BOM (PowerShell adiciona BOM ao redirecionar/pipar).
    if args.input:
        raw = open(args.input, encoding="utf-8-sig").read()
    else:
        raw = sys.stdin.buffer.read().decode("utf-8-sig")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(f"JSON de entrada invalido: {exc}")

    suggestions = payload.get("suggestions") or []
    if not suggestions:
        _fail("nenhuma sugestao em 'suggestions'")

    items = [build_item(payload, s) for s in suggestions]
    authorizer = build_authorizer(payload)
    event = build_event(items, authorizer, args.execute)

    print(f"Ambiente: {args.env} | lambda: {LAMBDA_FUNCTION}")
    print(
        f"executeOnCreate: {args.execute} (status inicial: "
        f"{'planning -> plan_review' if args.execute else 'waiting'})"
    )
    print(
        f"tenant: {authorizer['tenantId']}/{authorizer['verticalId']} | user: {authorizer['userId']}"
    )
    print(f"Sugestoes a inserir: {len(items)}")
    for i, it in enumerate(items, 1):
        print(
            f"  [{i}/{len(items)}] bt={it['businessType']!r} "
            f"| tone={it['copyTone']} | style={it['imageStyle']} | base={it['templateId']}"
        )
        print(f"        idea: {it['idea'][:90]}...")

    if args.dry_run:
        print("\n[DRY RUN] Nada foi invocado. Evento que seria enviado:")
        print(json.dumps(event, ensure_ascii=False, indent=2))
        return

    session = get_session(args.env)
    client = session.client("lambda")
    resp = client.invoke(
        FunctionName=LAMBDA_FUNCTION,
        InvocationType="RequestResponse",
        Payload=json.dumps(event, ensure_ascii=False).encode("utf-8"),
    )

    raw_payload = resp["Payload"].read().decode("utf-8")
    if resp.get("FunctionError"):
        _fail(f"Lambda retornou erro ({resp['FunctionError']}): {raw_payload}")

    try:
        result = json.loads(raw_payload)
    except json.JSONDecodeError:
        _fail(f"Resposta da Lambda nao e JSON: {raw_payload}")

    status_code = result.get("statusCode")
    body = result.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass

    if status_code != 200:
        _fail(f"Lambda respondeu {status_code}: {json.dumps(body, ensure_ascii=False)}")

    created = (body or {}).get("requests", [])
    request_ids = [r.get("requestId") for r in created if isinstance(r, dict)]
    print(
        f"\nOK - {len(request_ids)} sugestoes criadas. "
        f"{(body or {}).get('message', '')}"
    )
    if request_ids:
        print("requestIds:", ", ".join(rid for rid in request_ids if rid))


if __name__ == "__main__":
    main()
