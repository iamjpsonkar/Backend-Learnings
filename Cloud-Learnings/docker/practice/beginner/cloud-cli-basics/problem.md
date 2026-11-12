# Cloud CLI Basics — Beginner

**Difficulty**: Beginner
**Profile**: `aws`
**Time estimate**: 45–60 minutes

---

## Scenario

You have AWS CLI access to LocalStack. Practice the most common CLI operations you will use every day.

---

## Setup

```bash
./run.sh start aws

# Enter the AWS CLI container
docker exec -it cloud-learnings-lab-aws-cli-1 sh

# Or run commands directly from your host
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

---

## Tasks

### Task 1 — S3 Basics

```bash
# 1a. List all S3 buckets
# 1b. Create a new bucket called "my-practice-bucket"
# 1c. Upload a file to it (create a test file first)
# 1d. List objects in the bucket
# 1e. Download the file back (to a different name)
# 1f. Delete the object
# 1g. Delete the bucket
```

### Task 2 — SQS Basics

```bash
# 2a. List all SQS queues
# 2b. Create a queue called "my-queue"
# 2c. Send a message: "Hello from SQS"
# 2d. Receive the message (note: ReceiptHandle)
# 2e. Delete the message using the ReceiptHandle
# 2f. Delete the queue
```

### Task 3 — DynamoDB Basics

```bash
# 3a. Create a table "users" with hash key "user_id" (String)
# 3b. Put an item: user_id="u001", name="Alice", age=30
# 3c. Get the item by user_id
# 3d. Update the item: set age=31
# 3e. Scan the table to see all items
# 3f. Delete the item
# 3g. Delete the table
```

### Task 4 — IAM Basics (LocalStack)

```bash
# 4a. List IAM users
# 4b. Create a user "practice-user"
# 4c. Create an access key for the user
# 4d. List the user's access keys
# 4e. Delete the user
```

### Task 5 — Output Formats

For any of the above commands, try all three output formats:
```bash
aws s3 ls --output json
aws s3 ls --output table
aws s3 ls --output text
```

Which is easiest to read? Which is easiest to script?

### Task 6 — Using --query

Filter output with JMESPath:
```bash
# List only bucket names (not dates)
aws s3api list-buckets --query "Buckets[].Name"

# Get only the first bucket name
aws s3api list-buckets --query "Buckets[0].Name" --output text
```

---

## Success criteria

- [ ] Created and deleted an S3 bucket with file upload/download
- [ ] Sent and received an SQS message
- [ ] Created a DynamoDB table and performed CRUD operations
- [ ] Used all three output formats
- [ ] Used `--query` to filter output
