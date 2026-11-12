# Tasks — AWS with LocalStack

Complete each task in order. Check off each one as you go.

## Task 1 — Verify LocalStack is running

- [ ] Check LocalStack health
- [ ] List currently available services

```bash
curl http://localhost:4566/_localstack/health
```

Expected: JSON with service statuses.

---

## Task 2 — S3: Create and use a bucket

- [ ] Create a new S3 bucket named `my-practice-bucket`
- [ ] Upload a text file to the bucket
- [ ] List objects in the bucket
- [ ] Download the file
- [ ] Enable versioning on the bucket
- [ ] Delete the file and the bucket

---

## Task 3 — SQS: Create a queue and send messages

- [ ] Create a SQS queue named `my-queue`
- [ ] Get the queue URL
- [ ] Send 3 messages to the queue
- [ ] Receive and process messages
- [ ] Delete processed messages
- [ ] Get queue attributes (approximate message count)

---

## Task 4 — SNS: Topics and subscriptions

- [ ] Create an SNS topic named `my-topic`
- [ ] Subscribe the SQS queue to the topic
- [ ] Publish a message to the topic
- [ ] Verify the message arrived in the SQS queue

---

## Task 5 — DynamoDB: Table operations

- [ ] Create a DynamoDB table `my-table` with partition key `id`
- [ ] Put 3 items into the table
- [ ] Get an item by key
- [ ] Scan all items
- [ ] Delete an item

---

## Task 6 — Lambda: Create and invoke a function

- [ ] Write a simple Python Lambda function
- [ ] Create the Lambda function in LocalStack
- [ ] Invoke the function with test event
- [ ] Read the function logs

---

## Task 7 — Terraform with LocalStack

- [ ] Initialize Terraform with LocalStack provider
- [ ] Write a resource: `aws_s3_bucket`
- [ ] Run `terraform plan`
- [ ] Run `terraform apply`
- [ ] Verify the bucket was created in LocalStack
- [ ] Run `terraform destroy`

---

## Bonus Challenge

- Create an S3 event trigger that invokes Lambda when a file is uploaded
- Use SQS as a Lambda trigger

See [commands.md](commands.md) for all commands needed.
