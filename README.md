# HealthMarket Template Suggestions

Repositório da skill e scripts de geração de sugestões para templates estáticos de Instagram no HealthMarket.

## Fluxo atual (end-to-end)

1. `generate-suggestions.py` lê credenciais Supabase do SSM:
   - `supabase-database-credentials`
2. Busca templates no Supabase com filtros:
   - `template_type = ai`
   - `status = published`
   - `user_id/userId = public`
3. Usa `description` do template como contexto da ideia.
4. Insere requests na `AIRequestsTable` com `status = waiting`.
5. Pipeline backend processa e atualiza status (`completed`/`failed`).

## Segmentos válidos

- odontologia → `dentistry`
- medicos → `medical-clinic`
- nutricao → `nutrition`
- fisioterapia → `physiotherapy`
- psicologia → `psychology`
- estetica → `aesthetics`
- farmacias → `pharmacy`
- laboratorios → `laboratory`
- laserterapia → `laserterapy`
- generico/genérico/generic → `""` (em branco)

## Scripts

- `scripts/generate-suggestions.py`
- `scripts/insert-segment-ideas.py`
- `scripts/check-suggestions.py`
- `scripts/check-segment-ideas.py`

## Uso rápido

```bash
python scripts/generate-suggestions.py --count 1 --segment medicos
python scripts/check-suggestions.py
```

## Pré-requisitos

- Python 3.10+
- `pip install boto3`
- AWS CLI com profile `healthmarket-prod` autenticado (`aws sso login --profile healthmarket-prod`)
