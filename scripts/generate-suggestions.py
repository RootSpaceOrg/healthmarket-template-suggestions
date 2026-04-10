#!/usr/bin/env python3
"""
Script para gerar sugestões de ideias de marketing e inserir no DynamoDB.

Uso:
    python scripts/generate-suggestions.py --count 10
    python scripts/generate-suggestions.py --count 5 --segment odontologia
"""

import boto3
import uuid
import argparse
from datetime import datetime, timezone
import random

# Configurações AWS
AWS_PROFILE = 'healthmarket-prod'
DYNAMODB_TABLE = 'AIRequestsTable'
AWS_REGION = 'sa-east-1'

# Templates AI disponíveis (publicados) com descrições completas
TEMPLATES = [
    {
        "id": "KLUsr-oI1xrrs1Q6jZJgs",
        "name": "Hero/Banner",
        "type": "hero",
        "description": "Banner hero em tela cheia com imagem de fundo e sobreposição de texto (título + subtítulo). Ideal para landing pages, comunicação rápida de ofertas ou campanhas.",
        "elements": ["imagem de fundo", "título destacado", "subtítulo", "CTA"]
    },
    {
        "id": "_RFWfXL-V7hi-EQ5X-gZv",
        "name": "Post único (imagem + título + parágrafo)",
        "type": "post",
        "description": "Layout hero/banner com área de imagem substituível + bloco de conteúdo em duas colunas (texto descritivo + elemento visual). Para apresentar serviços/campanhas e incentivar ação.",
        "elements": ["imagem principal", "título", "descrição", "elemento visual lateral"]
    },
    {
        "id": "WM42V_UBvD1C9BQc4A_4O",
        "name": "Texto + parágrafo + Imagem",
        "type": "landing",
        "description": "Landing page completa com múltiplas seções: cabeçalho (logo), área hero com título + descrições, bloco de conteúdo auxiliar, cartão de CTA destacado e imagem principal com sobreposição de profissional.",
        "elements": ["logo", "título hero", "descrições", "bloco conteúdo", "CTA destacado", "imagem profissional"]
    },
    {
        "id": "xkzg3dYYVJCuaW98uUEYq",
        "name": "Post único (2 imagens + título + 2 textos)",
        "type": "gallery",
        "description": "Layout em três níveis: cabeçalho com logo, galeria com duas imagens lado a lado (feature cards) e área de título seguida de blocos de texto. Adequado para comparações, antes/depois ou apresentação de benefícios.",
        "elements": ["logo", "2 imagens lado a lado", "título destaque", "2 blocos de texto"]
    },
    {
        "id": "nuv0S6gQqTO6vTnYWYz32",
        "name": "Coluna única",
        "type": "simple",
        "description": "Template simples de coluna única com cabeçalho/texto no topo e imagem centralizada como hero. Facilita leitura rápida e foco visual. Ideal para materiais educativos, e-mails ou posts diretos.",
        "elements": ["cabeçalho/texto", "imagem hero centralizada"]
    }
]

# Copy Tones disponíveis
COPY_TONES = [
    'formal',           # Profissional, corporativo
    'casual',           # Leve, descontraído
    'educativo',        # Informativo, didático
    'inspiracional',    # Motivador, emocional
    'autoritativo',     # Especialista, confiável
    'empatico',         # Acolhedor, compreensivo
    'urgente',          # Ação imediata, FOMO
    'divertido',        # Bem-humorado, leve
    'storytelling',     # Narrativo, história
    'minimalista'       # Direto ao ponto, conciso
]

# Visual Styles disponíveis
VISUAL_STYLES = [
    'fotorrealista',      # Fotos realistas, alta fidelidade
    'ilustracao',         # Ilustrações artísticas
    'minimalista',        # Clean, espaços vazios, minimal
    'corporativo',        # Profissional, sóbrio, confiável
    'bold_vibrante',      # Cores fortes, alto contraste
    'flat_design',        # Design plano, 2D
    'moderno_tech',       # Gradientes, glassmorphism, futurista
    'organico_natural',   # Tons terrosos, texturas naturais
    'elegante_premium',   # Sofisticado, luxuoso
    'energetico'          # Dinâmico, movimento, ação
]

# LLM Configs padrão
DEFAULT_COPY_LLM = {
    "provider": "bedrock",
    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
}

DEFAULT_IMAGE_LLM = {
    "provider": "openrouter",
    "model": "google/gemini-3-pro-image-preview"
}

