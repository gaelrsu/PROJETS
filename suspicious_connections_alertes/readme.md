# 🛡️ Suspicious Connections Alert

[![AWS](https://img.shields.io/badge/AWS-CloudTrail%20%7C%20CloudWatch%20%7C%20SNS-orange?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)
[![Security](https://img.shields.io/badge/Security-Alerting%20%26%20Monitoring-red?style=flat-square)](https://aws.amazon.com/security/)

## 📌 Project Overview

Monitoring AWS Management Console login attempts is essential to detecting unauthorized access and brute-force attempts early. 

This project sets up an automated security alerting pipeline using native AWS services (**CloudTrail**, **CloudWatch**, and **SNS**). It tracks console logins across all regions, triggers an alert when multiple sign-in failures occur, and provides CloudWatch Logs Insights queries to inspect suspicious events.

---

## 📐 Architecture Flow
AWS CloudTrail ──► CloudWatch Logs ──► CloudWatch Alarm ──► SNS Topic ──► Email / Webhook


---

## 🛠️ Step-by-Step Implementation

### 1. Activate AWS CloudTrail to Track Activity

#### A. Create Trail
1. Go to the AWS Console and search for **CloudTrail**.
2. Click on **Create Trail**.
3. **Trail name**: `security-trail`.
4. **Log storage**:
   - Select **Create a new S3 bucket**.
   - Set a unique bucket name (e.g., `my-cloudtrail-logs`).

#### B. Log Configuration
1. Check **Enable for all regions** (important for multi-region security).
2. Activate **Log file validation** (to verify logs have not been modified).
3. Activate **Server-side encryption** to secure logs.
4. Click **Create trail**.

---

### 2. Create an SNS Topic for Alerts

#### A. Create Topic
1. Go to **Simple Notification Service (SNS)**.
2. Click on **Create topic**.
3. **Name**: `security-alerts`.
4. **Type**: Standard.
5. Click **Create topic**.

#### B. Add Email Subscription
1. In SNS, go to **Subscriptions** and click **Create subscription**.
2. **Topic ARN**: Select `security-alerts`.
3. **Protocol**: Email.
4. **Endpoint**: Enter your email address.
5. Click **Create subscription**, then open your inbox and confirm the subscription email.

---

### 3. Verify CloudTrail Delivery to CloudWatch Logs

1. Go to the AWS Console and open **CloudTrail**.
2. Go to the **Trails** tab and ensure `security-trail` is active.
3. In the **CloudWatch Logs** column, check that log sending is enabled (enable it if it is not active).

---

### 4. Create a CloudWatch Alarm for Connection Failures

1. Go to **CloudWatch** -> **Alarms**.
2. Click on **Create Alarm**.
3. Select the log source (**CloudTrail log group**) or select **CloudTrail Metrics** -> **Signin Failures**.
4. Configure the rule/threshold:
   - **Statistic**: Sum
   - **Condition**: Greater than threshold (e.g., `> 5` failures in `5` minutes).
5. In **Actions**, select **Send notification to** -> `security-alerts` (SNS Topic).
6. Click **Create alarm**.

---

## 🔍 Checking & Querying CloudTrail Logs in CloudWatch

### 1. Access CloudTrail Logs
1. Go to **CloudWatch** -> **Logs** -> **Log groups**.
2. Search for the log group named `/aws/cloudtrail/...`.
3. Select it and click on **Logs Insights**.

### 2. Run Query to View Console Connections
In the CloudWatch Logs Insights query editor, paste the following query:

```
fields @timestamp, eventName, userIdentity.arn, sourceIPAddress, responseElements.ConsoleLogin
| filter eventName="ConsoleLogin"
| sort @timestamp desc
| limit 20
```

Query Breakdown:
- filter eventName="ConsoleLogin": Filters events specifically for console login attempts.

- fields ...: Displays the timestamp, user identity (ARN), source IP address, and login result (ConsoleLogin).

- sort @timestamp desc: Displays the most recent events first.

- limit 20: Returns the last 20 matching events.





























