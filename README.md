# template-suggester (mkt-platform)

Skill + scripts para gerar **sugestoes de copy** para novos templates da plataforma
**mkt-platform** (multi-tenant / multi-vertical — KultivAi e demais tenants).

Roda sob demanda a partir de um pedido em linguagem natural, ex:

> "quero 5 sugestoes sobre laserterapia no kultivai saude"

A **IA escreve a copy**; os scripts so fazem I/O. Veja [`SKILL.md`](SKILL.md) para o workflow completo.

## Fluxo

```
Pedido NL
  -> resolve_tenant.py     (tenantConfig: valida businessType + monta adminLink)
  -> fetch_ai_templates.py (Supabase prod: templates ai+published, amostra aleatoria)
  -> IA escreve N copies   (idea + copyTone + imageStyle)
  -> insert_requests.py    (AIRequestsTable status=waiting, tenant-aware)
  -> tela request-workflow (fila "waiting") -> pipeline backend gera template -> status=review
```

## Scripts

| Script | Faz |
|--------|-----|
| `scripts/aws_auth.py` | Auth compartilhada: assume `TemplateSuggesterRole` via STS (padrao template-generator) ou cai para profile SSO local. |
| `scripts/resolve_tenant.py` | Resolve `TENANT#{t}#VERTICAL#{v}`/`CONFIG`, valida `businessTypes`, casa o assunto, emite `adminLink`. Exit 0/2/3/4. |
| `scripts/fetch_ai_templates.py` | Le templates `template_type=ai` + `status=published` do Supabase (prod) e amostra aleatoriamente. |
| `scripts/insert_requests.py` | Grava sugestoes na `AIRequestsTable` com `status=waiting` + tenant/vertical/owner. |

## Uso rapido

```bash
# 1) resolve tenant + valida assunto
python scripts/resolve_tenant.py --tenant kultivai --vertical health --subject laserterapia

# 2) busca N templates AI base (aleatorio)
python scripts/fetch_ai_templates.py --count 5

# 3) (IA escreve o batch.json) e grava
python scripts/insert_requests.py --input batch.json --dry-run
python scripts/insert_requests.py --input batch.json
```

Adicione `--env dev` para o ambiente de dev (default e `prod`).

## Autenticacao AWS

Mesmo modelo do template-generator: o user IAM `TemplateGenerator` assume uma role via STS.
A role do suggester (criada em ambas as contas) e:

- prod: `arn:aws:iam::692046683598:role/TemplateSuggesterRole`
- dev:  `arn:aws:iam::656032436386:role/TemplateSuggesterRole`

Permissoes minimas (inline `TemplateSuggesterActionsPolicy`): `ssm:GetParameter` na credencial
do Supabase, leitura de `tenantConfig`, leitura/escrita de `AIRequestsTable`. Confia no mesmo
user `TemplateGenerator`, entao **reusa o mesmo `.env` de credenciais** do template-generator
(`aws-credentials-template-generator-mkt-platform-{env}.env` em `GP2_SECRETS_DIR`).

Fallback de dev local: sem o `.env`, `aws_auth.py` usa o profile SSO `mkt-platform-{env}`.

## Pre-requisitos

- Python 3.10+, `pip install boto3`
- Modo producao/OpenClaw: `.env` do user `TemplateGenerator` em `GP2_SECRETS_DIR`
  (default `/root/.openclaw/workspace/secrets`)
- Modo dev local: `aws sso login --profile mkt-platform-prod` (ou `-dev`)
- Windows: rode com `PYTHONUTF8=1` (businessTypes tem emoji)

## Referencias

- [`references/airequests-schema.md`](references/airequests-schema.md)
- [`references/tenant-resolution.md`](references/tenant-resolution.md)
