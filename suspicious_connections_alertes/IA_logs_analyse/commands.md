# 📝 Mémo — Commandes utiles du lab AWS Security

---

## 🔍 Amazon Bedrock

### Lister les modèles Anthropic disponibles
```bash
aws bedrock list-foundation-models \
  --region eu-west-1 \
  --query "modelSummaries[?contains(modelId, 'anthropic')].{id:modelId, name:modelName}" \
  --output table
```

### Tester 'l'invocation' d'un modèle Bedrock
```bash
aws bedrock-runtime invoke-model \
  --model-id "eu.anthropic.claude-haiku-4-5-20251001-v1:0" \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":50,"messages":[{"role":"user","content":"Réponds juste OK"}]}' \
  --cli-binary-format raw-in-base64-out \
  --region eu-west-1 \
  /tmp/test-output.json && cat /tmp/test-output.json
```

---

## 🪵 CloudTrail

### Lister les trails actifs et leur configuration
```bash
aws cloudtrail describe-trails \
  --region eu-west-1 \
  --query "trailList[*].{name:Name,region:HomeRegion,global:IncludeGlobalServiceEvents,multiregion:IsMultiRegionTrail}" \
  --output table
```

### Rechercher les events ConsoleLogin (Global → us-east-1 obligatoire)
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --region us-east-1 \
  --output json | python3 -c "
import json, sys
events = json.load(sys.stdin)['Events']
print(f'Total: {len(events)}')
for e in events[:10]:
    detail = json.loads(e['CloudTrailEvent'])
    result = (detail.get('responseElements') or {}).get('ConsoleLogin', 'N/A')
    print({
        'event': e['EventName'],
        'time': str(e['EventTime']),
        'user': e.get('Username','?'),
        'ip': detail.get('sourceIPAddress','?'),
        'result': result
    })
"
```

### Rechercher les events d'un utilisateur spécifique
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=Analyst \
  --region us-east-1 \
  --output json | python3 -c "
import json, sys
events = json.load(sys.stdin)['Events']
print(f'Total: {len(events)}')
for e in events[:10]:
    detail = json.loads(e['CloudTrailEvent'])
    result = (detail.get('responseElements') or {}).get('ConsoleLogin', 'N/A')
    print({'event': e['EventName'], 'time': str(e['EventTime']), 'ip': detail.get('sourceIPAddress','?'), 'result': result})
"
```

### Rechercher les ConsoleLogin du jour avec détail complet
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --region us-east-1 \
  --start-time "2026-03-22T00:00:00Z" \
  --output json | python3 -c "
import json, sys
events = json.load(sys.stdin)['Events']
print(f'Total ConsoleLogin: {len(events)}')
for e in events:
    detail = json.loads(e['CloudTrailEvent'])
    result = (detail.get('responseElements') or {}).get('ConsoleLogin', 'N/A')
    uid = detail.get('userIdentity', {})
    print({
        'time': str(e['EventTime']),
        'result': result,
        'username': e.get('Username', '?'),
        'identity_type': uid.get('type', '?'),
        'ip': detail.get('sourceIPAddress', '?')
    })
"
```

---

## 📊 CloudWatch

### Lister les Metric Filters actifs
```bash
aws logs describe-metric-filters \
  --region eu-west-1 \
  --output json | python3 -c "
import json, sys
filters = json.load(sys.stdin)['metricFilters']
for f in filters:
    print({'name': f['filterName'], 'logGroup': f['logGroupName'], 'pattern': f['filterPattern']})
"
```

### Lister les alarmes CloudWatch et leur état
```bash
aws cloudwatch describe-alarms \
  --region eu-west-1 \
  --query "MetricAlarms[*].{name:AlarmName,state:StateValue,metric:MetricName}" \
  --output table
```

### Query Logs Insights — échecs de connexion (30 dernières minutes)
```
fields @timestamp, userIdentity.userName, userIdentity.type, awsRegion, sourceIPAddress
| filter eventName = "ConsoleLogin"
| filter responseElements.ConsoleLogin = "Failure"
| sort @timestamp desc
| limit 50
```
> À exécuter dans **CloudWatch → Logs Insights** en sélectionnant le log group CloudTrail.

### Query Logs Insights — voir le message brut complet
```
fields @timestamp, @message
| filter @message like "ConsoleLogin"
| filter @message like "Failure"
| sort @timestamp desc
| limit 10
```

---

## ⚡ Lambda

### Lister les fonctions Lambda du compte
```bash
aws lambda list-functions \
  --region eu-west-1 \
  --query "Functions[*].{name:FunctionName,runtime:Runtime,timeout:Timeout,memory:MemorySize}" \
  --output table
