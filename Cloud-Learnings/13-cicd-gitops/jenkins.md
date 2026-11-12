← [Previous: GitLab CI](./gitlab-ci.md) | [Home](../README.md) | [Next: ArgoCD →](./argocd.md)

---

# Jenkins

Jenkins is the most widely deployed open-source CI/CD server. It supports declarative and scripted pipelines, a massive plugin ecosystem, and flexible on-premises or cloud deployment.

---

## Installation

```bash
# Docker (quickstart)
docker run -d \
    -p 8080:8080 \
    -p 50000:50000 \
    -v jenkins_home:/var/jenkins_home \
    --name jenkins \
    jenkins/jenkins:lts-jdk21

# Get initial admin password
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword

# Kubernetes (Helm)
helm repo add jenkins https://charts.jenkins.io
helm repo update
helm upgrade --install jenkins jenkins/jenkins \
    --namespace jenkins \
    --create-namespace \
    --set controller.adminPassword=changeme \
    --set persistence.enabled=true
```

---

## Declarative Pipeline (Jenkinsfile)

```groovy
// Jenkinsfile
pipeline {
    agent {
        docker {
            image 'python:3.12-slim'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        APP_NAME     = 'my-app'
        REGISTRY     = 'registry.example.com'
        IMAGE        = "${REGISTRY}/${APP_NAME}"
        DEPLOY_SA    = credentials('aws-deploy-credentials')  // Injected as env vars
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        timestamps()
    }

    triggers {
        // Poll SCM every 5 minutes (use webhooks in production)
        // pollSCM('H/5 * * * *')
        githubPush()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint') {
            steps {
                sh 'pip install ruff --quiet && ruff check .'
            }
        }

        stage('Test') {
            steps {
                sh '''
                    pip install -r requirements-dev.txt --quiet
                    pytest tests/ -v \
                        --junitxml=test-results.xml \
                        --cov=src \
                        --cov-report=xml \
                        --tb=short
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]
                }
            }
        }

        stage('Build') {
            when {
                branch 'main'
            }
            steps {
                script {
                    def imageTag = "${IMAGE}:${env.GIT_COMMIT.take(7)}"
                    sh """
                        docker build \
                            --cache-from ${IMAGE}:latest \
                            --build-arg BUILDKIT_INLINE_CACHE=1 \
                            -t ${imageTag} \
                            -t ${IMAGE}:latest \
                            .
                        docker push ${imageTag}
                        docker push ${IMAGE}:latest
                    """
                    env.IMAGE_TAG = imageTag
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([
                    string(credentialsId: 'aws-region', variable: 'AWS_DEFAULT_REGION'),
                    string(credentialsId: 'aws-account-id', variable: 'AWS_ACCOUNT_ID')
                ]) {
                    sh '''
                        aws ecs update-service \
                            --cluster my-app-staging \
                            --service my-app-api \
                            --force-new-deployment
                        aws ecs wait services-stable \
                            --cluster my-app-staging \
                            --services my-app-api
                    '''
                }
            }
        }

        stage('Approve Production') {
            when {
                branch 'main'
            }
            steps {
                timeout(time: 1, unit: 'HOURS') {
                    input message: "Deploy ${env.IMAGE_TAG} to production?",
                          ok: 'Deploy',
                          submitterParameter: 'APPROVER'
                }
                echo "Approved by: ${env.APPROVER}"
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    aws ecs update-service \
                        --cluster my-app-production \
                        --service my-app-api \
                        --force-new-deployment
                    aws ecs wait services-stable \
                        --cluster my-app-production \
                        --services my-app-api
                '''
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            slackSend(
                channel: '#deployments',
                color: 'good',
                message: "✅ ${env.APP_NAME} deployed to production: ${env.IMAGE_TAG}"
            )
        }
        failure {
            slackSend(
                channel: '#deployments',
                color: 'danger',
                message: "❌ Pipeline failed: ${env.APP_NAME} build #${env.BUILD_NUMBER}"
            )
            emailext(
                to: 'team@my-app.com',
                subject: "Jenkins Build Failed: ${env.JOB_NAME}",
                body: "Build URL: ${env.BUILD_URL}"
            )
        }
    }
}
```

---

## Shared Libraries

Shared libraries let you extract common pipeline logic into a reusable library in a separate Git repository.

```
(library repo: my-org/jenkins-shared-lib)
vars/
├── standardPipeline.groovy    # Global function
└── dockerBuild.groovy
src/
└── com/myorg/
    ├── Docker.groovy          # Class
    └── Notifier.groovy
resources/
└── scripts/
    └── health-check.sh
```

```groovy
// vars/dockerBuild.groovy
def call(Map config = [:]) {
    String image    = config.image    ?: error("image is required")
    String context  = config.context  ?: '.'
    String registry = config.registry ?: 'registry.example.com'

    stage("Build ${image}") {
        def tag = "${registry}/${image}:${env.GIT_COMMIT.take(7)}"
        sh """
            docker build --cache-from ${registry}/${image}:latest \
                -t ${tag} -t ${registry}/${image}:latest ${context}
            docker push ${tag}
            docker push ${registry}/${image}:latest
        """
        return tag
    }
}
```

```groovy
// Jenkinsfile — use the shared library
@Library('my-jenkins-lib@v1.2.0') _

pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                script {
                    def tag = dockerBuild(image: 'my-app/api', context: 'backend/')
                    env.IMAGE_TAG = tag
                }
            }
        }
    }
}
```

---

## Multibranch Pipeline

```groovy
// Jenkinsfile — multibranch pipeline adapts behavior per branch
pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh 'make test'
            }
        }

        stage('Deploy') {
            when {
                anyOf {
                    branch 'main'
                    branch 'release/*'
                    tag pattern: 'v\\d+\\.\\d+\\.\\d+', comparator: 'REGEXP'
                }
            }
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        sh 'make deploy-staging'
                    } else if (env.TAG_NAME) {
                        sh "make deploy-production VERSION=${env.TAG_NAME}"
                    }
                }
            }
        }
    }
}
```

---

## Jenkins Configuration as Code (JCasC)

```yaml
# jenkins.yaml — configure Jenkins declaratively
jenkins:
  systemMessage: "Jenkins configured with JCasC"
  numExecutors: 0

  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: admin
          password: "${JENKINS_ADMIN_PASSWORD}"

  authorizationStrategy:
    roleBased:
      roles:
        global:
          - name: admin
            permissions: [Overall/Administer]
            assignments: [admin]

credentials:
  system:
    domainCredentials:
      - credentials:
          - aws:
              accessKey: "${AWS_ACCESS_KEY_ID}"
              secretKey: "${AWS_SECRET_ACCESS_KEY}"
              id: aws-credentials
              scope: GLOBAL

tool:
  git:
    installations:
      - name: Default
        home: git
```

---

## References

- [Jenkins documentation](https://www.jenkins.io/doc/)
- [Declarative pipeline syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Shared libraries](https://www.jenkins.io/doc/book/pipeline/shared-libraries/)
- [JCasC plugin](https://plugins.jenkins.io/configuration-as-code/)

---

← [Previous: GitLab CI](./gitlab-ci.md) | [Home](../README.md) | [Next: ArgoCD →](./argocd.md)
