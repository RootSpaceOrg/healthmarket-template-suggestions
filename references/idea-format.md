# Formato do campo `idea` — o que a Lambda espera

O `idea` gravado na `AIRequestsTable` e consumido pela Lambda
**`mkt-platform-lambda-ai-idea-to-template`**
(`app/Utils/prompt_templates.py`). Entender como ela usa o `idea` define como a skill
deve escreve-lo.

## O `idea` e um BRIEF, nao a copy final

A Lambda escreve a copy de cada elemento do template sozinha. O `idea` entra cru em 3 prompts:

| Prompt | Onde | Papel do `idea` |
|--------|------|-----------------|
| `BRIEFING_HUMAN_PROMPT_TEMPLATE` | gera o briefing | extrai `campaign_angle`, `target_audience`, `core_benefit`, `main_hook`, `narrative_arc`, `visual_anchor`, `style_anchor` |
| `COPY_HUMAN_PROMPT_TEMPLATE_V2` | gera a copy dos slides | contexto + ideia do cliente |
| `TITLE_GENERATION_HUMAN_PROMPT` | gera o titulo (<=40 chars) | contexto |

Entradas dinamicas que **acompanham** o `idea` (a skill nao precisa duplicar no texto):
`copyTone` (vira instrucao de tom), `businessType` (vira `especializado em {business_type}`),
`imageStyle`, e a `description` do template base.

## O `idea` deve conter (= o que o briefing extrai)

- **Angulo unico** (diferencia do concorrente) — minimo conceito forte, nao generico.
- **Audiencia especifica** — nunca "todos"/"para voce".
- **Beneficio concreto/mensuravel** — nao adjetivo vazio.
- **Hook do slide 1** — para o scroll.
- **Specifics** — 2-3 ancoras concretas (numero, prazo, cenario, objecao).
- **Direcao do arco** — alinhada a `description` do template base.
- **CTA pretendido** — especifico do servico.

## Regras inviolaveis (a Lambda rejeita)

1. **Anti-AI-slop.** Frase que serve a qualquer marca = rejeitada. Ancore em specific concreto.
2. **Frases globalmente proibidas** (`GLOBAL_FORBIDDEN_PHRASES`): `aproveite`, `saiba mais`,
   `clique aqui`, `nao perca`, `o melhor do mercado`, `qualidade incomparavel`,
   `a sua escolha certa`, `para voce`, `venha conhecer`, `tudo o que voce precisa`,
   `a solucao perfeita`, `feito sob medida para voce`. Nao use no `idea` nem sugira como CTA.
3. **Sem emoji** salvo se o elemento pedir.
4. **Nao escreva a copy literal slide-a-slide** — de direcao; a Lambda escreve.

## Tons e estilos validos

`copyTone`: formal · casual · educativo · inspiracional · autoritativo · empatico · urgente ·
divertido · storytelling · minimalista (mapeados em `TONE_INSTRUCTIONS`).

`imageStyle`: fotorrealista · ilustracao · minimalista · corporativo · bold_vibrante ·
flat_design · moderno_tech · organico_natural · elegante_premium · energetico.

## Bom vs. ruim (exemplo)

**Ruim (copy literal + generico):**
> "Slide 1: 'Laserterapia: a solucao perfeita para voce!'. Slide 2: aproveite nossos resultados incriveis..."
(usa frases proibidas, escreve copy final, angulo generico)

**Bom (brief com direcao):**
> "Angulo: laserterapia para dor lombar cronica em adultos 40+ que ja tentaram fisioterapia sem
> resultado duradouro. Beneficio: alivio perceptivel nas primeiras sessoes, sem medicacao continua.
> Hook: contrapor a crenca de que 'dor nas costas e para sempre'. Specifics: protocolo ajustado por
> avaliacao, numero de sessoes tipico, retorno a atividades do dia a dia. Arco antes/depois em 4
> slides conforme o template base. CTA: agendar avaliacao."
