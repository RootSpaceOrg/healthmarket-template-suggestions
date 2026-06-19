#!/usr/bin/env python3
"""
Autenticacao AWS compartilhada para a skill template-suggester.

Espelha o padrao do template-generator (gp2-template-uploader/import-template.py):
um IAM **user** `TemplateGenerator` (com chaves de longa duracao em um arquivo .env)
assume uma **role** via STS, e os clients boto3 usam as credenciais temporarias.

A role do suggester e a `TemplateSuggesterRole` (criada em cada conta, confiando no
mesmo user `TemplateGenerator` que o template-generator usa). Permissoes minimas:
ler `/default/supabase-database-credentials` (SSM), ler `tenantConfig` e escrever
`AIRequestsTable` (DynamoDB).

Modos (escolhidos automaticamente; force com SUGGESTER_AUTH_MODE=assume|profile):

  1. assume-role (default, igual ao template-generator / OpenClaw):
       - le o .env de credenciais em GP2_SECRETS_DIR (default /root/.openclaw/workspace/secrets)
       - arquivo: aws-credentials-template-generator-mkt-platform-{env}.env
       - sts.assume_role(RoleArn=TemplateSuggesterRole) -> creds temporarias

  2. profile (fallback p/ dev local nesta maquina, sem o .env):
       - usa boto3.Session(profile_name=mkt-platform-{env}) com seu SSO local

Env vars:
  GP2_SECRETS_DIR        diretorio dos .env (default /root/.openclaw/workspace/secrets)
  SUGGESTER_ROLE_ARN_PROD / SUGGESTER_ROLE_ARN_DEV   override do ARN da role
  SUGGESTER_AUTH_MODE    'assume' | 'profile' (override do modo automatico)
"""

from __future__ import annotations

import os
from pathlib import Path

import boto3

AWS_REGION = "sa-east-1"

# ARNs das roles criadas para o suggester (uma por conta).
ROLE_ARN_BY_ENV = {
    "prod": os.environ.get(
        "SUGGESTER_ROLE_ARN_PROD",
        "arn:aws:iam::692046683598:role/TemplateSuggesterRole",
    ),
    "dev": os.environ.get(
        "SUGGESTER_ROLE_ARN_DEV",
        "arn:aws:iam::656032436386:role/TemplateSuggesterRole",
    ),
}

# Perfis SSO locais (fallback de dev nesta maquina).
PROFILE_BY_ENV = {"prod": "mkt-platform-prod", "dev": "mkt-platform-dev"}

# Diretorio dos .env de credenciais (mesmo default do template-generator).
SECRETS_DIR = Path(
    os.environ.get("GP2_SECRETS_DIR", "/root/.openclaw/workspace/secrets")
)


def _aws_env_path(env: str) -> Path:
    # Reusa exatamente o mesmo arquivo de credenciais do template-generator.
    return SECRETS_DIR / f"aws-credentials-template-generator-mkt-platform-{env}.env"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"AWS env file not found: {path}")
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key] = value.strip().strip('"').strip("'")


def _assume_role_kwargs(env: str) -> dict:
    _load_env_file(_aws_env_path(env))
    sts = boto3.client("sts", region_name="us-east-1")
    creds = sts.assume_role(
        RoleArn=ROLE_ARN_BY_ENV[env],
        RoleSessionName="openclaw-template-suggester",
    )["Credentials"]
    return {
        "aws_access_key_id": creds["AccessKeyId"],
        "aws_secret_access_key": creds["SecretAccessKey"],
        "aws_session_token": creds["SessionToken"],
    }


def get_session(env: str) -> boto3.Session:
    """Retorna uma boto3.Session autenticada para o ambiente dado.

    Tenta assume-role (padrao template-generator). Se o .env nao existir e o modo
    nao foi forcado para 'assume', cai para o profile SSO local.
    """
    if env not in ROLE_ARN_BY_ENV:
        raise ValueError(f"env invalido: {env!r} (use 'prod' ou 'dev')")

    mode = os.environ.get("SUGGESTER_AUTH_MODE", "").strip().lower()

    if mode == "profile":
        return boto3.Session(profile_name=PROFILE_BY_ENV[env], region_name=AWS_REGION)

    if mode == "assume" or _aws_env_path(env).exists():
        kwargs = _assume_role_kwargs(env)
        return boto3.Session(region_name=AWS_REGION, **kwargs)

    # Fallback automatico: sem .env e sem modo forcado -> profile SSO local.
    return boto3.Session(profile_name=PROFILE_BY_ENV[env], region_name=AWS_REGION)
