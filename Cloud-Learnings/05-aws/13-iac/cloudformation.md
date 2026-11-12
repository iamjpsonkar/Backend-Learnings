← [Previous: AWS IaC](./README.md) | [Home](../../README.md) | [Next: CDK →](./cdk.md)

---

# AWS CloudFormation

CloudFormation provisions and manages AWS infrastructure from declarative YAML or JSON templates. AWS ensures stacks are created, updated, and deleted safely — rolling back automatically on failure.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Template** | YAML/JSON file describing resources and their relationships |
| **Stack** | A deployed instance of a template — all resources are managed together |
| **Change set** | A preview of what changes an update will make before applying |
| **Stack set** | Deploy the same template across multiple accounts and regions |
| **Nested stack** | A stack that includes another stack as a resource (`AWS::CloudFormation::Stack`) |
| **Drift** | Difference between the template and the actual resource configuration |
| **Parameter** | Input value passed at deploy time |
| **Output** | Value exported from a stack for use by other stacks |
| **Condition** | Template logic to conditionally create resources |
| **Transform** | Pre-processing macro (`AWS::Serverless-2016-10-31` for SAM) |

---

## Template Structure

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: "Production VPC with EC2 and RDS"

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues: [development, staging, production]
  InstanceType:
    Type: String
    Default: t3.medium
  DBPassword:
    Type: String
    NoEcho: true
    MinLength: 8

Mappings:
  RegionAMI:
    us-east-1:
      AMI: ami-0c55b159cbfafe1f0
    eu-west-1:
      AMI: ami-01f3682deed220c2a

Conditions:
  IsProduction: !Equals [!Ref Environment, production]

Resources:
  # VPC
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-vpc"
        - Key: Environment
          Value: !Ref Environment

  PublicSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs ""]
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-public-1"

  # Security Group
  WebSG:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: "Web tier — allow HTTPS inbound"
      VpcId: !Ref VPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-web-sg"

  # EC2 Instance
  WebServer:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: !Ref InstanceType
      ImageId: !FindInMap [RegionAMI, !Ref AWS::Region, AMI]
      SubnetId: !Ref PublicSubnet
      SecurityGroupIds:
        - !Ref WebSG
      IamInstanceProfile: !Ref InstanceProfile
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash -xe
          yum update -y
          amazon-linux-extras install nginx1 -y
          systemctl enable nginx
          systemctl start nginx
      Tags:
        - Key: Name
          Value: !Sub "${Environment}-web-server"

  # IAM
  InstanceRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
      Tags:
        - Key: Environment
          Value: !Ref Environment

  InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref InstanceRole

  # Production-only WAF (conditional)
  WebACL:
    Type: AWS::WAFv2::WebACL
    Condition: IsProduction
    Properties:
      Name: !Sub "${Environment}-waf"
      Scope: REGIONAL
      DefaultAction:
        Allow: {}
      VisibilityConfig:
        SampledRequestsEnabled: true
        CloudWatchMetricsEnabled: true
        MetricName: !Sub "${Environment}-waf"
      Rules: []

Outputs:
  VPCId:
    Description: "VPC ID"
    Value: !Ref VPC
    Export:
      Name: !Sub "${AWS::StackName}-VPCId"

  WebServerPublicIP:
    Description: "Web server public IP"
    Value: !GetAtt WebServer.PublicIp

  WebSGId:
    Description: "Web security group ID"
    Value: !Ref WebSG
    Export:
      Name: !Sub "${AWS::StackName}-WebSGId"
```

---

## Deploying and Managing Stacks

```bash
# Validate a template before deploying
aws cloudformation validate-template \
    --template-body file://template.yml

# Create a stack
aws cloudformation create-stack \
    --stack-name my-app-production \
    --template-body file://template.yml \
    --parameters \
        ParameterKey=Environment,ParameterValue=production \
        ParameterKey=InstanceType,ParameterValue=t3.medium \
        ParameterKey=DBPassword,ParameterValue=SecurePass123! \
    --capabilities CAPABILITY_NAMED_IAM \
    --tags Key=Environment,Value=production Key=ManagedBy,Value=CloudFormation

# Wait for stack creation
aws cloudformation wait stack-create-complete --stack-name my-app-production

# Get stack outputs
aws cloudformation describe-stacks \
    --stack-name my-app-production \
    --query 'Stacks[0].Outputs[*].{Key:OutputKey,Value:OutputValue}' \
    --output table

# Create a change set before updating (safe update workflow)
aws cloudformation create-change-set \
    --stack-name my-app-production \
    --change-set-name update-instance-type \
    --template-body file://template.yml \
    --parameters \
        ParameterKey=Environment,UsePreviousValue=true \
        ParameterKey=InstanceType,ParameterValue=t3.large \
        ParameterKey=DBPassword,UsePreviousValue=true \
    --capabilities CAPABILITY_NAMED_IAM

# Review what will change
aws cloudformation describe-change-set \
    --stack-name my-app-production \
    --change-set-name update-instance-type \
    --query 'Changes[*].ResourceChange.{Action:Action,Resource:LogicalResourceId,Type:ResourceType,Replacement:Replacement}' \
    --output table

