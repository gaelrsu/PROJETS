# 🔔 AWS CloudWatch Alarms to Discord Notification

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

