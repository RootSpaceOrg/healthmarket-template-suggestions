#!/usr/bin/env python3
"""
Insere sugestoes (copies geradas pela IA) na DynamoDB `AIRequestsTable` com
`status: waiting` e contexto multi-tenant completo, para que aparecam na tela
de request-workflow do frontend (filtra por tenantId/verticalId).

A IA (skill) e responsavel por ESCREVER a copy. Este script so faz I/O: recebe
um JSON com a lista de sugestoes e grava cada item com o schema correto.

Schema gravado por item (campos lidos pelo frontend ai-requests-api.service):
    requestId, status=waiting, idea, templateId, businessType,
    copyTone, imageStyle, copyLLM, imageLLM,
    tenantId, verticalId, ownerUserId, createdBy,
    createdAt, updatedAt, generatedTemplateId=None, executionArn=None, error=None

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
    python scripts/insert_requests.py --input batch.json --dry-run
    cat batch.json | python scripts/insert_requests.py
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

from aws_auth import get_session

TABLE = "AIRequestsTable"

# Defaults observados nos items reais da tabela (mantidos em sincronia com o backend).
DEFAULT_COPY_LLM = {
    "provider": "bedrock",
    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "imageQuality": None,
}
DEFAULT_IMAGE_LLM = {
    "provider": "openrouter",
    "model": "openai/gpt-5.4-image-2",
    "imageQuality": "low",
}

VALID_TONES = {
    "formal", "casual", "educativo", "inspiracional", "autoritativo",
    "empatico", "urgente", "divertido", "storytelling", "minimalista",
}
VALID_STYLES = {
    "fotorrealista", "ilustracao", "minimalista", "corporativo", "bold_vibrante",
    "flat_design", "moderno_tech", "organico_natural", "elegante_premium", "energetico",
}


def _fail(msg, code=1):
    sys.stderr.write(f"ERRO: {msg}\n")
    sys.exit(code)


def build_item(payload, sug):
    now = datetime.now(timezone.utc).isoformat()

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

    tenant_id = sug.get("tenantId") or payload.get("tenantId")
    vertical_id = sug.get("verticalId") or payload.get("verticalId")
    if not tenant_id or not vertical_id:
        _fail("tenantId e verticalId sao obrigatorios (item ficaria invisivel no frontend)")

    return {
        "requestId": str(uuid.uuid4()),
        "status": "waiting",
        "idea": idea,
        "templateId": template_id,
        "businessType": sug.get("businessType") or payload.get("businessType") or "",
        "copyTone": tone or "educativo",
        "imageStyle": style or "fotorrealista",
        "copyLLM": sug.get("copyLLM") or payload.get("copyLLM") or DEFAULT_COPY_LLM,
        "imageLLM": sug.get("imageLLM") or payload.get("imageLLM") or DEFAULT_IMAGE_LLM,
        "tenantId": tenant_id,
        "verticalId": vertical_id,
        "ownerUserId": sug.get("ownerUserId") or payload.get("ownerUserId") or "",
        "createdBy": payload.get("createdBy") or "Template Suggester (AI)",
        "createdAt": now,
        "updatedAt": now,
        "generatedTemplateId": None,
        "executionArn": None,
        "error": None,
    }


def main():
    ap = argparse.ArgumentParser(description="Insere sugestoes na AIRequestsTable (status=waiting)")
    ap.add_argument("--input", help="arquivo JSON de entrada (default: stdin)")
    ap.add_argument("--env", default="prod", choices=["prod", "dev"], help="ambiente AWS (default: prod)")
    ap.add_argument("--dry-run", action="store_true", help="preview sem gravar")
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

    print(f"Ambiente: {args.env} | tabela: {TABLE}")
    print(f"Sugestoes a inserir: {len(items)}")
    for i, it in enumerate(items, 1):
        print(f"  [{i}/{len(items)}] {it['requestId'][:8]} | bt={it['businessType']!r} "
              f"| tone={it['copyTone']} | style={it['imageStyle']} | base={it['templateId']}")
        print(f"        idea: {it['idea'][:90]}...")

    if args.dry_run:
        print("\n[DRY RUN] Nada foi gravado.")
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    session = get_session(args.env)
    table = session.resource("dynamodb").Table(TABLE)
    with table.batch_writer() as batch:
        for it in items:
            batch.put_item(Item=it)

    print(f"\nOK - {len(items)} sugestoes inseridas com status=waiting.")
    print("requestIds:", ", ".join(it["requestId"] for it in items))


if __name__ == "__main__":
    main()