# Execute the change set
aws cloudformation execute-change-set \
    --stack-name my-app-production \
    --change-set-name update-instance-type

aws cloudformation wait stack-update-complete --stack-name my-app-production

# Delete a stack (removes all resources)
aws cloudformation delete-stack --stack-name my-app-production
aws cloudformation wait stack-delete-complete --stack-name my-app-production
```

---

## Cross-Stack References

```bash
# Stack A exports the VPC ID
# Outputs section in stack-a.yml:
# VPCId:
#   Value: !Ref VPC
#   Export:
#     Name: stack-a-VPCId

# Stack B imports it
# Resources section in stack-b.yml:
# WebServer:
#   Properties:
#     SubnetId:
#       Fn::ImportValue: stack-a-VPCId

# List all exports across stacks
aws cloudformation list-exports \
    --query 'Exports[*].{Name:Name,Value:Value,StackName:ExportingStackId}' \
    --output table
```

---

## Drift Detection

```bash
# Initiate drift detection on a stack
DRIFT_ID=$(aws cloudformation detect-stack-drift \
    --stack-name my-app-production \
    --query 'StackDriftDetectionId' --output text)

# Wait a moment for detection to complete
aws cloudformation describe-stack-drift-detection-status \
    --stack-drift-detection-id $DRIFT_ID \
    --query '{Status:DetectionStatus,DriftStatus:StackDriftStatus}'

# List drifted resources
aws cloudformation describe-stack-resource-drifts \
    --stack-name my-app-production \
    --stack-resource-drift-status-filters MODIFIED DELETED \
    --query 'StackResourceDrifts[*].{Resource:LogicalResourceId,Type:ResourceType,Drift:StackResourceDriftStatus}' \
    --output table
```

---

## Nested Stacks

```yaml
# Parent template referencing child stacks
Resources:
  NetworkingStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: "https://s3.amazonaws.com/my-templates/networking.yml"
      Parameters:
        Environment: !Ref Environment
        CidrBlock: 10.0.0.0/16
      Tags:
        - Key: Environment
          Value: !Ref Environment

  ComputeStack:
    Type: AWS::CloudFormation::Stack
    DependsOn: NetworkingStack
    Properties:
      TemplateURL: "https://s3.amazonaws.com/my-templates/compute.yml"
      Parameters:
        VPCId: !GetAtt NetworkingStack.Outputs.VPCId
        SubnetIds: !GetAtt NetworkingStack.Outputs.SubnetIds
```

---

## Stack Sets (Multi-Account/Region)

```bash
# Deploy a security baseline stack to all accounts in an organization
aws cloudformation create-stack-set \
    --stack-set-name security-baseline \
    --template-body file://security-baseline.yml \
    --capabilities CAPABILITY_NAMED_IAM \
    --permission-model SERVICE_MANAGED \
    --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false

# Deploy to all accounts in an OU
aws cloudformation create-stack-instances \
    --stack-set-name security-baseline \
    --deployment-targets OrganizationalUnitIds=ou-root-abc123 \
    --regions us-east-1 eu-west-1 ap-southeast-1 \
    --operation-preferences FailureToleranceCount=0,MaxConcurrentCount=10

# Get stack set operation status
aws cloudformation describe-stack-set-operation \
    --stack-set-name security-baseline \
    --operation-id $(aws cloudformation list-stack-set-operations \
        --stack-set-name security-baseline \
        --query 'Summaries[0].OperationId' --output text) \
    --query '{Status:OperationPreferences,Summary:StackSetDriftDetectionDetails}'
```

---

## cfn-lint and Best Practices

```bash
# Install cfn-lint (validates CloudFormation templates)
pip install cfn-lint

# Lint a template
cfn-lint template.yml

# Format check with cfn-python-lint rules
cfn-lint template.yml --include-checks W

# Key best practices:
# 1. Always use change sets before updates in production
# 2. Set DeletionPolicy: Retain on stateful resources (RDS, S3)
# 3. Use SSM Parameter Store for dynamic values (AMI IDs, etc.)
# 4. Store sensitive parameters with NoEcho: true
# 5. Tag every resource with Environment, ManagedBy=CloudFormation, StackName
# 6. Use Outputs + Exports for cross-stack dependencies
# 7. Enable termination protection on production stacks
```

```bash
# Enable termination protection
aws cloudformation update-termination-protection \
    --stack-name my-app-production \
    --enable-termination-protection
```

---

## References

- [CloudFormation documentation](https://docs.aws.amazon.com/cloudformation/latest/userguide/)
- [Template reference](https://docs.aws.amazon.com/cloudformation/latest/userguide/aws-template-resource-type-ref.html)
- [Intrinsic functions](https://docs.aws.amazon.com/cloudformation/latest/userguide/intrinsic-function-reference.html)
- [cfn-lint](https://github.com/aws-cloudformation/cfn-lint)
- [CloudFormation pricing](https://aws.amazon.com/cloudformation/pricing/)
---

← [Previous: AWS IaC](./README.md) | [Home](../../README.md) | [Next: CDK →](./cdk.md)
