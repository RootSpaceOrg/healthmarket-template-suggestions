# AIRequestsTable Schema

## Estrutura

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `requestId` | String (PK) | UUID v4 único |
| `idea` | String | Descrição completa da ideia (layout, cores, copy, CTA) |
| `templateId` | String | ID do template AI base no Supabase |
| `businessType` | String | Segmento (odontologia, medicos, nutricao, etc) |
| `copyTone` | String | educativo \| empatico \| urgente \| autoritativo \| inspiracional |
| `imageStyle` | String | fotorrealista \| ilustracao \| minimalista \| corporativo \| organico_natural \| elegante_premium |
| `status` | String | waiting \| processing \| completed \| failed |
| `createdBy` | String | Identificador da origem (ex: "Ideias Segmentadas 2x8") |
| `createdAt` | String | ISO timestamp |
| `updatedAt` | String | ISO timestamp |
| `copyLLM` | Object | `{ provider: "bedrock", model: "..." }` |
| `imageLLM` | Object | `{ provider: "openrouter", model: "..." }` |
| `executionArn` | String | ARN do Step Functions (quando processando) |
| `error` | String | Mensagem de erro (se falhar) |
| `generatedTemplateId` | String | ID do template gerado (quando completo) |

## LLM Defaults

```json
{
  "copyLLM": {
    "provider": "bedrock",
    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
  },
  "imageLLM": {
    "provider": "openrouter",
    "model": "google/gemini-3-pro-image-preview"
  }
}
```

## Segmentos Disponíveis

- 🦷 odontologia
- 🏥 medicos
- 🥗 nutricao
- 🧘 fisioterapia
- 🧠 psicologia
- 💆 estetica
- 💊 farmacias
- 🔬 laboratorios
