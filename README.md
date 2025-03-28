# Athena Redshift Connector with Pulumi (Python)

This project deploys the **Amazon Athena Redshift Federated Query Connector** via Pulumi.

## Features
- Deploys official Athena Redshift Connector (SAR)
- Creates S3 spill bucket with 7-day lifecycle
- Configures Lambda + IAM Role
- Supports Glue Connection, VPC Subnets, and Security Groups

## Requirements
- Python ≥ 3.8
- Pulumi & Pulumi AWS Provider
- Existing Redshift Cluster & Glue Connection
- Valid Subnets & Security Groups for Lambda

## Quickstart

```bash
# Install
brew install pulumi
pip install pulumi pulumi_aws

# Configure
pulumi login s3://<your-backend-bucket>
pulumi stack init dev
pulumi config set aws:region eu-central-1

# Deploy
pulumi up
