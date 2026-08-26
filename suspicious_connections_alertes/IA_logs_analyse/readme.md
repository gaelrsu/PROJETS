# 🛡️ AWS Security Alert Enrichment with Amazon Bedrock

> Enrichissement automatique des alertes de sécurité AWS via l'IA générative.  
> CloudTrail détecte → CloudWatch alerte → Lambda analyse → Bedrock enrichit → Discord notifie.

---

## 📋 Sommaire

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Résultat final](#résultat-final)
- [Stack technique](#stack-technique)
- [Mise en place étape par étape](#mise-en-place-étape-par-étape)
  - [Prérequis](#prérequis)
  - [Étape 1 — Vérifier les modèles Bedrock disponibles](#étape-1--vérifier-les-modèles-bedrock-disponibles)
  - [Étape 2 — Soumettre le formulaire Anthropic](#étape-2--soumettre-le-formulaire-anthropic)
  - [Étape 3 — Créer la Lambda d'enrichissement](#étape-3--créer-la-lambda-denrichissement)
  - [Étape 4 — Configurer les permissions IAM](#étape-4--configurer-les-permissions-iam)
  - [Étape 5 — Modifier la Lambda dispatcher](#étape-5--modifier-la-lambda-dispatcher)
  - [Étape 6 — Alerte budget AWS](#étape-6--alerte-budget-aws)
- [Problèmes rencontrés et solutions](#problèmes-rencontrés-et-solutions)
- [Limitations connues](#limitations-connues)
- [Coût estimé](#coût-estimé)
- [Améliorations futures](#améliorations-futures)

---

## Vue d'ensemble

Ce lab construit un pipeline de détection et d'analyse de sécurité AWS enrichi par l'IA.

**Point de départ** : une alarme CloudWatch existante détectant les échecs de connexion console, déclenchant une Lambda qui envoie un message brut sur Discord.

**Objectif** : enrichir ces alertes avec une analyse IA (niveau de risque, contexte CloudTrail, actions recommandées) avant l'envoi sur Discord.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flux existant                            │
│                                                                 │
│  CloudTrail ──► CloudWatch Logs ──► Metric Filter               │
│                      │                                          │
│                 CloudWatch Alarm                                │
│                      │                                          │
│                   SNS Topic                                     │
│                      │                                          │
│              Lambda sendToDiscord ◄──────────────────────────┐  │
│                      │                                       │  │
└──────────────────────┼───────────────────────────────────────┼──┘
                       │         Enrichissement IA (nouveau)   │
                       ▼                                       │
          Lambda security-alert-enricher                       │
                       │                                       │
                       ▼                                       │
              Amazon Bedrock                                   │
           (Claude Haiku 4.5)                                  │
                       │                                       │
                       └── enriched_message ───────────────────┘
                                    │
                                    ▼
                              Discord Webhook
                         (alerte enrichie par IA)
```

---

## Résultat final

**Avant — message brut CloudWatch :**
```
ALARM: "ConsoleLoginFailures" in EU (Ireland)
Threshold Crossed: 1 out of the last 1 datapoints [7.0] was greater than the threshold (4.0)
```

**Après — enrichi par Claude Haiku 4.5 :**
```
🔴 ConsoleLoginFailure !!! → ALARM

Détail CloudTrail — 7 échec(s) unique(s)
Users ciblés : Root, Analyst
IPs sources : 86.237.004.004
Régions : eu-west-1, eu-north-1

🔍 Analyse
19 tentatives de connexion échouées sur le compte Root en ~13 minutes
depuis l'IP 86.237.004.004, toutes sans MFA, suggérant une attaque
par force brute ou vol de credentials.

⚠️ Risque
Élevé — Accès Root compromis ou tentative active d'accès ;
absence de MFA + taux d'échecs élevé = vecteur critique.

🛠️ Action
1. Bloquer immédiatement l'IP 86.237.004.004 via WAF/Security Group
2. Forcer un changement de mot de passe Root + activer MFA obligatoire
3. Auditer CloudTrail pour connexions réussies dans les 24h précédentes
```

---

## Stack technique

| Service | Rôle |
|---------|------|
| AWS CloudTrail | Capture tous les events API du compte |
| CloudWatch Logs | Stockage des logs CloudTrail |
| CloudWatch Metric Filter | Compte les échecs `ConsoleLogin` |
| CloudWatch Alarm | Déclenche l'alerte quand le seuil est dépassé |
| Amazon SNS | Transmet l'alerte à la Lambda |
| Lambda `sendToDiscord` | Orchestre le pipeline, récupère le contexte CloudTrail |
| Lambda `security-alert-enricher` | Appelle Bedrock et retourne l'analyse IA |
| Amazon Bedrock (Claude Haiku 4.5) | Génère l'analyse de sécurité enrichie |
| CloudWatch Logs Insights | Requête les logs CloudTrail bruts pour le contexte |
| Discord Webhook | Réception finale des alertes enrichies |

---

## Mise en place étape par étape

### Prérequis

- Compte AWS (Free Tier est suffisant)
- CloudTrail activé avec un log group CloudWatch configuré
- Une alarme CloudWatch existante sur les échecs `ConsoleLogin`
- Une Lambda existante abonnée au SNS topic envoyant sur Discord
- Un webhook Discord

---

### Étape 1 — Vérifier les modèles Bedrock disponibles

Les model IDs Bedrock varient selon la région et évoluent dans le temps. Avant tout, lister les modèles disponibles :

```bash
aws bedrock list-foundation-models \
  --region eu-west-1 \
  --query "modelSummaries[?contains(modelId, 'anthropic')].{id:modelId, name:modelName}" \
  --output table
```

Tester la connectivité avec le bon model ID (préfixe régional `eu.` obligatoire pour les nouveaux modèles) :

```bash
aws bedrock-runtime invoke-model \
  --model-id "eu.anthropic.claude-haiku-4-5-20251001-v1:0" \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":50,"messages":[{"role":"user","content":"Réponds juste OK"}]}' \
  --cli-binary-format raw-in-base64-out \
  --region eu-west-1 \
  /tmp/test-output.json && cat /tmp/test-output.json
```

**Résultat attendu :**
```json
{"model":"claude-haiku-4-5-20251001","type":"message","content":[{"type":"text","text":"OK"}]}
```

#### Erreurs connues et solutions

| Erreur | Cause | Solution |
|--------|-------|----------|
| `ResourceNotFoundException: Legacy model` | Modèle déprécié (ex: claude-3-haiku v1) | Utiliser `eu.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `ValidationException: invalid model identifier` | Inference profile manquant | Ajouter le préfixe régional `eu.` |
| `ResourceNotFoundException: use case details` | Formulaire Anthropic non soumis | Voir étape 2 |
| `AccessDeniedException: aws-marketplace` | Permissions IAM manquantes | Ajouter les permissions marketplace (voir étape 4) |

> **Pourquoi le préfixe `eu.` ?**  
> AWS a migré les nouveaux modèles Bedrock vers un système d'**inference profiles** avec routage cross-région. Le préfixe indique la zone géographique (`eu.` = Europe, `us.` = US). Sans ce préfixe, AWS retourne une `ValidationException`.

---

### Étape 2 — Soumettre le formulaire Anthropic

Pour les nouveaux comptes AWS, Anthropic impose de soumettre un formulaire d'usage avant d'accéder aux modèles.

1. Console AWS → **Amazon Bedrock** → **Model catalog**
2. Sélectionner **Claude Haiku 4.5**
3. Cliquer sur **Submit use case details**
4. Remplir :
   - **Company name** : `Ton Nom Lab` (ou profil perso)
   - **Company website URL** : ton profil GitLab `https://gitlab.com/username`
   - **Use case** : `Security log analysis and alert enrichment for personal AWS lab`
   - **Industry** : `Information Technology`
   - **Expected monthly usage** : option la plus basse

> Le délai annoncé est 15 minutes. En pratique l'accès est accordé quasi-immédiatement mais peut prendre jusqu'à 30 minutes.  
> Une fois validé, l'erreur passe de `ResourceNotFoundException` à `AccessDeniedException` — c'est normal, il faut alors ajouter les permissions IAM (étape 4).

---

### Étape 3 — Créer la Lambda d'enrichissement

**Console AWS → Lambda → Create function**

| Paramètre | Valeur |
|-----------|--------|
| Nom | `security-alert-enricher` |
| Runtime | Python 3.12 |
| Architecture | x86_64 |
| Timeout | **30 secondes** (Bedrock peut prendre 3-5s) |
| Memory | 128 MB |

Code source : [`lambdas/security-enricher/lambda_function.py`](https://github.com/gaelrsu/Cloud/blob/main/AWS/Projet_IA_analyse_log_connexion/Lambda_IA.py)

**Tester avec ce payload dans l'onglet Test :**

```json
{
  "alarm_name": "ConsoleLoginFailures",
  "alert_message": "5 échecs de connexion console détectés en 2 minutes depuis 185.234.2.5",
  "details": {
    "sourceIPAddress": "185.234.2.5",
    "eventName": "ConsoleLogin",
    "errorMessage": "Failed authentication"
  }
}
```

**Résultat attendu :**
```json
{
  "statusCode": 200,
  "enriched_message": "🔍 **Analyse**\n...\n⚠️ **Risque**\n...\n🛠️ **Action**\n..."
}
```

> **Attention** : si `statusCode` est `None` dans les logs, vérifier que le timeout de la Lambda est bien à 30 secondes. Un timeout à 3 secondes (valeur par défaut) est insuffisant pour Bedrock.

---

### Étape 4 — Configurer les permissions IAM

#### Lambda `security-alert-enricher` — inline policy `bedrock-marketplace-access`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "aws-marketplace:ViewSubscriptions",
        "aws-marketplace:Subscribe",
        "aws-marketplace:Unsubscribe"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Pourquoi les permissions `aws-marketplace` ?**  
> Depuis la refonte de Bedrock Model Access (2025), les modèles Anthropic sont distribués via AWS Marketplace. Sans ces permissions sur le rôle Lambda, l'invocation échoue avec `AccessDeniedException` même si le formulaire Anthropic a été validé.

#### Lambda `sendToDiscord` — inline policy `enricher-and-logs`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "arn:aws:lambda:eu-west-1:*:function:security-alert-enricher"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "arn:aws:logs:eu-west-1:*:log-group:*:*"
    }
  ]
}
```

---

### Étape 5 — Modifier la Lambda dispatcher

La Lambda existante (`sendToDiscord`) reçoit les messages SNS et les envoie sur Discord. On la modifie pour :

1. Interroger **CloudWatch Logs Insights** afin de récupérer le contexte CloudTrail réel (IPs, users, régions)
2. Appeler `security-alert-enricher` avec ce contexte enrichi
3. Envoyer le message enrichi sur Discord avec un fallback si Bedrock est indisponible

Code source complet : [`lambdas/alert-dispatcher/lambda_function.py`](https://github.com/gaelrsu/Cloud/blob/main/AWS/Projet_IA_analyse_log_connexion/lambda.py)

**Paramètre de configuration à modifier :**
- Timeout : **30 secondes** (Logs Insights + Bedrock = ~5-10s)

**Tester avec un payload réaliste :**

```json
{
  "Records": [{
    "Sns": {
      "Subject": "ALARM: ConsoleLoginFailures in EU (Ireland)",
      "Message": "{\"AlarmName\":\"ConsoleLoginFailure !!!\",\"NewStateValue\":\"ALARM\",\"OldStateValue\":\"OK\",\"NewStateReason\":\"Threshold Crossed: 1 out of the last 1 datapoints [7.0 (22/03/26 15:30:00)] was greater than the threshold (4.0)\",\"Region\":\"EU (Ireland)\",\"Trigger\":{\"Namespace\":\"CloudTrailMetrics\"}}"
    }
  }]
}
```

---

### Étape 6 — Alerte budget AWS

Pour éviter les mauvaises surprises financières, configurer une alerte si les coûts dépassent 6$ (≈ 5€).

**Console AWS → Billing → Budgets → Create budget**

| Paramètre | Valeur |
|-----------|--------|
| Type | Cost budget |
| Nom | `lab-security-budget` |
| Period | Monthly |
| Amount | `6` USD |
| Seuil 1 | 80% — notification email |
| Seuil 2 | 100% — email + SNS topic existant |

Brancher le SNS topic existant sur l'alerte à 100% — la Lambda `sendToDiscord` reçoit et formate automatiquement les alertes budget grâce à la détection du sujet `AWS Budgets` dans le code.

**Tester** en cliquant sur **"Send test alert"** dans la page du budget.

---

## Problèmes rencontrés et solutions

Cette section documente les problèmes réels rencontrés lors de la mise en place, utiles pour comprendre les subtilités AWS.

### 1. Model ID invalide — inference profiles obligatoires

**Symptôme :** `ValidationException: The provided model identifier is invalid`

**Cause :** Les modèles Bedrock récents (Haiku 4.5, Sonnet 4, etc.) ne supportent pas l'invocation directe — ils nécessitent un inference profile avec préfixe régional.

**Solution :** Utiliser `eu.anthropic.claude-haiku-4-5-20251001-v1:0` au lieu de `anthropic.claude-haiku-4-5-20251001-v1:0`.

---

### 2. AccessDeniedException — permissions AWS Marketplace

**Symptôme :** `AccessDeniedException: IAM role is not authorized to perform aws-marketplace actions`

**Cause :** Bedrock utilise AWS Marketplace en backend pour les modèles Anthropic. Le rôle Lambda doit avoir les permissions marketplace même si on n'achète rien.

**Solution :** Ajouter `aws-marketplace:ViewSubscriptions`, `aws-marketplace:Subscribe`, `aws-marketplace:Unsubscribe` à la policy IAM.

---

### 3. Mauvaise Lambda modifiée

**Symptôme :** Les modifications ne prennent pas effet malgré le Deploy

**Cause :** La Lambda abonnée au SNS topic s'appelait `sendToDiscord`, pas `alert-dispatcher`. Le code était déployé sur la mauvaise fonction.

**Solution :** Vérifier dans **SNS → Topic → Subscriptions** quel est le nom exact de la Lambda abonnée.

---

### 4. Events ConsoleLogin dans us-east-1 seulement via lookup-events

**Symptôme :** `aws cloudtrail lookup-events` retourne 0 résultats en `eu-west-1` malgré des échecs de connexion réels

**Cause :** Les events `ConsoleLogin` sont des **événements globaux AWS** — ils sont physiquement enregistrés dans `us-east-1` par l'API `lookup-events`, quelle que soit la région du trail.

**Solution :** Utiliser `--region us-east-1` pour `lookup-events`, ou mieux — utiliser **CloudWatch Logs Insights** qui lit directement le log group du trail (où tous les events arrivent).

---

### 5. Doublons d'events — deux trails actifs

**Symptôme :** 20 échecs retournés alors que seulement 7 ont été effectués

**Cause :** Deux trails CloudTrail actifs (`TEST-security-trail` et `iam-logs-test-lab`) écrivent le même event dans le même log group, créant des doublons.

**Solution :** Dédoublonnage par `eventID` côté Python lors du parsing des résultats Logs Insights.

---

### 6. Timeout Lambda insuffisant

**Symptôme :** `Status: timeout` dans les logs, `statusCode: None` retourné par l'enrichisseur

**Cause :** Timeout par défaut Lambda = 3 secondes. Bedrock (Claude Haiku 4.5) prend 2-5 secondes selon la charge.

**Solution :** Passer le timeout des deux Lambdas à **30 secondes**.

---

### 7. MalformedQueryException avec dedup dans Logs Insights

**Symptôme :** `unexpected symbol found sort at line 6` lors de l'exécution de la query

**Cause :** La commande `dedup` de CloudWatch Logs Insights n'est pas compatible avec `sort` dans la même query.

**Solution :** Supprimer `dedup` de la query et gérer le dédoublonnage côté Python avec un `set()` sur les `eventID`.

---

## Limitations connues

### Délai d'indexation des events IAM User

Les events `ConsoleLogin` des IAM Users (ex: `Analyst`) arrivent dans le log group avec **2-3 minutes de délai supplémentaire** par rapport aux events Root, car ils transitent par une région différente (`eu-north-1` → log stream `eu-west-1_2`).

Quand l'alarme se déclenche, ces events ne sont pas encore indexés dans Logs Insights. En pratique :
- **Events Root** : disponibles quasi-immédiatement
- **Events IAM User** : disponibles 2-3 minutes après

**Impact :** Dans un scénario d'attaque réel (qui dure plusieurs minutes), les deux types d'events seraient capturés. Pour un lab avec des tests rapides, seuls les events Root apparaissent dans l'alerte.

**Solutions possibles (non implémentées) :**
- Lambda différée via EventBridge (déclencher l'enrichissement 5 minutes après l'alarme)
- Se connecter via l'URL régionale `eu-west-1.signin.aws.amazon.com` pour forcer le même log stream

---

## Coût estimé (Free Tier)

| Service | Usage estimé | Coût mensuel |
|---------|-------------|--------------|
| Lambda | < 1M invocations | Gratuit |
| CloudWatch Logs | < 5 GB | Gratuit |
| CloudWatch Alarms | 1 alarme | Gratuit |
| SNS | < 1M notifications | Gratuit |
| Bedrock Claude Haiku 4.5 | ~100 alertes × ~500 tokens | < $0.05 |
| **Total** | | **< $0.05/mois** |

---

## Améliorations futures

- **DynamoDB** : stocker chaque alerte enrichie pour un historique consultable et des analyses de tendances
- **Severity routing** : si Claude détecte un risque "Élevé", envoyer en parallèle un SMS via SNS
- **Contexte étendu** : passer à Bedrock les derniers events CloudTrail de l'IP source pour une corrélation plus fine
- **GuardDuty** : remplacer les Metric Filters manuels par GuardDuty pour une détection plus complète (brute force, credential stuffing, etc.)
- **Security Hub** : centraliser toutes les findings avant l'enrichissement IA
- **Lambda différée** : résoudre le délai d'indexation IAM User via un déclenchement EventBridge 5 minutes après l'alarme
- **Multi-compte** : étendre le pipeline à plusieurs comptes AWS via AWS Organizations

