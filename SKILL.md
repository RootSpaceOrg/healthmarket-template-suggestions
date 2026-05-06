---
name: template-ideas-generator
description: Generate and manage template ideas for health market segments (odontologia, médicos, nutrição, fisioterapia, psicologia, estética, farmácias, laboratórios, laserterapia e genérico) by inserting ideas into DynamoDB AIRequestsTable. Use when needing to create batch template ideas, manage segment-specific suggestions, populate the ideas database, or check existing ideas.
---

# Template Ideas Generator

Generate and insert template ideas for health market segments into DynamoDB's AIRequestsTable.

## Quick Start

### Generate Segment-Specific Ideas (16 ideas: 2 per segment)

```bash
python scripts/insert-segment-ideas.py
```

Inserts segment ideas for valid health segments:
- 🦷 Odontologia
- 🏥 Médicos
- 🥗 Nutrição
- 🧘 Fisioterapia
- 🧠 Psicologia
- 💆 Estética
- 💊 Farmácias
- 🔬 Laboratórios
- ⚡ Laserterapia
- 🧩 Genérico (sem `businessType`)

### Generate Contextual Ideas from Supabase Templates

```bash
python scripts/generate-suggestions.py --count 10
```

Creates N ideas using real template context from Supabase (`description` field), filtered by:
- `template_type == ai`
- `status == published`
- `user_id/userId == public`

Supabase credentials are loaded from AWS SSM Parameter Store parameter:
- `supabase-database-credentials`

### Check Existing Ideas

```bash
# Check segment-specific ideas
python scripts/check-segment-ideas.py

# Check generic suggestions
python scripts/check-suggestions.py
```

## Prerequisites

```bash
pip install boto3
```

AWS CLI configured with profile `healthmarket-prod`:

```bash
aws configure --profile healthmarket-prod
```

## Scripts

### insert-segment-ideas.py

Inserts 16 segment-specific ideas (2 per segment).

**Features:**
- Pre-defined ideas mapped to real templates
- Segment identification via `businessType`
- Appropriate `copyTone` and `imageStyle` per idea
- `createdBy: "Ideias Segmentadas 2x8"` for filtering

**Options:**
- `--dry-run` - Preview without inserting
- `--profile PROFILE` - AWS CLI profile (default: healthmarket-prod)

**Output:**
```
📝 Preparando 16 ideias segmentadas...
[ 1/16] 🦷 ODONTOLOGIA
  📌 Sorriso Perfeito em 3 Passos
  ✍️  educativo | 🎨 fotorrealista
...
✅ 16 ideias inseridas com sucesso!
```

### generate-suggestions.py

Generates N contextual ideas based on template descriptions fetched from Supabase.

**Options:**
- `--count N` - Number of ideas (default: 5)
- `--segment SEGMENT` - Segmento válido: `odontologia | medicos | nutricao | fisioterapia | psicologia | estetica | farmacias | laboratorios | laserterapia | generico`
- `--dry-run` - Preview without inserting
- `--profile PROFILE` - AWS CLI profile

**Output:**
```
Gerando 10 sugestões...
✅ 10 sugestões inseridas com sucesso!
```

### check-segment-ideas.py

Lists segment-specific ideas from DynamoDB.

**Output:**
```
📊 Ideias Segmentadas no DynamoDB

Total: 16 ideias
Status: waiting (prontas para processamento)

Por Segmento:
  🦷 odontologia: 2 ideias
  🏥 medicos: 2 ideias
  ...
```

### check-suggestions.py

Lists generic suggestions from DynamoDB.

**Output:**
```
📊 Sugestões no DynamoDB

Total: 50 sugestões
Por Status:
  waiting: 45
  completed: 5
```

## Data Structure

Each idea is inserted into `AIRequestsTable` with:

```json
{
  "requestId": "uuid-v4",
  "idea": "Detailed description with layout, colors, copy, CTA",
  "templateId": "base template ID from Supabase",
  "businessType": "segment (odontologia, medicos, etc)",
  "copyTone": "educativo | empatico | urgente | autoritativo | inspiracional",
  "imageStyle": "fotorrealista | ilustracao | minimalista | corporativo | organico_natural | elegante_premium",
  "status": "waiting",
  "createdBy": "identifier (e.g., 'Ideias Segmentadas 2x8')",
  "createdAt": "ISO timestamp",
  "updatedAt": "ISO timestamp",
  "copyLLM": { "provider": "bedrock", "model": "..." },
  "imageLLM": { "provider": "openrouter", "model": "..." }
}
```

## When to Use Each Script

| Task | Script | Use Case |
|------|--------|----------|
| **Initial database population** | `insert-segment-ideas.py` | Need diverse, quality ideas across all segments |
| **Quick testing/demos** | `generate-suggestions.py --count 10` | Need random ideas fast for testing |
| **Verification** | `check-segment-ideas.py` | See what segment ideas exist |
| **Status monitoring** | `check-suggestions.py` | Monitor processing pipeline |

## References

- **[dynamodb-schema.md](references/dynamodb-schema.md)** - Complete AIRequestsTable schema
- **[segment-ideas.md](references/segment-ideas.md)** - All 16 segment ideas with details

## End-to-End Workflow (com inserção no Dynamo)

```
Supabase (templates ai+published+public) → generate-suggestions.py → AIRequestsTable(status=waiting) → Backend pipeline → status=completed|failed
```

**Processing:**
1. `generate-suggestions.py` lê credenciais do SSM (`supabase-database-credentials`)
2. Busca templates no Supabase com filtros:
   - `template_type == ai`
   - `status == published`
   - `user_id/userId == public`
3. Usa `description` do template como contexto da ideia gerada
4. Insere item na `AIRequestsTable` com `status: waiting`
5. Backend processa e atualiza `generatedTemplateId` + `status`
6. Em erro, preenche `error` + `status: failed`

## Tips

**Filtering by source:**
```python
# Only segment ideas
FilterExpression=Attr('createdBy').eq('Ideias Segmentadas 2x8')

# Only generic/contextual ideas
FilterExpression=Attr('createdBy').begins_with('Sugestão AI')
```

**Dry-run first:**
```bash
# Preview before inserting
python scripts/insert-segment-ideas.py --dry-run
```

**Windows encoding fix:**
All scripts include Windows UTF-8 encoding fix for emoji support.
