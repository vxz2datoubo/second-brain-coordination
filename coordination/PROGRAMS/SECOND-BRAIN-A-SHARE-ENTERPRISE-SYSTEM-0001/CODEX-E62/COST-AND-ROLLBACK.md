# AWS A1 Cost and Rollback

agent_id: `CODEX`

For a tiny single-Region project using one asymmetric customer-managed KMS key, AWS currently lists about USD 1/month per key and USD 0.15 per 10,000 signing operations. Lambda's published free tier is 1 million requests and 400,000 GB-seconds/month; DynamoDB publishes a provisioned free tier including 25 RCUs, 25 WCUs, and 25 GB. These are estimates, not a guarantee: Region, taxes, account terms, logging, network/NAT, backup/PITR, monitoring, and retention can add cost.

Rollback is designed before activation: disable the requester role's issuer invocation, disable/revoke issuer policy, revoke outstanding ledger records, and disable KMS signing. Do not delete candidate packages or claim that a revoked/expired grant wrote formal knowledge. Actual key deletion, account/billing, and resource destruction require a later explicit user-approved runbook.

Sources: <https://aws.amazon.com/kms/pricing/>, <https://aws.amazon.com/lambda/pricing/>, <https://aws.amazon.com/dynamodb/pricing/>.
