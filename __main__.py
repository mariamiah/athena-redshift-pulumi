import pulumi
import pulumi_aws as aws
import json

# -------------------------------
# Load Config
# -------------------------------

config = pulumi.Config()
name = config.require("name")
subnet_ids = config.require("subnet_ids")
sg_ids = config.require("sg_ids")
spill_retention = int(config.get("spill_bucket_retention_days") or 7)
redshift_conn = config.require("default_redshift_connection")
account_id = aws.get_caller_identity().account_id
region = aws.config.region

# -------------------------------
# Spill Bucket
# -------------------------------

spill_bucket = aws.s3.Bucket(
    f"{name}-spill",
    lifecycle_rules=[
        aws.s3.BucketLifecycleRuleArgs(
            enabled=True,
            expiration=aws.s3.BucketLifecycleRuleExpirationArgs(
                days=spill_retention
            ),
            id="auto-delete"
        )
    ]
)

# -------------------------------
# IAM Role for Lambda
# -------------------------------

lambda_role = aws.iam.Role(
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

aws.iam.RolePolicyAttachment(
    f"{name}-lambda-basic-exec",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

# -------------------------------
# Inline Policy (SpillBucket, Glue, Secrets, Athena)
# -------------------------------

policy_doc = pulumi.Output.all(spill_bucket.arn).apply(lambda arn: json.dumps({
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
    role=lambda_role.id,
    policy=policy_doc
)

# -------------------------------
# Deploy the Redshift Connector (SAR)
# -------------------------------

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
        "DefaultConnectionString": redshift_conn
    },
    capabilities=[
        "CAPABILITY_NAMED_IAM",
        "CAPABILITY_RESOURCE_POLICY"
    ]
)

# -------------------------------
# Athena DataCatalog pointing to Connector Lambda
# -------------------------------
lambda_name = f"{name}-lambda"
connector_catalog = aws.athena.DataCatalog(
    f"{name}-catalog",
    name=f"{name}_catalog",
    type="LAMBDA",
    description="Athena Federated Query Catalog for Redshift Connector",
    parameters={
        "function": f"arn:aws:lambda:{region}:{account_id}:function:{lambda_name}"
    }
)

# -------------------------------
# Optional - Export outputs
# -------------------------------

pulumi.export("spill_bucket", spill_bucket.bucket)
pulumi.export("lambda_name", lambda_name)
pulumi.export("catalog_name", connector_catalog.name)
