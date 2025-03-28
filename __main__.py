from modules import redshift_connector

redshift_connector.deploy_redshift_connector(
    name="test-redshift-2",
    glue_conn="your-glue-connection-name",
    subnet_ids="subnet-xxxxx,subnet-yyyyy",
    sg_ids="sg-zzzzzz"
)
