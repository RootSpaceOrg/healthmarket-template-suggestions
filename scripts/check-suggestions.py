#!/usr/bin/env python3
"""Verifica sugestões inseridas no DynamoDB"""

import boto3
from boto3.dynamodb.conditions import Attr

AWS_PROFILE = 'healthmarket-prod'
DYNAMODB_TABLE = 'AIRequestsTable'
AWS_REGION = 'sa-east-1'

session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
dynamodb = session.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)

# Query com filtro
response = table.scan(
    FilterExpression=Attr('createdBy').eq('Sugestão AI'),
    Limit=10
)

items = response.get('Items', [])

print(f"Total de sugestoes encontradas: {len(items)}\n")

for i, item in enumerate(items, 1):
    print(f"[{i}] {item['requestId'][:8]}...")
    print(f"  Status: {item['status']}")
    print(f"  Ideia: {item['idea'][:70]}...")
    print(f"  Template: {item['templateId']}")
    print(f"  Tone: {item['copyTone']} | Style: {item['imageStyle']}")
    print(f"  Created: {item['createdAt']}")
    print()
