# AIRequestsTable — Schema

Tabela DynamoDB onde as sugestoes sao gravadas. O frontend
(`request-workflow.component.ts` via `ai-requests-api.service.ts`) le esta tabela
filtrando por `status` **e** pelo tenant/vertical do usuario logado. Por isso
`tenantId`/`verticalId` sao obrigatorios — sem eles o item nao aparece.

## Atributos (observados nos items reais de prod)

| Campo | Tipo | Obrigatorio | Descricao |
|-------|------|:-----------:|-----------|
| `requestId` | String (PK) | sim | UUID v4 |
| `status` | String | sim | `waiting` → `running` → `review` → `approved`/`rejected` · ou `failed` |
| `idea` | String | sim | Copy final (a IA escreve). Tema, estrutura, hook, corpo, CTA. |
| `templateId` | String | sim | ID do template AI **base** no Supabase (selecao aleatoria) |
| `businessType` | String | sim* | **Label** do tenantConfig (ex: `"Laserterapia"`), nao o value |
| `copyTone` | String | sim | ver lista de tones validos |
| `imageStyle` | String | sim | ver lista de styles validos |
| `copyLLM` | Map | sim | `{ provider, model, imageQuality }` |
| `imageLLM` | Map | sim | `{ provider, model, imageQuality }` |
| `tenantId` | String | **sim** | ex: `kultivai` — sem isso o item some do frontend |
| `verticalId` | String | **sim** | ex: `health` |
| `ownerUserId` | String | recomendado | email/uid do dono (ex: `gustavo.reis20000@gmail.com`) |
| `createdBy` | String | sim | origem (ex: `"Template Suggester (AI)"`) |
| `createdAt` | String | sim | ISO timestamp |
| `updatedAt` | String | sim | ISO timestamp |
| `generatedTemplateId` | String/null | — | ID do template gerado (preenchido pelo backend) |
| `executionArn` | String/null | — | ARN do Step Functions (quando processando) |
| `error` | String/null | — | mensagem de erro (se `failed`) |

\* `businessType` pode ficar vazio (`""`) para sugestoes genericas, mas a skill normalmente
preenche com o label resolvido no `tenantConfig`.

## copyTone validos

`formal · casual · educativo · inspiracional · autoritativo · empatico · urgente · divertido · storytelling · minimalista`

## imageStyle validos

`fotorrealista · ilustracao · minimalista · corporativo · bold_vibrante · flat_design · moderno_tech · organico_natural · elegante_premium · energetico`

## LLM defaults (sincronizados com items reais)

```json
{
  "copyLLM":  { "provider": "bedrock",    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0", "imageQuality": null },
  "imageLLM": { "provider": "openrouter", "model": "openai/gpt-5.4-image-2", "imageQuality": "low" }
}
```

## Como o frontend le

`AiRequestsApiService.getRequests({ status }, limit, offset)` → `GET ai_requests?status=...&limit=...`.
A tela `request-workflow` carrega duas filas: `status=waiting` (validar) e `status=review` (revisar).
Sugestoes novas entram em `waiting`.