```

### Invoquer une Lambda manuellement en CLI
```bash
aws lambda invoke \
  --function-name security-alert-enricher \
  --region eu-west-1 \
  --payload '{"alarm_name":"Test","alert_message":"Test depuis CLI","details":{}}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda-output.json && cat /tmp/lambda-output.json
```

### Voir les derniers logs d'une Lambda
```bash
# Lister les log streams (du plus récent au plus ancien)
aws logs describe-log-streams \
  --log-group-name /aws/lambda/security-alert-enricher \
  --region eu-west-1 \
  --order-by LastEventTime \
  --descending \
  --query "logStreams[0].logStreamName" \
  --output text

# Lire les logs du dernier stream
aws logs get-log-events \
  --log-group-name /aws/lambda/security-alert-enricher \
  --region eu-west-1 \
  --log-stream-name "$(aws logs describe-log-streams \
    --log-group-name /aws/lambda/security-alert-enricher \
    --region eu-west-1 \
    --order-by LastEventTime \
    --descending \
    --query 'logStreams[0].logStreamName' \
    --output text)" \
  --query "events[*].message" \
  --output text
```

### Payload de test — alarme CloudWatch réelle
```json
{
  "Records": [{
    "Sns": {
      "Subject": "ALARM: \"ConsoleLoginFailure !!!\" in EU (Ireland)",
      "Message": "{\"AlarmName\":\"ConsoleLoginFailure !!!\",\"NewStateValue\":\"ALARM\",\"OldStateValue\":\"OK\",\"NewStateReason\":\"Threshold Crossed: 1 out of the last 1 datapoints [7.0 (22/03/26 15:30:00)] was greater than the threshold (4.0)\",\"Region\":\"EU (Ireland)\",\"Trigger\":{\"Namespace\":\"CloudTrailMetrics\"}}"
    }
  }]
}
```

### Payload de test — Lambda enrichisseur directement
```json
{
  "alarm_name": "ConsoleLoginFailures",
  "alert_message": "5 échecs de connexion console détectés en 2 minutes depuis 185.234.12.45",
  "details": {
    "sourceIPAddress": "185.234.12.45",
    "userAgent": "aws-cli/2.0",
    "eventName": "ConsoleLogin",
    "errorMessage": "Failed authentication",
    "state": "ALARM",
    "failure_count": 5
  }
}
```

---

## 📣 SNS

### Lister les topics SNS
```bash
aws sns list-topics \
  --region eu-west-1 \
  --output table
```

### Lister les abonnements d'un topic (voir quelle Lambda est branchée)
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:eu-west-1:TON_ACCOUNT_ID:discord-alerts \
  --region eu-west-1 \
  --output table
```

### Publier un message de test sur un topic SNS
```bash
aws sns publish \
  --topic-arn arn:aws:sns:eu-west-1:TON_ACCOUNT_ID:discord-alerts \
  --region eu-west-1 \
  --subject "Test manuel" \
  --message "Ceci est un test depuis la CLI"
```

---

## 💰 Billing & Budget

### Voir les coûts du mois en cours par service
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-03-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query "ResultsByTime[0].Groups[?Metrics.BlendedCost.Amount > '0'].{Service:Keys[0],Cost:Metrics.BlendedCost.Amount}" \
  --output table
```

### Lister les budgets actifs
```bash
aws budgets describe-budgets \
  --account-id TON_ACCOUNT_ID \
  --query "Budgets[*].{name:BudgetName,limit:BudgetLimit.Amount,unit:BudgetLimit.Unit}" \
  --output table
```

---

## 🔐 IAM

### Voir les policies attachées au rôle d'une Lambda
```bash
# Trouver le rôle d'une Lambda
aws lambda get-function-configuration \
  --function-name security-alert-enricher \
  --region eu-west-1 \
  --query "Role" \
  --output text

# Lister les policies du rôle
aws iam list-role-policies \
  --role-name NOM_DU_ROLE \
  --output table

aws iam list-attached-role-policies \
  --role-name NOM_DU_ROLE \
  --output table
```

---

## 💡 Astuces utiles

| Besoin | Commande rapide |
|--------|----------------|
| Tester Bedrock | CloudShell → commande invoke-model |
| Voir les logs Lambda | Console → Lambda → Monitor → View CloudWatch logs |
| Identifier la Lambda d'un SNS | Console → SNS → Topic → Subscriptions |
| Voir les events globaux CloudTrail | Toujours `--region us-east-1` pour ConsoleLogin |
| Dédoublonner les events | Filtrer par `eventID` quand plusieurs trails actifs |
| Déboguer une Lambda silencieuse | Vérifier `import logging` + `logger.setLevel(logging.INFO)` |
| Lambda trop lente / timeout | Configuration → General → Timeout : mettre 30s |
