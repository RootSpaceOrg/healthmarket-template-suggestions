---
name: template-ideas-generator
description: Generate and manage template ideas for health market segments (odontologia, médicos, nutrição, fisioterapia, psicologia, estética, farmácias, laboratórios) by inserting ideas into DynamoDB AIRequestsTable. Use when needing to create batch template ideas, manage segment-specific suggestions, populate the ideas database, or check existing ideas.
---

# Template Ideas Generator

Generate and insert template ideas for health market segments into DynamoDB's AIRequestsTable.

## Quick Start

### Generate Segment-Specific Ideas (16 ideas: 2 per segment)

```bash
python scripts/insert-segment-ideas.py
```

Inserts 16 carefully crafted ideas covering 8 health segments:
- 🦷 Odontologia
- 🏥 Médicos
- 🥗 Nutrição
- 🧘 Fisioterapia
- 🧠 Psicologia
- 💆 Estética
- 💊 Farmácias
- 🔬 Laboratórios

### Generate Random Generic Ideas

```bash
python scripts/generate-suggestions.py --count 10
```

Creates N random ideas from a pool of generic templates.

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

Generates N random generic ideas.

**Options:**
- `--count N` - Number of ideas (default: 5)
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

## Workflow

```
Script Inserts → status: waiting → Backend Processes → Template Generated → status: completed
```

**Processing:**
1. Scripts insert ideas with `status: waiting`
2. Backend system picks up waiting items
3. Generates template using AI (copy + image)
4. Updates with `generatedTemplateId` + `status: completed`
5. On error: updates `error` field + `status: failed`

## Tips

**Filtering by source:**
```python
# Only segment ideas
FilterExpression=Attr('createdBy').eq('Ideias Segmentadas 2x8')

# Only generic ideas
FilterExpression=Attr('createdBy').begins_with('Sugestões Genéricas')
```

**Dry-run first:**
```bash
# Preview before inserting
python scripts/insert-segment-ideas.py --dry-run
```

**Windows encoding fix:**
All scripts include Windows UTF-8 encoding fix for emoji support.
