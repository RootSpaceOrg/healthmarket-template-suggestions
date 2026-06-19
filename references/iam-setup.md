# IAM — TemplateSuggesterRole

A skill autentica igual ao template-generator: o **user IAM `TemplateGenerator`**
(chaves de longa duracao no `.env` de secrets) assume uma **role** via STS, e os clients
boto3 usam as credenciais temporarias. Ver [`scripts/aws_auth.py`](../scripts/aws_auth.py).

## Roles criadas

| Ambiente | Conta | ARN |
|----------|-------|-----|
| prod | 692046683598 | `arn:aws:iam::692046683598:role/TemplateSuggesterRole` |
| dev  | 656032436386 | `arn:aws:iam::656032436386:role/TemplateSuggesterRole` |

Cada role:
- **Trust:** confia em `arn:aws:iam::{acct}:user/TemplateGenerator` (mesmo user do template-generator).
- **Permissoes:** inline policy `TemplateSuggesterActionsPolicy` (least-privilege).

## Politica de permissoes (TemplateSuggesterActionsPolicy)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadSupabaseCredentials",
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:sa-east-1:{ACCOUNT}:parameter/default/supabase-database-credentials"
    },
    {
      "Sid": "ReadTenantConfig",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:sa-east-1:{ACCOUNT}:table/tenantConfig"
    },
    {
      "Sid": "WriteAIRequests",
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:BatchWriteItem", "dynamodb:GetItem", "dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:sa-east-1:{ACCOUNT}:table/AIRequestsTable"
    }
  ]
}
```

## Verificacao (já validada via simulacao)

```bash
aws iam get-role --role-name TemplateSuggesterRole --profile mkt-platform-prod \
  --query "Role.AssumeRolePolicyDocument"

aws iam simulate-principal-policy --profile mkt-platform-prod \
  --policy-source-arn arn:aws:iam::692046683598:role/TemplateSuggesterRole \
  --action-names dynamodb:PutItem \
  --resource-arns arn:aws:dynamodb:sa-east-1:692046683598:table/AIRequestsTable
# -> allowed
```

## Override

- `SUGGESTER_ROLE_ARN_PROD` / `SUGGESTER_ROLE_ARN_DEV` — troca o ARN da role.
- `SUGGESTER_AUTH_MODE=assume|profile` — forca o modo de auth.
- `GP2_SECRETS_DIR` — diretorio do `.env` (default `/root/.openclaw/workspace/secrets`).
