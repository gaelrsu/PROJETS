import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock  = boto3.client("bedrock-runtime", region_name="eu-west-1")
MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

SYSTEM_PROMPT = """Tu es un analyste en sécurité AWS. On te donne une alerte brute issue de CloudWatch/CloudTrail.
Produis un résumé enrichi en 3 parties courtes, format Discord (markdown) :
1. 🔍 **Analyse** : ce qui s'est passé, en une phrase claire
2. ⚠️ **Risque** : Faible / Modéré / Élevé + justification courte
3. 🛠️ **Action** : une action concrète et immédiate

Réponds uniquement avec ces 3 points, en français, sans introduction."""


def lambda_handler(event, context):
    """
    Reçoit : { "alarm_name": "...", "alert_message": "...", "details": {...} }
    Retourne : { "statusCode": 200, "enriched_message": "..." }
    """
    alarm_name    = event.get("alarm_name", "Inconnue")
    alert_message = event.get("alert_message", "Alerte sans détails")
    details       = event.get("details", {})

    logger.info(f"Enrichissement pour : {alarm_name}")

    user_prompt = f"""Alerte déclenchée : **{alarm_name}**
Message : {alert_message}
Détails : {json.dumps(details, indent=2, ensure_ascii=False)}"""

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 400,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}]
            }),
            contentType="application/json",
            accept="application/json"
        )
        body     = json.loads(response["body"].read())
        enriched = body["content"][0]["text"]
        logger.info(f"Enrichissement OK — {alarm_name}")
        return {"statusCode": 200, "enriched_message": enriched}

    except Exception as e:
        logger.error(f"Erreur Bedrock : {e}")
        return {
            "statusCode": 500,
            "enriched_message": f"⚠️ Enrichissement IA indisponible\n\n{alert_message}"
        }
