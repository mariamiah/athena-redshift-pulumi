import pulumi
import pulumi_aws as aws
import json

def deploy_redshift_connector(name: str, glue_conn: str, subnet_ids: str, sg_ids: str, region="eu-central-1"):
    spill_bucket = aws.s3.Bucket(
        f"{name}-spill",
        lifecycle_rules=[aws.s3.BucketLifecycleRuleArgs(
            enabled=True,
            expiration=aws.s3.BucketLifecycleRuleExpirationArgs(
                days=7
            ),
            id="auto-delete"
        )]
    )

    role = aws.iam.Role(f"{name}-lambda-role",
        assume_role_policy='''{
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
          }]
        }'''
    )

    aws.iam.RolePolicyAttachment(f"{name}-lambda-basic",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

    inline_policy_doc = pulumi.Output.all(spill_bucket.arn).apply(lambda args: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["glue:GetConnection", "glue:GetConnections", "secretsmanager:GetSecretValue", "athena:*"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject"],
                "Resource": f"{args}/*"
            }
        ]
    }))

    aws.iam.RolePolicy(f"{name}-lambda-inline",
        role=role.id,
        policy=inline_policy_doc)

    connector = aws.serverlessrepository.CloudFormationStack(
        f"{name}-connector",
        application_id="arn:aws:serverlessrepo:us-east-1:292517598671:applications/AthenaRedshiftConnector",
        semantic_version="2025.8.1",
        parameters={
            "SecretNamePrefix": "athena-redshift-",
            "LambdaFunctionName": f"{name}-lambda",
            "SecurityGroupIds": "sg-0caa54aeae8b87cad",
            "SubnetIds": "subnet-07153934e12680abe,subnet-0205d851706777a9c",
            "SpillBucket": spill_bucket.id.apply(lambda name: name),
            "DefaultConnectionString": "redshift://jdbc:redshift://redshift-cluster-endpoint:5439/dev?user=user&password=pass"
        },
        capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_RESOURCE_POLICY"]
    )


    pulumi.export("spill_bucket", spill_bucket.bucket)
    pulumi.export("catalog_name", f"{name}_catalog")
