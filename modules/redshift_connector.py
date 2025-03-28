import pulumi
import pulumi_aws as aws
import json

def deploy_redshift_connector(
    name: str,
    glue_conn: str,
    subnet_ids: str,
    sg_ids: str,
    region: str = "eu-central-1"
):

    # Spill Bucket with lifecycle
    spill_bucket = aws.s3.Bucket(
        f"{name}-spill",
        lifecycle_rules=[
            aws.s3.BucketLifecycleRuleArgs(
                enabled=True,
                expiration=aws.s3.BucketLifecycleRuleExpirationArgs(
                    days=7
                ),
                id="auto-delete"
            )
        ]
    )

    # IAM Role for Lambda
    role = aws.iam.Role(
        f"{name}-lambda-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        })
    )

    # Basic Lambda permissions
    aws.iam.RolePolicyAttachment(
        f"{name}-lambda-basic",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )

    # Inline Policy (S3 + Glue + SecretsManager)
    inline_policy_doc = pulumi.Output.all(spill_bucket.arn).apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "glue:GetConnection",
                    "glue:GetConnections",
                    "secretsmanager:GetSecretValue",
                    "athena:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject"],
                "Resource": f"{arn}/*"
            }
        ]
    }))

    aws.iam.RolePolicy(
        f"{name}-lambda-inline",
        role=role.id,
        policy=inline_policy_doc
    )

    # Connector Deployment (SAR)
    connector = aws.serverlessrepository.CloudFormationStack(
        f"{name}-connector",
        application_id="arn:aws:serverlessrepo:us-east-1:292517598671:applications/AthenaRedshiftConnector",
        semantic_version="2025.8.1",
        parameters={
            "SecretNamePrefix": "athena-redshift-",
            "LambdaFunctionName": f"{name}-lambda",
            "SecurityGroupIds": sg_ids,
            "SubnetIds": subnet_ids,
            "SpillBucket": spill_bucket.id,
            "DefaultConnectionString": "redshift://jdbc:redshift://redshift-cluster-endpoint:5439/dev?user=user&password=pass"
        },
        capabilities=[
            "CAPABILITY_NAMED_IAM",
            "CAPABILITY_RESOURCE_POLICY"
        ]
    )

    # Exports
    pulumi.export("spill_bucket", spill_bucket.bucket)
    pulumi.export("catalog_name", f"{name}_catalog")
