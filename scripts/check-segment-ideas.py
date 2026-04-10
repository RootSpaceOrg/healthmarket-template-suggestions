#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica ideias segmentadas inseridas na AIRequestsTable"""

import boto3
import sys
from boto3.dynamodb.conditions import Attr

# Fix encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

AWS_PROFILE = 'healthmarket-prod'
DYNAMODB_TABLE = 'AIRequestsTable'
AWS_REGION = 'sa-east-1'

session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
dynamodb = session.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)

print("🔍 Buscando ideias segmentadas na AIRequestsTable...\n")

# Query com filtro para ideias segmentadas
response = table.scan(
    FilterExpression=Attr('createdBy').eq('Ideias Segmentadas 2x8')
)

items = response.get('Items', [])

if not items:
    print("⚠️  Nenhuma ideia segmentada encontrada.")
    print("Execute: python scripts/insert-segment-ideas.py\n")
    exit(0)

print(f"✅ Total encontrado: {len(items)}\n")

# Agrupar por segmento
by_segment = {}
for item in items:
    seg = item.get('businessType', 'sem-segmento')
    if seg not in by_segment:
        by_segment[seg] = []
    by_segment[seg].append(item)

# Emojis por segmento
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

# Mostrar por segmento
for segment in sorted(by_segment.keys()):
    emoji = segment_emoji.get(segment, '📋')
    ideas = by_segment[segment]
    
    print(f"{emoji} {segment.upper()} ({len(ideas)} ideias)")
    print("─" * 70)
    
    for item in ideas:
        print(f"  🆔 {item['requestId'][:8]}... | Status: {item['status']}")
        print(f"  💡 Ideia: {item['idea'][:80]}...")
        print(f"  📋 Template: {item['templateId'][:8]}...")
        print(f"  ✍️  Tone: {item['copyTone']} | 🎨 Style: {item['imageStyle']}")
        print(f"  📅 Criado: {item['createdAt']}")
        print()
    
    print()

# Estatísticas
print("=" * 70)
print("📊 ESTATÍSTICAS:")
print(f"  Total de ideias: {len(items)}")
print(f"  Segmentos: {len(by_segment)}")
print(f"  Templates únicos: {len(set(i['templateId'] for i in items))}")
print(f"  Tones únicos: {len(set(i['copyTone'] for i in items))}")
print(f"  Styles únicos: {len(set(i['imageStyle'] for i in items))}")

# Status breakdown
status_count = {}
for item in items:
    status = item['status']
    status_count[status] = status_count.get(status, 0) + 1

print(f"\n  Status:")
for status, count in sorted(status_count.items()):
    print(f"    - {status}: {count}")

print("=" * 70)
