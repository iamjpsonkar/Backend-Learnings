← [Previous: CodeDeploy](./codedeploy.md) | [Home](../../README.md) | [Next: AWS IaC →](../13-iac/README.md)

---

# AWS CodePipeline

CodePipeline is a fully managed CI/CD orchestration service. It models your release workflow as a series of stages (source → build → test → approve → deploy) and triggers them automatically on every code change.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Pipeline** | An ordered sequence of stages |
| **Stage** | A named group of actions (e.g., Source, Build, Deploy) |
| **Action** | A single step: source fetch, build, test, approval, invoke Lambda, deploy |
| **Artifact** | Files passed between stages via S3 (encrypted with KMS) |
| **Transition** | Connection between stages — can be disabled to gate deployments |
| **Execution** | One run of the pipeline triggered by a source change or manually |
| **V2 pipeline** | Newer pipeline type with execution mode (queued/superseded/parallel), cheaper at $0.002/action/month |

---

## Complete Pipeline: GitHub → CodeBuild → ECS

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ARTIFACT_BUCKET="my-pipeline-artifacts-${ACCOUNT_ID}"
PIPELINE_ROLE="arn:aws:iam::$ACCOUNT_ID:role/CodePipelineServiceRole"

# Create artifact bucket (required by CodePipeline)
aws s3api create-bucket --bucket $ARTIFACT_BUCKET --region us-east-1
aws s3api put-bucket-versioning \
    --bucket $ARTIFACT_BUCKET \
    --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption \
    --bucket $ARTIFACT_BUCKET \
    --server-side-encryption-configuration '{
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"}}]
    }'

# Create the pipeline
aws codepipeline create-pipeline \
    --pipeline '{
        "name": "my-app-production",
        "roleArn": "'"$PIPELINE_ROLE"'",
        "pipelineType": "V2",
        "executionMode": "SUPERSEDED",
        "artifactStore": {
            "type": "S3",
            "location": "'"$ARTIFACT_BUCKET"'",
            "encryptionKey": {"id": "alias/codepipeline-key", "type": "KMS"}
        },
        "stages": [
            {
                "name": "Source",
                "actions": [{
                    "name": "GitHub",
                    "actionTypeId": {
                        "category": "Source",
                        "owner": "AWS",
                        "provider": "CodeStarSourceConnection",
                        "version": "1"
                    },
                    "configuration": {
                        "ConnectionArn": "arn:aws:codestar-connections:us-east-1:'"$ACCOUNT_ID"':connection/abc123",
                        "FullRepositoryId": "my-org/my-app",
                        "BranchName": "main",
                        "DetectChanges": "true"
                    },
                    "outputArtifacts": [{"name": "SourceOutput"}],
                    "runOrder": 1
                }]
            },
            {
                "name": "Build",
                "actions": [{
                    "name": "CodeBuild",
                    "actionTypeId": {
                        "category": "Build",
                        "owner": "AWS",
                        "provider": "CodeBuild",
                        "version": "1"
                    },
                    "configuration": {
                        "ProjectName": "my-app-build"
                    },
                    "inputArtifacts": [{"name": "SourceOutput"}],
                    "outputArtifacts": [{"name": "BuildOutput"}],
                    "runOrder": 1
                }]
            },
            {
                "name": "DeployStaging",
                "actions": [{
                    "name": "ECS-Staging",
                    "actionTypeId": {
                        "category": "Deploy",
                        "owner": "AWS",
                        "provider": "ECS",
                        "version": "1"
                    },
                    "configuration": {
                        "ClusterName": "staging",
                        "ServiceName": "my-app-backend",
                        "FileName": "imagedefinitions.json"
                    },
                    "inputArtifacts": [{"name": "BuildOutput"}],
                    "runOrder": 1
                }]
            },
            {
                "name": "ApproveProduction",
                "actions": [{
                    "name": "ManualApproval",
                    "actionTypeId": {
                        "category": "Approval",
                        "owner": "AWS",
                        "provider": "Manual",
                        "version": "1"
                    },
                    "configuration": {
                        "NotificationArn": "arn:aws:sns:us-east-1:'"$ACCOUNT_ID"':pipeline-approvals",
                        "CustomData": "Review staging and approve production deployment",
                        "ExternalEntityLink": "https://staging.example.com"
                    },
                    "runOrder": 1
                }]
            },
            {
                "name": "DeployProduction",
                "actions": [{
                    "name": "CodeDeploy-ECS",
                    "actionTypeId": {
                        "category": "Deploy",
                        "owner": "AWS",
                        "provider": "CodeDeployToECS",
                        "version": "1"
                    },
                    "configuration": {
                        "ApplicationName": "my-app-ecs",
                        "DeploymentGroupName": "production",
                        "TaskDefinitionTemplateArtifact": "BuildOutput",
                        "TaskDefinitionTemplatePath": "taskdef.json",
                        "AppSpecTemplateArtifact": "BuildOutput",
                        "AppSpecTemplatePath": "appspec.yml",
                        "Image1ArtifactName": "BuildOutput",
                        "Image1ContainerName": "IMAGE1_NAME"
                    },
                    "inputArtifacts": [
                        {"name": "BuildOutput"}
                    ],
                    "runOrder": 1
                }]
            }
        ]
    }'
```

---

## Managing Pipelines

```bash
# Get pipeline state (current execution status per stage)
aws codepipeline get-pipeline-state \
    --name my-app-production \
    --query 'stageStates[*].{Stage:stageName,Status:latestExecution.status,LastChange:latestExecution.lastStatusChange}' \
    --output table

