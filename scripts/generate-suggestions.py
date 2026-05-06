#!/usr/bin/env python3
"""
Script para gerar sugestões de ideias de marketing e inserir no DynamoDB.

Fonte de contexto dos templates:
- Busca templates no Supabase via credenciais do Parameter Store
- Filtra por template_type=ai, status=published e user_id/userId=public
- Usa o campo description dos templates como contexto para gerar sugestões

Uso:
    python scripts/generate-suggestions.py --count 10
    python scripts/generate-suggestions.py --count 5 --segment odontologia
"""

import boto3
import uuid
import argparse
from datetime import datetime, timezone
import random
import json
import urllib.parse
import urllib.request

# Configurações AWS
AWS_PROFILE = 'healthmarket-prod'
DYNAMODB_TABLE = 'AIRequestsTable'
AWS_REGION = 'sa-east-1'
PARAMETER_NAME = 'supabase-database-credentials'

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

BUSINESS_TYPE_BY_SEGMENT = {
    'medicos': 'medical-clinic',
    'laboratorios': 'laboratory',
    'farmacias': 'pharmacy',
    'nutricao': 'nutrition',
    'fisioterapia': 'physiotherapy',
    'psicologia': 'psychology',
    'odontologia': 'dentistry',
    'estetica': 'aesthetics',
    'laserterapia': 'laserterapy',
    'laserterapy': 'laserterapy',
    'generico': '',
    'genérico': '',
    'generic': '',
}

def load_supabase_credentials(session):
    """Carrega credenciais do Supabase a partir do Parameter Store."""
    ssm = session.client('ssm', region_name=AWS_REGION)
    response = ssm.get_parameter(Name=PARAMETER_NAME, WithDecryption=True)
    raw_value = response['Parameter']['Value']

    try:
        data = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Parametro '{PARAMETER_NAME}' nao contem JSON valido"
        ) from exc

    url = data.get('url') or data.get('supabaseUrl') or data.get('SUPABASE_URL')
    api_key = (
        data.get('key')
        or data.get('anonKey')
        or data.get('publishableKey')
        or data.get('apiKey')
        or data.get('SUPABASE_ANON_KEY')
        or data.get('SUPABASE_PUBLISHABLE_KEY')
    )

    if not url or not api_key:
        raise RuntimeError(
            f"Credenciais incompletas em '{PARAMETER_NAME}' (url/api key ausentes)"
        )

    return url.rstrip('/'), api_key


def fetch_templates_from_supabase(supabase_url, api_key):
    """Busca templates e aplica filtros exigidos (ai/published/public)."""
    base_url = f"{supabase_url}/rest/v1/templates"

    query = {
        'select': '*',
        'template_type': 'eq.ai',
        'status': 'eq.published'
    }

    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }

    request_url = f"{base_url}?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(request_url, headers=headers, method='GET')

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode('utf-8'))
    except Exception as exc:
        raise RuntimeError(f'Erro ao buscar templates no Supabase: {exc}') from exc

    if not isinstance(payload, list):
        raise RuntimeError('Resposta inesperada do Supabase ao buscar templates')

    filtered = []
    for t in payload:
        uid = t.get('user_id', t.get('userId'))
        if uid != 'public':
            continue
        if not t.get('description'):
            continue
        if not t.get('id'):
            continue
        filtered.append({
            'id': t.get('id'),
            'name': t.get('name') or 'Template sem nome',
            'description': str(t.get('description')).strip(),
        })

    if not filtered:
        raise RuntimeError(
            'Nenhum template encontrado no Supabase com filtros '
            '(template_type=ai, status=published, user_id/userId=public).'
        )

    return filtered


def build_idea_from_template(template, segment=None):
    """Gera ideia usando description do template como contexto principal."""
    theme = random.choice([
        'educativo', 'promocional', 'institucional', 'sazonal', 'prova social'
    ])
    cta = random.choice([
        'Agende sua avaliação',
        'Fale com a equipe no WhatsApp',
        'Salve este post para consultar depois',
        'Compartilhe com quem precisa'
    ])

    segment_prefix = f"[{segment.title()}] " if segment else ""
    description = template['description'].replace('\n', ' ').strip()

    return (
        f"{segment_prefix}Crie um conteúdo para Instagram no tema {theme}, "
        f"aproveitando a estrutura do template '{template['name']}'. "
        f"Contexto visual/estrutural do template: {description}. "
        f"Inclua título forte, texto principal objetivo, elemento de prova social "
        f"(dado/depoimento) e CTA final: '{cta}'."
    )

def generate_suggestion_item(template, segment=None):
    """Gera um item de sugestão completo"""
    now = datetime.now(timezone.utc).isoformat()

    # Seleciona valores aleatórios
    copy_tone = random.choice(COPY_TONES)
    visual_style = random.choice(VISUAL_STYLES)

    # Gera ideia baseada no tipo de template
    idea = build_idea_from_template(template, segment)

    business_type = ''
    if segment:
        business_type = BUSINESS_TYPE_BY_SEGMENT.get(segment.strip().lower(), '')

    item = {
        'requestId': str(uuid.uuid4()),
        'idea': idea,
        'templateId': template['id'],
        'businessType': business_type,  # Vazio para templates genéricos
        'copyTone': copy_tone,
        'imageStyle': visual_style,
        'status': 'waiting',
        'createdBy': 'Sugestão AI (Supabase Context)',
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

    supabase_url, supabase_api_key = load_supabase_credentials(session)
    templates = fetch_templates_from_supabase(supabase_url, supabase_api_key)
    
    suggestions = []
    
    print(f"Gerando {count} sugestoes...")
    print(f"Templates Supabase carregados: {len(templates)}")
    if segment:
        print(f"Segmento: {segment}")
    
    for i in range(count):
        selected_template = random.choice(templates)
        item = generate_suggestion_item(selected_template, segment)
        suggestions.append(item)
        
        print(f"\n[{i+1}/{count}] {item['requestId'][:8]}...")
        print(f"  Ideia: {item['idea'][:60]}...")
        print(f"  Template: {selected_template['name']}")
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
    parser.add_argument(
        '--segment',
        type=str,
        help=(
            'Segmento (odontologia, medicos, nutricao, fisioterapia, psicologia, '
            'estetica, farmacias, laboratorios, laserterapia, generico)'
        )
    )
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
