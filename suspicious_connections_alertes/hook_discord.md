# 🔔 AWS CloudWatch Alarms to Discord Notification Pipeline

[![AWS](https://img.shields.io/badge/AWS-Lambda%20%7C%20SNS%20%7C%20CloudWatch-orange?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)
[![Discord](https://img.shields.io/badge/Discord-Webhook%20Integration-5865F2?style=flat-square&logo=discord)](https://discord.com/)


## 📌 Project Overview

Receiving security alerts directly where operational teams communicate reduces Incident Response time (MTTR). 
Standard email alerts from AWS SNS are often delayed, ignored, or lost in flooded inboxes.

This project implements a serverless event-driven bridging solution that forwards **AWS CloudWatch Alarms** directly to a **Discord channel** in real time. By connecting **Amazon SNS**, an **AWS Lambda function (Python 3.12)**, and a **Discord Webhook**, security analysts receive immediate notifications upon critical event triggers (such as brute-force connection attempts or operational failures).

---

## 📐 Architecture Flow

```text
                            ┌─────────────────────────┐
                            │  AWS Management Console │
                            └────────────┬────────────┘
                                         │ (Failed Login Attempts)
                                         v
                            ┌─────────────────────────┐
                            │  CloudWatch Log Group   │
                            └────────────┬────────────┘
                                         │
                                         v
                            ┌─────────────────────────┐
                            │   CloudWatch Alarm      │
                            │  (Trigger: > 5 Failures)│
                            └────────────┬────────────┘
                                         │
                                         v
                            ┌─────────────────────────┐
                            │   Amazon SNS Topic      │
                            │    (discord-alerts)     │
                            └────────────┬────────────┘
                                         │
                                         v
                            ┌─────────────────────────┐
                            │   AWS Lambda Function   │
                            │  (Python 3.12 Bridge)   │
                            └────────────┬────────────┘
                                         │
                                         │ (HTTPS / POST Webhook)
                                         v
                            ┌─────────────────────────┐     ┌─────────────────────────┐
                            │     Discord Webhook     ├────►│     Discord Channel     │
                            │   (Integration API)     │     │    (#security-alerts)   │
                            └─────────────────────────┘     └─────────────────────────┘
```

---

## 🛠️ Step-by-Step Implementation Guide

### 1. Create a Discord Webhook
1. Open your Discord server settings -> **Integrations** -> **Webhooks** -> **New Webhook**.
2. **Name**: `AWS-Alerts` (or your preferred name).
3. Select the channel where you want security alerts to land.
4. Click **Copy Webhook URL** and save it securely for later use.

---

### 2. Create a New SNS Topic for Discord
1. Navigate to **Simple Notification Service (SNS)** -> **Topics** -> **Create topic**.
2. **Name**: `discord-alerts` (or `security-alerts-discord`).
3. **Type**: Standard.
4. Click **Create topic**.

---

### 3. Deploy the AWS Lambda Function (Bridge)

#### A. Create the Function
1. Navigate to **AWS Lambda** -> **Create function**.
2. **Name**: `cloudwatch-to-discord`.
3. **Runtime**: Python 3.12.
4. **Permissions**: Create a new role with basic Lambda execution permissions.
5. Click **Create function**.

#### B. Add the Code
Paste the Python script into the inline editor (`lambda_function.py`):

```python
import json
import urllib3
import os

http = urllib3.PoolManager()

def lambda_handler(event, context):
    # 1. Extract the alarm message from the SNS payload
    sns_message = event['Records'][0]['Sns']['Message']
    alarm = json.loads(sns_message)
    
    # 2. Format the payload for Discord
    texte = f"🚨 **{alarm['AlarmName']}** est en état **{alarm['NewStateValue']}**\n{alarm['NewStateReason']}"
    
    # 3. Deliver to Discord Webhook
    webhook_url = os.environ['DISCORD_WEBHOOK_URL']
    data = {"content": texte}
    
    http.request(
        'POST',
        webhook_url,
        body=json.dumps(data),
        headers={'Content-Type': 'application/json'}
    )
    
    return {"status": "ok"}
```

### C. Configure Environment Variables
In Lambda, go to Configuration -> Environment variables -> Edit.

Add variable:

- Key: DISCORD_WEBHOOK_URL

- Value: [Paste your Discord Webhook URL here]

- Click Save.

### D. Adjust Timeout
Go to Configuration -> General configuration -> Edit.

- Set Timeout: 10 seconds.

- Click Save.

## 4. Subscribe Lambda to the SNS Topic
Return to SNS -> Topics -> discord-alerts -> Subscriptions.

- Click Create subscription.

- Protocol: AWS Lambda.

- Endpoint: Select cloudwatch-to-discord.

- Click Create subscription. (Status will show "Confirmed").

## 5. Connect Your CloudWatch Alarm
Navigate to CloudWatch -> Alarms -> Choose your target alarm -> Edit.

Under Configure actions:

- Alarm state trigger: In alarm.

- Send notification to: Select the discord-alerts SNS topic.

- Update alarm.

## 6. Test the Integration
Manual Trigger (Sanity Check)
- Go to SNS -> Topics -> discord-alerts -> Publish message.

- Paste the test payload:
```
{
  "AlarmName": "Test Discord",
  "NewStateValue": "ALARM", 
  "NewStateReason": "This is a manual test"
}
```
- Click Publish message and verify the message appears in Discord.

- Real Security Event Test
- Generate 5 failed login attempts on the AWS console.

- Wait 5-10 minutes for evaluation.

- Check Discord for the automated alert notification.



