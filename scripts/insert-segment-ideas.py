#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Insere 16 ideias segmentadas (2 por segmento) na AIRequestsTable

Uso:
    python scripts/insert-segment-ideas.py
    python scripts/insert-segment-ideas.py --dry-run
"""

import boto3
import uuid
import argparse
import sys
from datetime import datetime, timezone

# Fix encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configurações AWS
AWS_PROFILE = 'healthmarket-prod'
DYNAMODB_TABLE = 'AIRequestsTable'
AWS_REGION = 'sa-east-1'

# LLM Configs padrão
DEFAULT_COPY_LLM = {
    "provider": "bedrock",
    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
}

DEFAULT_IMAGE_LLM = {
    "provider": "openrouter",
    "model": "google/gemini-3-pro-image-preview"
}

# 16 ideias segmentadas (2 por segmento)
SEGMENT_IDEAS = [
    # ODONTOLOGIA (2)
    {
        "segment": "odontologia",
        "name": "Sorriso Perfeito em 3 Passos",
        "idea": "[Odontologia] Carrossel educativo mostrando jornada de clareamento dental: Slide 1 com antes/depois impactante, Slide 2 explicando 'Como funciona o clareamento profissional', Slide 3 com lista de cuidados pós-procedimento (evitar café, usar creme dental específico), Slide 4 com depoimento de paciente real com quote inspiradora, Slide 5 finalizando com CTA 'Agende sua avaliação gratuita'. Layout em azul claro + branco transmitindo limpeza e profissionalismo.",
        "templateId": "NYwBsaDvxxCf7jhRP5r71",  # Carrossel 5 slides
        "copyTone": "educativo",
        "imageStyle": "fotorrealista"
    },
    {
        "segment": "odontologia",
        "name": "Dor de Dente? Descubra a Causa",
        "idea": "[Odontologia] Post único com imagem impactante de pessoa tocando o rosto com expressão de desconforto, lupa destacando área dolorida (molares/gengiva). Título em vermelho suave 'Dor ao mastigar pode ser sinal de...', seguido de lista visual com ícones: cárie profunda, sensibilidade dentária, bruxismo, problema na gengiva. Logo da clínica + botão de agendamento urgente 'Agende Avaliação Hoje'. Design clean em vermelho suave + branco para alertar sem alarmar.",
        "templateId": "KG4cOYVzMNTQjYNpWwlGL",  # Post Único Dor + LUPA
        "copyTone": "empatico",
        "imageStyle": "fotorrealista"
    },
    
    # MÉDICOS (2)
    {
        "segment": "medicos",
        "name": "Check-up Anual: O que Incluir?",
        "idea": "[Médicos] Carrossel educativo sobre exames preventivos por faixa etária. Slide 1: Hook 'Quando foi seu último check-up?' com imagem de médico confiável. Slide 2: Card informativo 'Por que fazer prevenção salva vidas'. Slide 3: Lista ilustrada de exames essenciais (hemograma, glicemia, colesterol, tireoide). Slide 4: '5 benefícios da medicina preventiva' com ícones. Slide 5: 'Mitos vs Verdades sobre check-up'. Slide 6: CTA com logo + telefone/WhatsApp. Verde institucional + branco transmitindo confiança médica.",
        "templateId": "WdnGN8TFNJiBrs-dvAFIv",  # Carrossel 6 slides
        "copyTone": "autoritativo",
        "imageStyle": "corporativo"
    },
    {
        "segment": "medicos",
        "name": "Hipertensão Silenciosa",
        "idea": "[Médicos] Página 1: Estatística impactante em grande destaque '1 em 4 brasileiros tem hipertensão e não sabe' com imagem de coração em vermelho escuro + gráfico visual simples. Página 2: Card branco centralizado com checklist de sinais de alerta (dor de cabeça frequente, tontura, visão turva, falta de ar) + botão vermelho 'Meça sua pressão gratuitamente'. Design vermelho escuro + cinza claro criando urgência controlada e seriedade médica.",
        "templateId": "5lJG7rIwdD4w3o58nKJOt",  # 2 Pages Hero + CTA
        "copyTone": "urgente",
        "imageStyle": "minimalista"
    },
    
    # NUTRIÇÃO (2)
    {
        "segment": "nutricao",
        "name": "Mitos sobre Carboidratos",
        "idea": "[Nutrição] Carrossel desmistificando dietas low-carb. Slide 1: Hero com prato colorido equilibrado (arroz integral, legumes, proteína). Slide 2: Card destacado 'Mito 1: Carboidrato engorda' com explicação científica clara. Slide 3: 'Mito 2: Cortar carbo emagrece rápido' + foto de alimentos integrais saudáveis. Slide 4: Conclusão 'O segredo está na QUALIDADE, não na exclusão' + CTA 'Consulta nutricional personalizada'. Verde limão + laranja transmitindo energia e frescor natural.",
        "templateId": "A7nW1IacAIV-nlq6zBP63",  # Carrossel 4 slides
        "copyTone": "educativo",
        "imageStyle": "organico_natural"
    },
    {
        "segment": "nutricao",
        "name": "Prato Equilibrado: Guia Visual",
        "idea": "[Nutrição] Post educativo com logo no topo. Galeria com 2 imagens lado a lado: primeira mostrando prato dividido visualmente (50% vegetais coloridos, 25% proteína magra, 25% carboidrato integral), segunda imagem mostrando exemplos reais de cada grupo alimentar. Título 'Monte seu prato ideal' em destaque. Texto 1 explicando proporções nutricionais. Texto 2 com dicas práticas de substituições saudáveis. Verde musgo + bege natural criando conexão com alimentação natural.",
        "templateId": "xkzg3dYYVJCuaW98uUEYq",  # Post único 2 imagens
        "copyTone": "educativo",
        "imageStyle": "organico_natural"
    },
    
    # FISIOTERAPIA (2)
    {
        "segment": "fisioterapia",
        "name": "5 Alongamentos para Dor nas Costas",
        "idea": "[Fisioterapia] Carrossel prático com exercícios ilustrados. Slide 1: Hook 'Trabalha sentado? Esses alongamentos são pra você' com imagem de pessoa no escritório com postura ruim. Slides 2-5: Um alongamento por slide com ilustração clara da posição + timer (segurar 30seg) + benefício específico (libera lombar, relaxa ombros, etc). Slide 6: 'Salve este post e pratique diariamente' + logo da clínica + CTA. Azul petróleo + cinza claro transmitindo calma profissional e bem-estar.",
        "templateId": "WdnGN8TFNJiBrs-dvAFIv",  # Carrossel 6 slides
        "copyTone": "educativo",
        "imageStyle": "ilustracao"
    },
    {
        "segment": "fisioterapia",
        "name": "Lesão no Joelho: Quando Procurar Ajuda?",
        "idea": "[Fisioterapia] Post urgente com imagem de joelho com marcação anatômica destacando ligamentos/menisco. Título em laranja 'Ignorar pode piorar a lesão'. Lista visual de sintomas graves que exigem atenção: inchaço persistente (>48h), impossibilidade de apoiar peso, estalos com dor, instabilidade ao caminhar. Texto explicativo sobre diagnóstico precoce. CTA urgente mas não alarmista 'Agende avaliação gratuita'. Laranja + branco criando atenção sem pânico.",
        "templateId": "thuvZfxTxWaK-wnvzswj4",  # Post Único Dor
        "copyTone": "urgente",
        "imageStyle": "ilustracao"
    },
    
    # PSICOLOGIA (2)
    {
        "segment": "psicologia",
        "name": "Ansiedade x Estresse: Qual a Diferença?",
        "idea": "[Psicologia] Carrossel educativo sobre saúde mental. Slide 1: Pergunta provocativa 'Você sabe diferenciar ansiedade de estresse?' com imagem acolhedora. Slide 2: Card 'Ansiedade é...' com definição acessível e sintomas comuns. Slide 3: Card 'Estresse é...' com definição e características. Slide 4: Quadro comparativo lado a lado (causas, sintomas físicos, duração). Slide 5: CTA empático 'Precisa conversar? Agende sessão acolhedora'. Roxo suave + rosa claro transmitindo acolhimento e serenidade.",
        "templateId": "NYwBsaDvxxCf7jhRP5r71",  # Carrossel 5 slides
        "copyTone": "empatico",
        "imageStyle": "minimalista"
    },
    {
        "segment": "psicologia",
        "name": "Burnout Não é Frescura",
        "idea": "[Psicologia] Página 1: Dados impactantes da OMS sobre burnout + ilustração sensível de pessoa exausta/sobrecarregada. Título 'Reconheça os sinais antes que seja tarde'. Página 2: Card branco com checklist honesto de sintomas (exaustão crônica, cinismo, redução de eficácia, isolamento social, sintomas físicos) + botão acolhedor 'Buscar ajuda é força, não fraqueza'. Azul escuro + amarelo equilibrando seriedade com esperança e acolhimento.",
        "templateId": "5lJG7rIwdD4w3o58nKJOt",  # 2 Pages Hero + CTA
        "copyTone": "empatico",
        "imageStyle": "ilustracao"
    },
    
    # ESTÉTICA (2)
    {
        "segment": "estetica",
        "name": "Antes e Depois: Harmonização Facial",
        "idea": "[Estética] Carrossel de resultados com ética visual. Slide 1: Foto antes (levemente desfocada nas áreas sensíveis, respeitando privacidade). Slide 2: Foto depois mostrando resultado natural e harmônico. Slide 3: Explicação técnica do procedimento (áreas tratadas, tipo de preenchimento, técnica utilizada). Slide 4: Depoimento genuíno da paciente sobre experiência + CTA 'Avaliação gratuita com especialista'. Rosa gold + branco transmitindo sofisticação e naturalidade premium.",
        "templateId": "A7nW1IacAIV-nlq6zBP63",  # Carrossel 4 slides
        "copyTone": "inspiracional",
        "imageStyle": "elegante_premium"
    },
    {
        "segment": "estetica",
        "name": "Skincare: Rotina Matinal em 4 Passos",
        "idea": "[Estética] Post educativo com imagem de produtos skincare alinhados em ordem de uso. Hero com ambiente clean e luminoso. Título 'Pele saudável começa pela manhã' em destaque. Numeração clara visual: 1-Limpeza (por que e como), 2-Tônico (benefícios), 3-Sérum (ativos essenciais), 4-Protetor solar (não negociável). Texto com dicas de aplicação correta. Elemento visual lateral com ilustração de pele absorvendo produtos. Verde menta + branco transmitindo frescor e limpeza.",
        "templateId": "_RFWfXL-V7hi-EQ5X-gZv",  # Post Único imagem
        "copyTone": "educativo",
        "imageStyle": "minimalista"
    },
    
    # FARMÁCIAS (2)
    {
        "segment": "farmacias",
        "name": "Antibiótico: 5 Erros que Você Comete",
        "idea": "[Farmácias] Carrossel educativo sobre uso consciente de medicamentos. Slide 1: Hook urgente 'Você faz isso? Pode ser perigoso'. Slides 2-5: Um erro por slide com ícone X vermelho: Erro 1-Parar antes do fim do tratamento, Erro 2-Tomar sem prescrição, Erro 3-Compartilhar antibiótico, Erro 4-Misturar com álcool, Erro 5-Armazenar incorretamente. Slide 6: 'Dúvidas? Fale com nosso farmacêutico gratuitamente' + contato. Verde farmácia + branco transmitindo confiança e saúde.",
        "templateId": "WdnGN8TFNJiBrs-dvAFIv",  # Carrossel 6 slides
        "copyTone": "autoritativo",
        "imageStyle": "corporativo"
    },
    {
        "segment": "farmacias",
        "name": "Vitamina D: Quem Precisa Suplementar?",
        "idea": "[Farmácias] Post educativo com logo. Galeria: Imagem 1 mostrando pessoa tomando sol pela manhã (fonte natural), Imagem 2 mostrando suplemento de vitamina D3 (fonte complementar). Título 'Sol não é suficiente para todos'. Texto 1 explicando grupos de risco (idosos, pele escura, pouca exposição solar, gestantes). Texto 2 sobre importância para imunidade e ossos + CTA 'Consulte nosso farmacêutico para orientação'. Amarelo vibrante + azul claro equilibrando sol com confiança profissional.",
        "templateId": "xkzg3dYYVJCuaW98uUEYq",  # Post único 2 imagens
        "copyTone": "educativo",
        "imageStyle": "fotorrealista"
    },
    
    # LABORATÓRIOS (2)
    {
        "segment": "laboratorios",
        "name": "Prepare-se para o Exame de Sangue",
        "idea": "[Laboratórios] Carrossel informativo sobre orientações pré-exame. Slide 1: 'Vai fazer exame de sangue?' com imagem profissional e acolhedora. Slide 2: 'Entenda: Jejum de 12h? Nem sempre!' explicando diferenças por tipo de exame. Slide 3: Lista de cuidados 24h antes (hidratação, evitar exercício intenso, medicamentos). Slide 4: Checklist visual 'O que pode / O que não pode' antes do exame. Slide 5: CTA 'Agende online com resultados em 24h' + logo. Azul royal + branco transmitindo confiança científica.",
        "templateId": "NYwBsaDvxxCf7jhRP5r71",  # Carrossel 5 slides
        "copyTone": "educativo",
        "imageStyle": "corporativo"
    },
    {
        "segment": "laboratorios",
        "name": "Exame de Tireoide: Quando Pedir?",
        "idea": "[Laboratórios] Post educativo com ilustração anatômica clean da glândula tireoide. Título 'Cansaço extremo pode ser sinal de problema na tireoide'. Lista visual de sintomas que indicam necessidade de exame: fadiga persistente, ganho/perda de peso inexplicável, alterações de humor, queda de cabelo, sensibilidade ao frio/calor. Breve explicação do TSH (hormônio indicador). CTA 'Solicite ao seu médico e agende conosco' com logo. Roxo institucional + cinza transmitindo ciência e profissionalismo.",
        "templateId": "3RNGeYMJJ202rHxHM6WHw",  # Post Único Dor 2
        "copyTone": "educativo",
        "imageStyle": "ilustracao"
    }
]

def insert_ideas(dry_run=False):
    """Insere as 16 ideias segmentadas na AIRequestsTable"""
    
    if not dry_run:
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        dynamodb = session.resource('dynamodb')
        table = dynamodb.Table(DYNAMODB_TABLE)
    
    now = datetime.now(timezone.utc).isoformat()
    items_to_insert = []
    
    print(f"📝 Preparando {len(SEGMENT_IDEAS)} ideias segmentadas...\n")
    
    for idx, idea_data in enumerate(SEGMENT_IDEAS, 1):
        item = {
            'requestId': str(uuid.uuid4()),
            'idea': idea_data['idea'],
            'templateId': idea_data['templateId'],
            'businessType': idea_data['segment'],  # Usa segmento como businessType
            'copyTone': idea_data['copyTone'],
            'imageStyle': idea_data['imageStyle'],
            'status': 'waiting',
            'createdBy': 'Ideias Segmentadas 2x8',
            'createdAt': now,
            'updatedAt': now,
            'copyLLM': DEFAULT_COPY_LLM,
            'imageLLM': DEFAULT_IMAGE_LLM,
            'executionArn': None,
            'error': None,
            'generatedTemplateId': None
        }
        
        items_to_insert.append(item)
        
        # Log detalhado
        segment_emoji = {
            'odontologia': '🦷',
            'medicos': '🏥',
            'nutricao': '🥗',
            'fisioterapia': '🧘',
            'psicologia': '🧠',
            'estetica': '💆',
            'farmacias': '💊',
            'laboratorios': '🔬'
        }
        
        emoji = segment_emoji.get(idea_data['segment'], '📋')
        print(f"[{idx:2d}/16] {emoji} {idea_data['segment'].upper()}")
        print(f"  📌 {idea_data['name']}")
        print(f"  🆔 {item['requestId'][:8]}...")
        print(f"  📋 Template: {idea_data['templateId'][:8]}...")
        print(f"  ✍️  {idea_data['copyTone']} | 🎨 {idea_data['imageStyle']}")
        print()
    
    if dry_run:
        print("⚠️  [DRY RUN] Nenhum item foi inserido no DynamoDB\n")
        return items_to_insert
    
    # Inserção em batch
    print("💾 Inserindo no DynamoDB...")
    
    try:
        with table.batch_writer() as batch:
            for item in items_to_insert:
                batch.put_item(Item=item)
        
        print(f"✅ {len(items_to_insert)} ideias inseridas com sucesso!\n")
        
    except Exception as e:
        print(f"❌ Erro ao inserir: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    # Resumo
    print("=" * 60)
    print("📊 RESUMO:")
    print(f"  Total inserido: {len(items_to_insert)}")
    print(f"  Segmentos: {len(set(i['businessType'] for i in items_to_insert))}")
    print(f"  Templates usados: {len(set(i['templateId'] for i in items_to_insert))}")
    print(f"  Tones variados: {len(set(i['copyTone'] for i in items_to_insert))}")
    print(f"  Styles variados: {len(set(i['imageStyle'] for i in items_to_insert))}")
    print("=" * 60)
    
    # Breakdown por segmento
    print("\n📋 Por Segmento:")
    segments = {}
    for item in items_to_insert:
        seg = item['businessType']
        segments[seg] = segments.get(seg, 0) + 1
    
    for seg, count in sorted(segments.items()):
        emoji = segment_emoji.get(seg, '📋')
        print(f"  {emoji} {seg.capitalize()}: {count} ideias")
    
    print()
    return items_to_insert

def main():
    parser = argparse.ArgumentParser(
        description='Insere 16 ideias segmentadas (2 por segmento) na AIRequestsTable'
    )
    parser.add_argument('--dry-run', action='store_true', 
                       help='Simula sem inserir no DynamoDB')
    
    args = parser.parse_args()
    
    try:
        insert_ideas(dry_run=args.dry_run)
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