# List pipeline executions
aws codepipeline list-pipeline-executions \
    --pipeline-name my-app-production \
    --max-results 5 \
    --query 'pipelineExecutionSummaries[*].{ID:pipelineExecutionId,Status:status,Trigger:trigger.triggerType,Start:startTime}' \
    --output table

# Manually start a pipeline execution
aws codepipeline start-pipeline-execution \
    --name my-app-production \
    --client-request-token $(uuidgen)

# Approve a manual approval action
aws codepipeline put-approval-result \
    --pipeline-name my-app-production \
    --stage-name ApproveProduction \
    --action-name ManualApproval \
    --result summary="Approved after staging validation",status=Approved \
    --token $(aws codepipeline get-pipeline-state \
        --name my-app-production \
        --query 'stageStates[?stageName==`ApproveProduction`].actionStates[0].latestExecution.token' \
        --output text)

# Disable a stage transition (gate production deployments)
aws codepipeline disable-stage-transition \
    --pipeline-name my-app-production \
    --stage-name DeployProduction \
    --transition-type Inbound \
    --reason "Production freeze — holiday period"

# Re-enable after the freeze
aws codepipeline enable-stage-transition \
    --pipeline-name my-app-production \
    --stage-name DeployProduction \
    --transition-type Inbound
```

---

## Adding a Test Stage with CodeBuild

```bash
# Add an integration test stage between Build and DeployStaging
# (update the pipeline JSON to include a Test stage)
aws codepipeline update-pipeline \
    --pipeline "$(aws codepipeline get-pipeline --name my-app-production --query 'pipeline' | \
    python3 -c "
import sys, json
pipeline = json.load(sys.stdin)
pipeline['stages'].insert(2, {
    'name': 'IntegrationTest',
    'actions': [{
        'name': 'RunTests',
        'actionTypeId': {
            'category': 'Test',
            'owner': 'AWS',
            'provider': 'CodeBuild',
            'version': '1'
        },
        'configuration': {'ProjectName': 'my-app-integration-tests'},
        'inputArtifacts': [{'name': 'BuildOutput'}],
        'runOrder': 1
    }]
})
print(json.dumps(pipeline))
")"
```

---

## EventBridge Integration — Pipeline Notifications

```bash
# Notify on pipeline failure
aws events put-rule \
    --name "codepipeline-failure" \
    --event-pattern '{
        "source": ["aws.codepipeline"],
        "detail-type": ["CodePipeline Pipeline Execution State Change"],
        "detail": {
            "state": ["FAILED"],
            "pipeline": ["my-app-production"]
        }
    }' \
    --state ENABLED

aws events put-targets \
    --rule codepipeline-failure \
    --targets Id=ops-sns,Arn=arn:aws:sns:us-east-1:123456789012:ops-alerts

# CodePipeline also supports native notifications via CodeStar Notifications
aws codestar-notifications create-notification-rule \
    --name my-app-pipeline-notifications \
    --resource arn:aws:codepipeline:us-east-1:123456789012:my-app-production \
    --event-type-ids \
        codepipeline-pipeline-pipeline-execution-failed \
        codepipeline-pipeline-pipeline-execution-succeeded \
        codepipeline-pipeline-manual-approval-needed \
    --targets '[{"TargetType": "SNS", "TargetAddress": "arn:aws:sns:us-east-1:123456789012:ops-alerts"}]' \
    --detail-type FULL
```

---

## CodePipeline IAM Role

Key permissions the CodePipeline service role needs:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:GetBucketVersioning"], "Resource": "arn:aws:s3:::my-pipeline-artifacts*"},
        {"Effect": "Allow", "Action": ["codebuild:StartBuild", "codebuild:BatchGetBuilds"], "Resource": "arn:aws:codebuild:us-east-1:123456789012:project/my-app-build"},
        {"Effect": "Allow", "Action": ["codedeploy:CreateDeployment", "codedeploy:GetDeployment", "codedeploy:GetDeploymentConfig", "codedeploy:RegisterApplicationRevision", "codedeploy:GetApplicationRevision"], "Resource": "*"},
        {"Effect": "Allow", "Action": ["ecs:DescribeServices", "ecs:DescribeTaskDefinition", "ecs:DescribeTasks", "ecs:ListTasks", "ecs:RegisterTaskDefinition", "ecs:UpdateService"], "Resource": "*"},
        {"Effect": "Allow", "Action": ["sns:Publish"], "Resource": "arn:aws:sns:us-east-1:123456789012:pipeline-approvals"},
        {"Effect": "Allow", "Action": ["codestar-connections:UseConnection"], "Resource": "arn:aws:codestar-connections:us-east-1:123456789012:connection/*"},
        {"Effect": "Allow", "Action": ["kms:GenerateDataKey", "kms:Decrypt"], "Resource": "arn:aws:kms:us-east-1:123456789012:key/*"}
    ]
}
```

---

## References

- [CodePipeline documentation](https://docs.aws.amazon.com/codepipeline/latest/userguide/)
- [Action type reference](https://docs.aws.amazon.com/codepipeline/latest/userguide/reference-pipeline-structure.html)
- [GitHub connection setup](https://docs.aws.amazon.com/codepipeline/latest/userguide/connections-github.html)
- [CodePipeline pricing](https://aws.amazon.com/codepipeline/pricing/)
---

← [Previous: CodeDeploy](./codedeploy.md) | [Home](../../README.md) | [Next: AWS IaC →](../13-iac/README.md)
