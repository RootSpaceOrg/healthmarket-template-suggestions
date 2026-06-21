---
name: template-suggester
description: "Gera sugestoes de copy para NOVOS templates da plataforma mkt-platform (KultivAi e outros tenants), a partir dos templates AI ja publicados. Use quando o usuario pedir sugestoes de template para um assunto e um tenant/vertical, ex: 'quero 5 sugestoes sobre laserterapia no kultivai saude', 'gera 3 ideias de nutricao para o kultivai health', 'sugere templates de odontologia'. A skill resolve o tenant/vertical no DynamoDB tenantConfig, valida que o businessType existe, le os templates AI publicados no Supabase (prod), e a propria IA escreve a copy final de cada sugestao, gravando como AIRequest com status=waiting para aparecer na tela de request-workflow. Roda sob demanda (inclusive via OpenClaw/Telegram)."
---

# template-suggester

Cerebro de sugestao de templates da plataforma **mkt-platform** (multi-tenant / multi-vertical).
Dado um pedido em linguagem natural (`"quero 5 sugestoes sobre laserterapia no kultivai saude"`),
a skill produz N sugestoes de **copy final** que viram `AIRequest`s com `status=waiting` — o
pipeline backend depois gera o template novo a partir de cada uma.

A **IA (voce, no chat) escreve a copy**. Os scripts so fazem I/O (resolver tenant, buscar
templates base, gravar no DynamoDB). Isso permite rodar tanto no chat quanto via OpenClaw/Telegram.

## Principios

1. **Tenant e source of truth.** O tenant/vertical e o `businessType` vem do `tenantConfig` no
   DynamoDB — nunca invente. Se o `businessType` pedido nao existir cadastrado, **pare** e peca
   ao usuario para cadastrar na plataforma, devolvendo o link de admin.
2. **Base = templates AI publicados em prod.** A copy nova e inspirada nas `description` dos
   templates com `template_type=ai` e `status=published` no Supabase. Selecao do template base e
   **aleatoria** (um base aleatorio por sugestao).
3. **A IA escreve a copy.** Nada de templates de string fixos. Cada sugestao e uma copy real,
   contextualizada ao assunto + businessType pedido, no idioma do usuario (PT-BR por padrao).
4. **Ambiente prod por padrao.** A leitura de templates base e a gravacao das sugestoes vao para
   prod, a menos que o usuario diga "dev". A autenticacao AWS usa o mesmo modelo do
   template-generator: o user IAM `TemplateGenerator` (chaves no `.env` de secrets) assume a role
   `TemplateSuggesterRole` via STS (ver "Autenticacao AWS" abaixo).
5. **Sai visivel na plataforma.** Cada sugestao e gravada com tenant/vertical/owner corretos para
   aparecer na tela de revisao (`request-workflow`) filtrada por tenant.

## Quando usar

Frases-gatilho:
- "quero N sugestoes sobre <assunto> no <tenant> <vertical>"
- "gera N ideias de <businessType> para o <tenant> <vertical>"
- "sugere templates de <assunto>"
- "roda o suggester para laserterapia no kultivai saude"

Se o usuario nao disser N, default e **3**.

## Como interpretar o pedido

Do texto livre, extraia:

| Campo | Como inferir | Default |
|-------|--------------|---------|
| `N` (quantidade) | numero no pedido ("5 sugestoes") | 3 |
| `assunto` | tema/businessType citado ("laserterapia", "nutricao") | obrigatorio |
| `tenant` | nome do tenant ("kultivai") | `kultivai` se omitido |
| `vertical` | apelido da vertical ("saude", "health", "pet") — **normalize** | obrigatorio (peca se faltar) |
| `ambiente` | "dev" em qualquer forma → `dev`; senao `prod` | `prod` |

**Normalizacao de vertical (apelido → verticalId):**
- `saude`, `saúde`, `health` → `health`
- `pet` → `pet`
- `beleza`, `beauty`, `estetica` → `beauty`
- `fitness` → `fitness`

