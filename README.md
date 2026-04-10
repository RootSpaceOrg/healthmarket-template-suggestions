# HealthMarket - Gerador de Sugestões de Templates

Sistema para gerar sugestões automatizadas de templates de marketing para diferentes segmentos de saúde.

## 📋 Descrição

Este projeto contém scripts Python para gerar e gerenciar sugestões de templates de marketing personalizados para o ecossistema HealthMarket, incluindo segmentos como:

- Odontologia
- Médicos
- Nutrição
- Fisioterapia
- Psicologia
- Estética
- Farmácias
- Laboratórios

## 🚀 Scripts Disponíveis

### `generate-suggestions.py`
Gera sugestões de ideias de marketing e insere no DynamoDB.

**Uso:**
```bash
# Gerar 10 sugestões aleatórias
python scripts/generate-suggestions.py --count 10

# Gerar 5 sugestões para um segmento específico
python scripts/generate-suggestions.py --count 5 --segment odontologia

# Testar sem inserir no banco (dry-run)
python scripts/generate-suggestions.py --count 3 --dry-run
```

### `insert-segment-ideas.py`
Insere ideias específicas de um segmento no DynamoDB.

### `check-suggestions.py`
Verifica sugestões existentes no banco de dados.

### `check-segment-ideas.py`
Verifica ideias específicas de segmentos.

## ⚙️ Configuração

### Pré-requisitos
- Python 3.7+
- AWS CLI configurado
- Perfil AWS: `healthmarket-prod`
- Região: `sa-east-1`

### Instalação
```bash
pip install boto3
```

### Credenciais AWS
Configure o perfil AWS com as credenciais apropriadas:
```bash
aws configure --profile healthmarket-prod
```

## 📊 Templates Disponíveis

O sistema suporta 5 tipos de templates:
1. **Hero/Banner** - Banners full-screen com CTA
2. **Post único** - Layout com imagem + texto
3. **Texto + parágrafo + Imagem** - Landing page completa
4. **Post com 2 imagens** - Galeria comparativa
5. **Coluna única** - Layout simples e direto

## 🎨 Configurações de Estilo

### Copy Tones
formal, casual, educativo, inspiracional, autoritativo, empático, urgente, divertido, storytelling, minimalista

### Visual Styles
fotorrealista, ilustração, minimalista, corporativo, bold_vibrante, flat_design, moderno_tech, organico_natural, elegante_premium, energético

## 📁 Estrutura

```
.
├── scripts/
│   ├── generate-suggestions.py      # Gerador principal
│   ├── insert-segment-ideas.py      # Inserção por segmento
│   ├── check-suggestions.py         # Verificação de sugestões
│   └── check-segment-ideas.py       # Verificação por segmento
├── references/
│   ├── dynamodb-schema.md           # Schema da tabela DynamoDB
│   └── segment-ideas.md             # Ideias por segmento
├── SKILL.md                         # Documentação da skill
└── README.md                        # Este arquivo
```

## 🔧 Desenvolvimento

Este projeto faz parte do ecossistema Clawdbot como uma skill reutilizável, mas pode ser executado de forma standalone via Python.

## 📝 Licença

Propriedade de HealthMarket - Uso interno.
