← [Previous: Cheatsheets Overview](./README.md) | [Home](../README.md) | [Next: kubectl →](./kubectl.md)

---

# AWS CLI Cheatsheet

```bash
# ── CONFIGURATION ─────────────────────────────────────────────────────────────
aws configure                                      # interactive setup
aws configure list                                 # show active config
aws configure list-profiles                        # list all profiles
aws sts get-caller-identity                        # who am I?
AWS_PROFILE=staging aws s3 ls                      # use a specific profile

# ── EC2 ────────────────────────────────────────────────────────────────────────
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=prod-*" \
    --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,IP:PrivateIpAddress,Type:InstanceType}'

aws ec2 start-instances --instance-ids i-0abc123
aws ec2 stop-instances  --instance-ids i-0abc123
aws ec2 reboot-instances --instance-ids i-0abc123

# Connect via SSM (no SSH key needed)
aws ssm start-session --target i-0abc123
aws ssm start-session --target i-0abc123 \
    --document-name AWS-StartPortForwardingSession \
    --parameters '{"portNumber":["5432"],"localPortNumber":["15432"]}'  # port forward

# Get instance metadata (from within instance)
curl -sf http://169.254.169.254/latest/meta-data/instance-id
curl -sf http://169.254.169.254/latest/meta-data/iam/security-credentials/

# ── S3 ─────────────────────────────────────────────────────────────────────────
aws s3 ls s3://my-bucket/prefix/                   # list
aws s3 cp file.txt s3://my-bucket/                 # upload
aws s3 cp s3://my-bucket/file.txt ./               # download
aws s3 sync ./local/ s3://my-bucket/prefix/ --delete  # sync (delete removed files)
aws s3 rm s3://my-bucket/file.txt                  # delete single file
aws s3 rm s3://my-bucket/prefix/ --recursive       # delete all in prefix
aws s3 mb s3://new-bucket --region us-east-1       # make bucket
aws s3 rb s3://empty-bucket                        # remove bucket

# Pre-signed URL (expires in 1 hour)
aws s3 presign s3://my-bucket/private-file.pdf --expires-in 3600

# Object metadata
aws s3api head-object --bucket my-bucket --key path/to/file.txt
aws s3api get-object-tagging --bucket my-bucket --key file.txt

# ── ECS ────────────────────────────────────────────────────────────────────────
aws ecs list-clusters
aws ecs list-services --cluster prod-cluster
aws ecs describe-services --cluster prod-cluster --services order-api \
    --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'

# Force new deployment (rolling update with same task definition)
aws ecs update-service --cluster prod-cluster --service order-api --force-new-deployment

# Scale a service
aws ecs update-service --cluster prod-cluster --service order-api --desired-count 5

# Get task logs
TASK_ID=$(aws ecs list-tasks --cluster prod-cluster --service-name order-api \
    --query 'taskArns[0]' --output text | awk -F/ '{print $NF}')
aws logs get-log-events \
    --log-group-name /ecs/order-api \
    --log-stream-name "ecs/api/$TASK_ID" \
    --limit 50 --query 'events[*].message' --output text

# Run one-off task (e.g., DB migration)
aws ecs run-task \
    --cluster prod-cluster \
    --task-definition order-api-migrate:1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-abc],securityGroups=[sg-xyz],assignPublicIp=DISABLED}"

# ── RDS ────────────────────────────────────────────────────────────────────────
aws rds describe-db-instances \
    --query 'DBInstances[*].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,Class:DBInstanceClass,Engine:Engine,Endpoint:Endpoint.Address}'

aws rds create-db-snapshot \
    --db-instance-identifier prod-postgres \
    --db-snapshot-identifier prod-postgres-$(date +%Y%m%d)

aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier restore-test \
    --db-snapshot-identifier prod-postgres-20240115

aws rds reboot-db-instance --db-instance-identifier prod-postgres --force-failover

# ── IAM ────────────────────────────────────────────────────────────────────────
aws iam get-user
aws iam list-roles --query 'Roles[*].{Name:RoleName,Created:CreateDate}'
aws iam list-attached-role-policies --role-name my-role
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::123456789012:role/my-role \
    --action-names s3:GetObject ec2:DescribeInstances \
    --query 'EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}'

# Rotate access key
aws iam create-access-key --user-name my-user
aws iam delete-access-key --user-name my-user --access-key-id AKIAXXXXXXXXXXXXXXXX

# ── CLOUDWATCH ─────────────────────────────────────────────────────────────────
# Tail logs (last 10 min)
aws logs tail /aws/lambda/my-function --since 10m --follow

# Filter logs for errors
aws logs filter-log-events \
    --log-group-name /ecs/order-api \
    --filter-pattern "ERROR" \
    --start-time $(($(date +%s) - 3600))000 \
    --query 'events[*].message' --output text

# Log Insights query
QUERY_ID=$(aws logs start-query \
    --log-group-name /ecs/order-api \
    --start-time $(($(date +%s) - 3600)) \
    --end-time $(date +%s) \
    --query-string 'filter @message like /ERROR/ | stats count(*) by bin(5min)' \
    --query 'queryId' --output text)
aws logs get-query-results --query-id $QUERY_ID

# ── SECRETS MANAGER ────────────────────────────────────────────────────────────
aws secretsmanager get-secret-value --secret-id prod/order-api/db-password \
    --query SecretString --output text
aws secretsmanager create-secret --name prod/my-secret --secret-string "myvalue"
aws secretsmanager put-secret-value --secret-id prod/my-secret --secret-string "newvalue"

# ── SSM PARAMETER STORE ────────────────────────────────────────────────────────
aws ssm get-parameter --name /prod/order-api/db-host --with-decryption --query Parameter.Value --output text
aws ssm put-parameter --name /prod/key --value "val" --type SecureString --overwrite
aws ssm get-parameters-by-path --path /prod/order-api/ --with-decryption \
    --query 'Parameters[*].{Name:Name,Value:Value}'

# ── USEFUL QUERY PATTERNS ──────────────────────────────────────────────────────
# Get account ID
aws sts get-caller-identity --query Account --output text

# List all regions
aws ec2 describe-regions --query 'Regions[*].RegionName' --output text

# Find resources by tag
aws resourcegroupstaggingapi get-resources \
    --tag-filters Key=environment,Values=prod \
    --query 'ResourceTagMappingList[*].ResourceARN'

# Wait commands (block until condition met)
aws ec2 wait instance-running --instance-ids i-0abc123
aws rds wait db-instance-available --db-instance-identifier prod-postgres
aws ecs wait services-stable --cluster prod-cluster --services order-api
```

---

← [Previous: Cheatsheets Overview](./README.md) | [Home](../README.md) | [Next: kubectl →](./kubectl.md)