Ex: `"quero 5 sugestoes sobre laserterapia no kultivai saude"` →
`N=5, assunto=laserterapia, tenant=kultivai, vertical=health, ambiente=prod`.

## Workflow da skill

Execute os passos em ordem. Os scripts estao em `scripts/` e usam `boto3` + AWS CLI profiles.

### Passo 1 — Resolver tenant e validar businessType

Monte `PK = TENANT#{tenant}#VERTICAL#{vertical}`, `SK = CONFIG` e rode:

```bash
python scripts/resolve_tenant.py --tenant <tenant> --vertical <vertical> \
  --subject "<assunto>" --env <prod|dev>
```

Interprete o **exit code** + JSON em stdout:

| Exit | Significado | O que fazer |
|------|-------------|-------------|
| `0` | tenant ok + `matchedBusinessType` encontrado | **siga** para o Passo 2. Use `matchedBusinessType.label` como `businessType` das sugestoes. |
| `3` | tenant existe mas **sem** `businessTypes` | **PARE.** Peca ao usuario para cadastrar businessTypes na plataforma. Mostre `adminLink`. |
| `4` | assunto nao casa com nenhum businessType | **PARE.** Liste os `businessTypes` disponiveis (do JSON) e peca para o usuario escolher um existente ou cadastrar o novo. Mostre `adminLink`. |
| `2` | tenantConfig nao encontrado | **PARE.** Avise que o par tenant/vertical nao existe nesse ambiente. |
| `1` | erro inesperado | reporte o erro. |

O `adminLink` ja vem pronto no JSON, no formato exigido:
`https://{domain}/admin/plataforma/{tenantId}/{verticalId}`.

> **businessType nas sugestoes = o `label`** do tenantConfig (ex: `"Laserterapia"`), nao o `value`.
> O frontend exibe o label. O script de resolve ja retorna `matchedBusinessType.label`.

### Passo 2 — Buscar templates AI base (amostra aleatoria)

```bash
python scripts/fetch_ai_templates.py --count <N> --env <prod|dev>
```

Retorna JSON `{ ok, totalAvailable, templates: [{id, name, description, businessType}] }`.
Pegue uma amostra aleatoria de N (o script ja amostra). Use o `id` como `templateId` base e a
`description` como **contexto criativo** para escrever a copy. Se quiser ver todos para escolher
manualmente, use `--all`.

> Os templates AI publicados sao majoritariamente multi-nicho (scope=platform). Voce vai
> **especializar** a copy para o assunto/businessType pedido, mantendo o templateId base.

### Passo 3 — Escrever o `idea` (VOCE, a IA)

> **Importante — o que e o `idea`.** A Lambda `ai-idea-to-template` consome o `idea` como
> **brief de campanha**, NAO como a copy final dos slides. Ela mesma escreve a copy de cada
> elemento (titulo, corpo, CTA, descricao de imagem) a partir do `idea` + `copyTone` +
> `businessType` + descricao do template base. Entao o `idea` deve dar **direcao**, nao texto
> literal slide-a-slide. (Ver `Lambda/mkt-platform-lambda-ai-idea-to-template/app/Utils/prompt_templates.py`.)

Para cada uma das N sugestoes, escreva um `idea` que funcione como brief. Inclua, no idioma do usuario:

- **Angulo unico** da campanha — o que diferencia esta peca de qualquer concorrente do mesmo
  segmento. (ex: "laserterapia para dor cronica em quem ja tentou fisioterapia sem resultado").
- **Audiencia especifica** — nunca "todos"/"para voce". (ex: "adultos 40+ com dor lombar persistente").
- **Beneficio concreto/mensuravel** — nao adjetivo vago. (ex: "reducao de dor ja nas primeiras sessoes").
- **Hook do slide 1** — pergunta provocativa, numero, contradicao que pare o scroll.
- **Specifics a referenciar** — 2-3 elementos concretos (numero, prazo, cenario cotidiano, objecao comum).
- **Direcao do arco** alinhada a `description` do template base (ex: formato antes/depois em 4 slides).
- **CTA pretendido** — especifico, ligado ao servico (ex: "agendar avaliacao"). NAO use CTA generico.

