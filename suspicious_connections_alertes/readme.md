# 🛡️ AWS Suspicious Connections Alert & Detection Pipeline

[![AWS](https://img.shields.io/badge/AWS-CloudTrail%20%7C%20CloudWatch%20%7C%20SNS-orange?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)
[![Security](https://img.shields.io/badge/Security-Monitoring%20%26%20Alerting-red?style=flat-square)](https://aws.amazon.com/security/)


## 📌 Project Overview

In cloud infrastructure, compromised credentials and brute-force attacks against management interfaces represent one of the most critical security risks. Unmonitoring authentication attempts leaves cloud environments vulnerable to unauthorized access, lateral movement, and data exfiltration.

This project delivers a **lightweight, cost-effective Security Operations (SecOps) solution** designed to continuously monitor, detect, and alert on suspicious connection attempts to the **AWS Management Console**. By leveraging native AWS security tools—**AWS CloudTrail, Amazon CloudWatch Logs, and Amazon SNS**—this implementation captures authentication events across all regions, triggers real-time alerts for excessive login failures, and provides forensic queries for incident response.

---

## 📐 Architecture Overview
                            
                            +-----------------------------------+
                            |   AWS Console Access Attempt      |
                            +-----------------+-----------------+
                                              |
                                              v
                                  +-----------+-----------+
                                  |     AWS CloudTrail    |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------+-----------+
                                  |   CloudWatch Log Group |
                                  +-----------+-----------+
                                              |
               +------------------------------+------------------------------+
               |                                                             |
               v                                                             v
    +----------+----------+                                       +----------+----------+
    | CloudWatch Metric   |                                       | CloudWatch Logs     |
    | Filter & Alarm      |                                       | Insights (Query)    |
    +----------+----------+                                       +---------------------+
               |
               v
    +----------+----------+
    |     Amazon SNS      |
    +----------+----------+
               |
    +----------+----------+
    | Email / Lambda      |
    +---------------------+ 


---

## 🎯 Features & Capabilities

- **Multi-Region Trail Logging:** Centralized logging of all AWS management events across all active regions.
- **Log Integrity Validation:** Cryptographic file validation to prevent log tampering and unauthorized deletion.
- **Real-Time Automated Alerting:** Trigger notifications via Amazon SNS to Email or Webhooks (Discord/Slack via AWS Lambda) when brute-force thresholds are exceeded.
- **Forensic Threat Hunting:** Pre-configured CloudWatch Logs Insights queries to extract source IPs, IAM user identities, and MFA enforcement status.

---

## 🚀 Deployment Guide

### Step 1: Configure AWS CloudTrail

1. Open the **AWS CloudTrail Console** and click **Create Trail**.
2. Set **Trail Name**: `security-trail`.
3. Under **Log storage**:
   - Choose **Create a new S3 bucket**.
   - Set a globally unique bucket name (e.g., `aws-cloudtrail-logs-sec-ops-<account-id>`).
4. Under **Additional settings**:
   - ✅ **Enable for all regions** (Essential for detecting unauthorized multi-region activity).
   - ✅ **Log file validation** (Ensures log integrity).
   - ✅ **Server-side encryption** (SSE-KMS or SSE-S3).
5. Complete the setup by clicking **Create Trail**.

---

### Step 2: Enable CloudWatch Logs Integration

1. In your Trail settings (`security-trail`), navigate to **CloudWatch Logs**.
2. Click **Edit** and enable **CloudWatch Logs integration**.
3. Specify or create a Log Group (Default: `aws-cloudtrail-logs-security`).
4. Assign or create an IAM Role allowing CloudTrail to deliver logs to CloudWatch Logs.

---

### Step 3: Create Amazon SNS Alerting Topic

1. Open the **Amazon SNS Console** and select **Topics** > **Create Topic**.
2. **Type**: `Standard`.
3. **Name**: `security-alerts`.
4. Click **Create Topic**.
5. Under **Subscriptions**, click **Create subscription**:
   - **Topic ARN**: Select `security-alerts`.
   - **Protocol**: `Email` *(or `AWS Lambda` for Discord/Slack webhooks)*.
   - **Endpoint**: Enter your SOC / Security email address.
6. Check your inbox and click **Confirm Subscription**.

---

### Step 4: Configure CloudWatch Metric Filter & Alarm

#### 1. Create Metric Filter
- Navigate to **CloudWatch** > **Log groups** > Select `/aws/cloudtrail/...`.
- Under **Metric filters**, click **Create metric filter**.
- Set **Filter pattern**:
  ```json
  { ($.eventName = "ConsoleLogin") && ($.errorMessage = "Failed authentication") }


Filter name: ConsoleLoginFailures
Metric details:
- Metric namespace: CloudTrailSecurity
- Metric name: FailedConsoleLogins
- Metric value: 1

2. Create Alarm
Go to CloudWatch > Alarms > Create Alarm.
Select the metric CloudTrailSecurity / FailedConsoleLogins.
Set evaluation parameters:

- Statistic: Sum

- Period: 5 minutes

- Threshold: Greater than or equal to 5 (>= 5)

Set Actions:

- Trigger state: In ALARM

- Send notification to: security-alerts (SNS Topic).

- Name the alarm: Alarm-High-Console-Login-Failures.

## 🔍 Threat Hunting & Investigation (CloudWatch Logs Insights)
Use the following queries in CloudWatch Logs Insights (Log group: /aws/cloudtrail/...) for quick security investigations:

1. View Recent Console Logins & Results
```
fields @timestamp, eventName, userIdentity.arn, sourceIPAddress, responseElements.ConsoleLogin, errorMessage
| filter eventName = "ConsoleLogin"
| sort @timestamp desc
| limit 20
```

2. Detect Failed Login Attempts & Source IPs (Brute-Force Indicator)
```
fields @timestamp, userIdentity.userName, sourceIPAddress, errorMessage
| filter eventName = "ConsoleLogin" and responseElements.ConsoleLogin = "Failure"
| stats count(*) as FailedCount by sourceIPAddress, userIdentity.userName
| sort FailedCount desc
```

3. Identify Logins Without Multi-Factor Authentication (MFA)
```
fields @timestamp, userIdentity.arn, sourceIPAddress
| filter eventName = "ConsoleLogin" and additionalEventData.MFAUsed != "Yes"
| sort @timestamp desc
```

## 🔐 Security Best Practices & Enhancements
- [ ] S3 Lifecycle & Immutability: Enable S3 Object Lock (Compliance Mode) on the CloudTrail S3 bucket to ensure log immutability against ransomware/attacker tampering.

- [ ] KMS Customer Managed Keys (CMK): Encrypt CloudTrail logs using a KMS CMK with key policies restricting key deletion.

- [ ] AWS GuardDuty Integration: Complement metric alarms with AWS GuardDuty for ML-driven anomaly detection (e.g., UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.UnusualLocation).

- [ ] Infrastructure as Code (IaC): Deploy this architecture using Terraform or AWS CloudFormation for standard, reproducible environments.