# Ideias detalhadas por tipo de template
IDEAS_BY_TYPE = {
    "hero": [
        "Campanha Janeiro Branco - Banner impactante com fundo em tons de azul/branco mostrando pessoa em meditação, título 'Sua Saúde Mental Importa' em destaque e subtítulo 'Agende sua primeira consulta com 30% de desconto'. CTA 'Fale com um Especialista'",
        "Outubro Rosa 2026 - Hero em rosa vibrante com imagem de mulheres diversas em abraço solidário, título 'Prevenir é Viver', subtítulo descrevendo pacote completo de exames preventivos. CTA 'Agende Seu Check-up'",
        "Tecnologia de Ponta Chegou - Fundo tech com gradientes modernos, imagem de equipamento médico inovador, título 'Diagnósticos Mais Precisos em Menos Tempo', subtítulo explicando nova tecnologia disponível. CTA 'Conheça a Novidade'",
        "Black Friday da Saúde - Banner urgente com cores vibrantes, imagem de profissionais sorrindo, título '48h de Ofertas Imperdíveis', subtítulo com pacotes de exames/consultas com descontos. CTA 'Aproveite Agora'",
        "Telemedicina 24/7 - Hero minimalista com ilustração de médico em videochamada, título 'Atendimento Online Quando Você Precisar', subtítulo destacando conveniência e qualidade. CTA 'Agende Online'"
    ],
    "post": [
        "Alimentação e Longevidade - Post educativo com imagem de prato colorido e balanceado no topo, título '5 Alimentos que Aumentam sua Expectativa de Vida', parágrafo explicando benefícios de cada um com ícones ilustrativos ao lado",
        "Postura no Home Office - Imagem principal mostrando setup ergonômico, título 'Dores nas Costas? Pode ser sua Mesa', descrição detalhada sobre ergonomia com ilustração de postura correta/incorreta ao lado",
        "Hidratação Inteligente - Post com imagem de pessoa bebendo água em ambiente saudável, título 'Você Está Bebendo Água o Suficiente?', texto explicativo com calculadora de necessidade diária e dicas práticas",
        "Sono de Qualidade - Imagem de quarto relaxante com iluminação suave, título '7 Segredos para Dormir Melhor', descrição com lista de hábitos noturnos e ilustração de ciclo do sono",
        "Vitamina D e Imunidade - Post com imagem de pessoa tomando sol pela manhã, título 'O Poder da Vitamina D na sua Imunidade', texto educativo sobre importância e fontes com gráfico ilustrativo"
    ],
    "landing": [
        "Clínica de Prevenção Cardiovascular - Landing completa com logo no topo, hero 'Proteja seu Coração', descrição dos serviços (check-up, acompanhamento, exames), bloco sobre equipe especializada, cartão CTA 'Agende Avaliação Gratuita', imagem de cardiologista confiável",
        "Centro de Estética Avançada - Logo premium, hero 'Beleza Natural com Ciência', descrições de tratamentos (harmonização, peeling, skincare), bloco de resultados/depoimentos, CTA destacado 'Agende Avaliação', foto de profissional em ambiente moderno",
        "Clínica Odontológica Especializada - Logo clean, hero 'Seu Sorriso Merece o Melhor', descrição de especialidades (implantes, ortodontia, clareamento), bloco sobre tecnologia 3D, CTA 'Primeira Consulta Grátis', imagem de dentista sorridente",
        "Fisioterapia Personalizada - Logo institucional, hero 'Movimento sem Dor', descrições de modalidades (ortopédica, esportiva, RPG), bloco sobre equipamentos modernos, CTA 'Avaliação Gratuita', foto de fisioterapeuta atendendo",
        "Nutrição Funcional - Logo clean, hero 'Transforme sua Relação com a Comida', descrição de abordagem personalizada, bloco sobre resultados comprovados, CTA 'Consulte um Especialista', imagem de nutricionista confiante"
    ],
    "gallery": [
        "Antes e Depois Ortodontia - Logo no topo, duas imagens lado a lado mostrando sorriso antes/depois de tratamento, título 'Transformações Reais em 12 Meses', texto 1 explicando processo e texto 2 sobre tecnologia invisível usada",
        "Comparativo Tratamentos Faciais - Logo, galeria com foto de rosto antes/depois de procedimento estético, título 'Harmonização Facial Natural', bloco 1 descrevendo técnica e bloco 2 sobre durabilidade dos resultados",
        "Resultados Emagrecimento - Logo, duas fotos de corpo inteiro mostrando evolução de paciente, título 'Perca Peso com Saúde', texto 1 sobre método nutricional e texto 2 sobre acompanhamento multidisciplinar",
        "Reabilitação Pós-Cirurgia - Logo, imagens mostrando progresso de mobilidade (semana 1 vs 8), título 'Recuperação Completa e Segura', texto 1 sobre protocolo personalizado e texto 2 sobre equipamentos utilizados",
        "Clareamento Dental Profissional - Logo, galeria antes/depois de sorriso clareado, título 'Dentes Brancos sem Sensibilidade', bloco 1 explicando técnica e bloco 2 sobre manutenção dos resultados"
    ],
    "simple": [
        "Dica Rápida de Saúde - Texto no topo: 'Você sabia que caminhar 30min por dia reduz risco cardíaco em 40%?', imagem centralizada de pessoa caminhando ao ar livre em momento inspirador",
        "Alerta de Sintoma - Cabeçalho: 'Atenção: dor de cabeça persistente pode ser sinal de hipertensão', imagem hero de pessoa medindo pressão com profissional, design clean e direto",
        "Promoção Relâmpago - Texto simples: 'Hoje: Consulta + Exames por R$150', imagem centralizada de profissional atendendo com sorriso, foco na oferta urgente",
        "Conquista da Clínica - Cabeçalho: 'Atingimos 10.000 vidas transformadas!', imagem hero de equipe comemorando ou pacientes felizes, mensagem de gratidão e convite",
        "Post Motivacional - Texto: 'Pequenas mudanças geram grandes resultados. Comece hoje!', imagem inspiradora de pessoa superando desafio de saúde, mensagem positiva e encorajadora"
    ]
}