**NAO faca no `idea`:**
- Nao escreva a copy final palavra-por-palavra de cada slide — isso e trabalho da Lambda.
- Nao use clichês/frases proibidas (a Lambda **rejeita automaticamente**): "aproveite", "saiba mais",
  "clique aqui", "nao perca", "o melhor do mercado", "qualidade incomparavel", "para voce",
  "venha conhecer", "a solucao perfeita", "feito sob medida", etc.
- Nao repita o `businessType` a exaustao — ele ja entra dinamicamente na Lambda.
- Nao inclua emoji (a Lambda so usa emoji se o elemento pedir explicitamente).

Escolha `copyTone` e `imageStyle` coerentes (listas validas abaixo). **Varie** entre as N sugestoes
— nao repita o mesmo tom/estilo/angulo em todas.

`copyTone`: `formal | casual | educativo | inspiracional | autoritativo | empatico | urgente | divertido | storytelling | minimalista`

`imageStyle`: `fotorrealista | ilustracao | minimalista | corporativo | bold_vibrante | flat_design | moderno_tech | organico_natural | elegante_premium | energetico`

### Passo 4 — Montar o batch JSON e gravar

Monte um arquivo JSON (ex: em `$TEMP/suggester_batch.json`) no formato:

```json
{
  "tenantId": "kultivai",
  "verticalId": "health",
  "businessType": "Laserterapia",
  "ownerUserId": "<email do usuario, se conhecido>",
  "createdBy": "Template Suggester (AI)",
  "suggestions": [
    {
      "idea": "<copy final escrita por voce>",
      "templateId": "<id do template AI base, aleatorio>",
      "copyTone": "educativo",
      "imageStyle": "fotorrealista"
    }
  ]
}
```

Grave (sempre rode `--dry-run` primeiro para conferir):

```bash
python scripts/insert_requests.py --input <batch>.json --env <prod|dev> --dry-run
python scripts/insert_requests.py --input <batch>.json --env <prod|dev>
```

Cada item entra na `AIRequestsTable` com `status=waiting`, `tenantId`/`verticalId`/`ownerUserId`
preenchidos (sem eles o item nao aparece no frontend), `createdAt`/`updatedAt` em ISO, e
`copyLLM`/`imageLLM` com os defaults do ambiente.

### Passo 5 — Reportar ao usuario

Responda com um resumo consolidado: N sugestoes criadas, o businessType resolvido, os
`requestId`s gerados, e onde revisar (`https://{domain}/processar-solicitacoes`). Se algum passo
parou (exit 2/3/4), explique.


## Defaults de gravacao

`copyLLM` e `imageLLM` espelham os items reais da tabela (sincronizados com o backend):

```json
{
  "copyLLM":  { "provider": "bedrock",    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0", "imageQuality": null },
  "imageLLM": { "provider": "openrouter", "model": "openai/gpt-5.4-image-2", "imageQuality": "low" }
}
```

Para sobrescrever, inclua `copyLLM`/`imageLLM` no topo do batch ou por sugestao.

## Autenticacao AWS

Mesmo padrao do template-generator (`gp2-template-uploader`). O helper
[`scripts/aws_auth.py`](scripts/aws_auth.py) centraliza isso; os outros scripts so chamam
`get_session(env)`.

**Modo padrao (assume-role — producao / OpenClaw):**
1. Le o `.env` de credenciais do user IAM `TemplateGenerator` em `GP2_SECRETS_DIR`
   (default `/root/.openclaw/workspace/secrets`), arquivo
   `aws-credentials-template-generator-mkt-platform-{env}.env` — **o mesmo arquivo que o
   template-generator usa**.
