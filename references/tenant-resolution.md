# tenantConfig — Resolucao de tenant/vertical e businessTypes

A skill resolve o par tenant/vertical no DynamoDB `tenantConfig` antes de gerar qualquer sugestao.

## Chave

| Chave | Formato | Exemplo |
|-------|---------|---------|
| `PK` | `TENANT#{tenantId}#VERTICAL#{verticalId}` | `TENANT#kultivai#VERTICAL#health` |
| `SK` | `CONFIG` | `CONFIG` |

## Atributos relevantes

| Campo | Tipo | Uso na skill |
|-------|------|--------------|
| `tenantId` | String | ex: `kultivai` |
| `verticalId` | String | ex: `health` |
| `domain` | String | ex: `saude.kultivai.com.br` — base do `adminLink` |
| `businessTypes` | List<Map> | catalogo de segmentos cadastrados |
| `brand`, `themes`, `status` | — | nao usados pela skill |

### Estrutura de `businessTypes`

Lista de maps; cada entrada:

```json
{ "label": "Laserterapia", "value": "laserterapy", "emoji": "🧑‍⚕️", "enabled": true }
```

- **`label`** → e o que vai em `businessType` da sugestao (o frontend exibe o label).
- **`value`** → slug interno; usado para casamento, nao gravado.
- **`enabled`** → entradas com `enabled=false` sao ignoradas.

## adminLink

Formato exigido (montado pelo `resolve_tenant.py`):

```
https://{domain}/admin/plataforma/{tenantId}/{verticalId}
```

Ex: `https://saude.kultivai.com.br/admin/plataforma/kultivai/health`

Use o `adminLink` quando precisar pedir ao usuario para cadastrar businessTypes
(tenant sem businessTypes, ou assunto sem match).

## Casamento de assunto (`--subject`)

`resolve_tenant.py` casa o assunto pedido contra `label` e `value` (lowercase, sem acento):
1. match exato em `value` ou `label`;
2. match parcial (contido) nos dois sentidos.

Exit codes do script:

| Exit | Reason | Acao da skill |
|------|--------|---------------|
| 0 | ok (+ `matchedBusinessType`) | seguir; usar `matchedBusinessType.label` |
| 2 | `tenant_config_not_found` | parar; par tenant/vertical nao existe |
| 3 | `no_business_types` | parar; pedir cadastro (mostrar `adminLink`) |
| 4 | `subject_no_match` | parar; listar disponiveis + `adminLink` |

## businessTypes atuais (kultivai / health, prod) — referencia

| label | value |
|-------|-------|
| Laserterapia | laserterapy |
| Clinica Medica | medical-clinic |
| Laboratorio | laboratory |
| Farmacia | pharmacy |
| Nutricionista | nutrition |
| Fisioterapia | physiotherapy |
| Psicologia | psychology |
| Odontologia | dentistry |
| Estetica e Bem-Estar | aesthetics |

> Esta lista e um snapshot — **sempre** resolva ao vivo com `resolve_tenant.py`, pois o
> cadastro muda na plataforma.
