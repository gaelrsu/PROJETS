import json
import urllib3
import boto3
import logging
import os
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http          = urllib3.PoolManager()
lambda_client = boto3.client("lambda")
logs_client   = boto3.client("logs", region_name="eu-west-1")

# Log group CloudTrail — à adapter selon ton compte
LOG_GROUP = "test-aws-cloudtrail-logs-445567090123-627e393a"

def get_recent_login_failures(minutes=15):
    """
    Interroge CloudWatch Logs Insights pour récupérer les échecs
    de connexion récents directement depuis les logs CloudTrail bruts.

    Note : les events ConsoleLogin IAM User (eu-north-1) peuvent arriver
    avec 2-3 minutes de délai par rapport aux events Root (us-east-1).
    """
    try:
        end_time   = int(time.time())
        start_time = end_time - (minutes * 60)

        query = """
        fields @timestamp, @message
        | filter @message like "ConsoleLogin"
        | filter @message like "Failure"
        | sort @timestamp desc
        | limit 50
        """

        response = logs_client.start_query(
            logGroupName=LOG_GROUP,
            startTime=start_time,
            endTime=end_time,
            queryString=query
        )
        query_id = response["queryId"]
        logger.info(f"Logs Insights query lancée : {query_id}")

        for i in range(10):
            time.sleep(1)
            result = logs_client.get_query_results(queryId=query_id)
            if result["status"] == "Complete":
                break

        rows = result.get("results", [])
        logger.info(f"Rows retournées : {len(rows)}")

        failures = []
        seen_ids = set()  # Dédoublonnage par eventID (2 trails actifs)

        for row in rows:
            fields = {f["field"]: f["value"] for f in row}
            try:
                detail   = json.loads(fields.get("@message", "{}"))
                event_id = detail.get("eventID", fields.get("@timestamp"))

                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                uid      = detail.get("userIdentity", {})
                username = uid.get("userName") or uid.get("type", "inconnu")

                failures.append({
                    "time":      detail.get("eventTime", "?"),
                    "ip":        detail.get("sourceIPAddress", "?"),
                    "user":      username,
                    "user_type": uid.get("type", "?"),
                    "region":    detail.get("awsRegion", "?"),
                    "mfa":       detail.get("additionalEventData", {}).get("MFAUsed", "No")
                })
            except Exception as e:
                logger.error(f"Erreur parsing row : {e}")
                continue

        logger.info(f"Failures uniques : {json.dumps(failures, ensure_ascii=False)}")
        return failures

    except Exception as e:
        logger.error(f"Erreur Logs Insights : {e}")
        return []


def enrich_alert(alarm_name, message, details={}):
    """Appelle la Lambda security-alert-enricher pour enrichir via Bedrock."""
    try:
        logger.info(f"Appel enrichissement pour : {alarm_name}")
        response = lambda_client.invoke(
            FunctionName="security-alert-enricher",
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "alarm_name":    alarm_name,
                "alert_message": message,
                "details":       details
            })
        )
        result = json.loads(response["Payload"].read())
        logger.info(f"Enrichissement statusCode : {result.get('statusCode')}")
        return result.get("enriched_message", message)
    except Exception as e:
        logger.error(f"Enrichissement échoué : {e}")
        return message  # Fallback : message original


def handle_cloudwatch_alarm(alarm):
    """Traite une alarme CloudWatch : récupère le contexte CloudTrail et enrichit via IA."""
    alarm_name  = alarm['AlarmName']
    raw_message = alarm['NewStateReason']
    state       = alarm['NewStateValue']

    logger.info(f"Alarm : {alarm_name} — {state}")

    failures = get_recent_login_failures(minutes=15)

    extra_details = {
        "state":           state,
        "previous_state":  alarm.get("OldStateValue"),
        "region":          alarm.get("Region", ""),
        "failure_count":   len(failures),
        "recent_failures": failures
    }

    if failures:
        users   = list(set(f["user"]   for f in failures))
        ips     = list(set(f["ip"]     for f in failures))
        regions = list(set(f["region"] for f in failures))
        summary = (
            f"\n\nDétail CloudTrail — {len(failures)} échec(s) unique(s)"
            f"\nUsers ciblés : {', '.join(users)}"
            f"\nIPs sources : {', '.join(ips)}"
            f"\nRégions : {', '.join(regions)}"
        )
        raw_message += summary
        logger.info(f"Users : {users} | IPs : {ips} | Régions : {regions}")
    else:
        logger.info("Aucune failure trouvée dans Logs Insights")

    enriched = enrich_alert(
        alarm_name=alarm_name,
        message=raw_message,
        details=extra_details
    )

    emoji = "🔴" if state == "ALARM" else "✅" if state == "OK" else "⚪"
    return f"{emoji} **{alarm_name}** → **{state}**\n\n{enriched}"


def handle_budget_alert(message_str):
    """Formate une alerte AWS Budgets pour Discord."""
    return (
        "💸 **Alerte Budget AWS**\n\n"
        "🔍 **Analyse**\nTon budget mensuel AWS a atteint ou dépassé le seuil configuré.\n\n"
        "⚠️ **Risque**\nÉlevé — Des frais inattendus sont en cours sur ton compte.\n\n"
        "🛠️ **Action**\n"
        "1. Aller dans **Billing** → **Cost Explorer** pour identifier le service en cause\n"
        "2. Vérifier les Lambdas, Bedrock et CloudWatch Logs\n"
        "3. Supprimer les ressources inutiles si besoin\n\n"
        f"📄 Détail AWS :\n```{message_str[:500]}```"
    )


def lambda_handler(event, context):
    logger.info(f"Event reçu : {json.dumps(event)[:500]}")

    sns_record  = event['Records'][0]['Sns']
    subject     = sns_record.get('Subject', '')
    message_str = sns_record['Message']

    if 'AWS Budgets' in subject or 'Budget' in subject:
        texte = handle_budget_alert(message_str)
    else:
        try:
            alarm = json.loads(message_str)
            texte = handle_cloudwatch_alarm(alarm)
        except json.JSONDecodeError:
            texte = f"⚠️ **Alerte AWS**\n\n```{message_str[:500]}```"

    webhook_url = os.environ['DISCORD_WEBHOOK_URL']
    http.request(
        'POST',
        webhook_url,
        body=json.dumps({"content": texte}),
        headers={'Content-Type': 'application/json'}
    )

    return {"status": "ok"}