2. `sts.assume_role` na role do suggester:
   - prod: `arn:aws:iam::692046683598:role/TemplateSuggesterRole`
   - dev:  `arn:aws:iam::656032436386:role/TemplateSuggesterRole`
3. Os clients boto3 usam as credenciais temporarias.

A role concede o minimo: `ssm:GetParameter` em `/default/supabase-database-credentials`,
`dynamodb:GetItem/Query` em `tenantConfig`, e `dynamodb:PutItem/BatchWriteItem/GetItem/Query`
em `AIRequestsTable`. Ela confia no mesmo user `TemplateGenerator`.

**Fallback (dev local nesta maquina):** se o `.env` nao existir, o helper cai automaticamente
para `boto3.Session(profile_name=mkt-platform-{env})` usando seu SSO local. Force um modo com
`SUGGESTER_AUTH_MODE=assume|profile`.

## Pre-requisitos

```bash
pip install boto3
# Producao/OpenClaw: garanta o .env do user TemplateGenerator em GP2_SECRETS_DIR.
# Dev local: aws sso login --profile mkt-platform-prod   # ou mkt-platform-dev
```

- Python 3.10+, `boto3`.
- `.env` de credenciais do `TemplateGenerator` (modo assume-role) **ou** perfis SSO
  `mkt-platform-prod` / `mkt-platform-dev` (fallback local).

> **Encoding (Windows):** rode com `PYTHONUTF8=1` (ou `$env:PYTHONUTF8=1`). Os `businessTypes`
> tem emoji; sem UTF-8 o console pode quebrar. O `insert_requests.py` tolera BOM no input.

## Scripts

| Script | Faz | Saida |
|--------|-----|-------|
| `scripts/aws_auth.py` | helper de auth (assume-role `TemplateSuggesterRole` ou fallback SSO) | `get_session(env)` |
| `scripts/resolve_tenant.py` | resolve `tenantConfig`, valida `businessTypes`, casa `--subject`, emite `adminLink` | JSON + exit code (0/2/3/4) |
| `scripts/fetch_ai_templates.py` | le templates `ai`+`published` do Supabase, amostra aleatoria | JSON `{templates:[...]}` |
| `scripts/insert_requests.py` | grava sugestoes na `AIRequestsTable` (`status=waiting`, tenant-aware) | requestIds |

## Nao faca

- Nao invente `tenantId`/`verticalId`/`businessType` — sempre confirme no `tenantConfig`.
- Nao prossiga se `resolve_tenant.py` retornar exit 2/3/4 — pare e oriente o usuario com o `adminLink`.
- Nao grave items sem `tenantId`/`verticalId` — ficam invisiveis no frontend.
- Nao use copy de string fixa/aleatoria — a IA escreve copy real e variada.
- Nao grave em prod sem rodar `--dry-run` antes.
- Nao hardcode HealthMarket nem o tenant `kultivai` nos scripts (eles ja sao parametrizados).

## Referencias

- [`references/idea-format.md`](references/idea-format.md) — **como escrever o `idea`**: a Lambda consumidora trata como brief, regras anti-AI-slop e frases proibidas.
- [`references/airequests-schema.md`](references/airequests-schema.md) — schema completo da `AIRequestsTable` e o que o frontend le.
- [`references/tenant-resolution.md`](references/tenant-resolution.md) — estrutura do `tenantConfig`, businessTypes e formato do adminLink.
- [`references/iam-setup.md`](references/iam-setup.md) — roles `TemplateSuggesterRole`, trust e policy.

## Fluxo end-to-end

```
Pedido NL ("quero 5 sugestoes sobre laserterapia no kultivai saude")
  -> resolve_tenant.py  (tenantConfig: valida businessType + adminLink)
  -> fetch_ai_templates.py  (Supabase prod: templates ai+published, amostra aleatoria)
  -> IA escreve N copies (idea + tone + style)
  -> insert_requests.py  (AIRequestsTable status=waiting, tenant-aware)
  -> tela request-workflow (fila "waiting") -> pipeline backend gera template -> status=review
```