def generate_idea(template_type):
    """Gera uma ideia detalhada baseada no tipo de template"""
    ideas = IDEAS_BY_TYPE.get(template_type, IDEAS_BY_TYPE["simple"])
    return random.choice(ideas)

def generate_suggestion_item(segment=None):
    """Gera um item de sugestão completo"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Seleciona valores aleatórios
    template = random.choice(TEMPLATES)
    copy_tone = random.choice(COPY_TONES)
    visual_style = random.choice(VISUAL_STYLES)
    
    # Gera ideia baseada no tipo de template
    idea = generate_idea(template['type'])
    
    # Adiciona contexto de segmento na ideia se especificado
    if segment:
        idea = f"[{segment.title()}] {idea}"
    
    item = {
        'requestId': str(uuid.uuid4()),
        'idea': idea,
        'templateId': template['id'],
        'businessType': '',  # Vazio para ideias genéricas
        'copyTone': copy_tone,
        'imageStyle': visual_style,
        'status': 'waiting',
        'createdBy': 'Sugestão AI',
        'createdAt': now,
        'updatedAt': now,
        'copyLLM': DEFAULT_COPY_LLM,
        'imageLLM': DEFAULT_IMAGE_LLM,
        'executionArn': None,
        'error': None,
        'generatedTemplateId': None
    }
    
    return item

def insert_suggestions(count, segment=None, dry_run=False):
    """Insere sugestões no DynamoDB"""
    
    # Inicializa cliente DynamoDB
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    suggestions = []
    
    print(f"Gerando {count} sugestoes...")
    if segment:
        print(f"Segmento: {segment}")
    
    for i in range(count):
        item = generate_suggestion_item(segment)
        suggestions.append(item)
        
        print(f"\n[{i+1}/{count}] {item['requestId'][:8]}...")
        print(f"  Ideia: {item['idea'][:60]}...")
        print(f"  Template: {next(t['name'] for t in TEMPLATES if t['id'] == item['templateId'])}")
        print(f"  Tone: {item['copyTone']} | Style: {item['imageStyle']}")
    
    if dry_run:
        print("\n[DRY RUN] Nenhum item foi inserido no DynamoDB")
        return suggestions
    
    # Inserção em lote
    print(f"\nInserindo {count} itens no DynamoDB...")
    
    with table.batch_writer() as batch:
        for item in suggestions:
            batch.put_item(Item=item)
    
    print(f"OK - {count} sugestoes inseridas com sucesso!")
    return suggestions

def main():
    parser = argparse.ArgumentParser(description='Gera sugestões de ideias de marketing para HealthMarket')
    parser.add_argument('--count', type=int, required=True, help='Quantidade de sugestões a gerar')
    parser.add_argument('--segment', type=str, help='Segmento específico (ex: odontologia, nutrição)')
    parser.add_argument('--dry-run', action='store_true', help='Simula sem inserir no DynamoDB')
    
    args = parser.parse_args()
    
    if args.count <= 0:
        print("ERRO: --count deve ser maior que 0")
        return
    
    try:
        suggestions = insert_suggestions(args.count, args.segment, args.dry_run)
        
        print("\n" + "="*60)
        print(f"RESUMO:")
        print(f"  Total gerado: {len(suggestions)}")
        print(f"  Templates usados: {len(set(s['templateId'] for s in suggestions))}")
        print(f"  Tones variados: {len(set(s['copyTone'] for s in suggestions))}")
        print(f"  Styles variados: {len(set(s['imageStyle'] for s in suggestions))}")
        
    except Exception as e:
        print(f"ERRO ao gerar sugestoes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
