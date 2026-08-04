# 🛡️ Suspicious Connections Alert

[![AWS](https://img.shields.io/badge/AWS-CloudTrail%20%7C%20CloudWatch%20%7C%20SNS-orange?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)
[![Security](https://img.shields.io/badge/Security-Alerting%20%26%20Monitoring-red?style=flat-square)](https://aws.amazon.com/security/)

## 📌 Project Overview

Monitoring AWS Management Console login attempts is essential to detecting unauthorized access and brute-force attempts early. 

This project sets up an automated security alerting pipeline using native AWS services (**CloudTrail**, **CloudWatch**, and **SNS**). It tracks console logins across all regions, triggers an alert when multiple sign-in failures occur, and provides CloudWatch Logs Insights queries to inspect suspicious events.

---

## 📐 Architecture Flow
