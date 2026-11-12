# Broken Scenario: CI/CD Pipeline

**Difficulty**: Advanced
**Profile**: `cicd`

---

## Scenario

The CI pipeline in Gitea/Jenkins was working but a recent commit broke it. The pipeline fails at the "test" stage. Your job: diagnose and fix it.

---

## Setup

```bash
./run.sh start cicd
```

Access:
- Gitea: http://localhost:3000 (gitea/gitea)
- Jenkins: http://localhost:8090 (admin/admin)
- Registry: http://localhost:5000

---

## The broken Jenkinsfile

This `Jenkinsfile` has multiple bugs:

```groovy
pipeline {
    agent {
        docker {
            image 'python:3.12-slim'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        REGISTRY = 'localhost:5000'
        IMAGE_NAME = 'sample-api'
    }

    stages {
        stage('Install') {
            steps {
                sh 'pip install -r apps/sample-api/requirements.txt'
            }
        }

        stage('Test') {
            steps {
                // Bug 1: running pytest without installing it
                sh 'pytest apps/sample-api/tests/'
            }
        }

        stage('Build') {
            steps {
                // Bug 2: docker not available in python:3.12-slim agent
                sh 'docker build -t ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} apps/sample-api/'
            }
        }

        stage('Push') {
            steps {
                // Bug 3: pushing to an insecure registry without configuring Docker daemon
                sh 'docker push ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}'
            }
        }
    }

    post {
        always {
            // Bug 4: archiving files that don't exist
            archiveArtifacts artifacts: 'test-results/*.xml', allowEmptyArchive: false
        }
    }
}
```

---

## Tasks

1. Create a Gitea repository and push the Jenkinsfile
2. Create a Jenkins pipeline job pointing to the repo
3. Run the pipeline — observe all failure points
4. Fix each bug and re-run until the pipeline passes

---

## Bug hints

- Bug 1: pytest is not in requirements.txt — how do you install test dependencies separately?
- Bug 2: docker CLI is not in python:3.12-slim — need a different agent or docker-in-docker approach
- Bug 3: Docker by default rejects HTTP registries — needs `--insecure-registry` in daemon.json
- Bug 4: `allowEmptyArchive: false` fails when no test XML files exist

---

## Solution validation

```bash
# Pipeline shows green in Jenkins
# Image appears in registry
curl http://localhost:5000/v2/_catalog
# {"repositories":["sample-api"]}

curl http://localhost:5000/v2/sample-api/tags/list
# {"name":"sample-api","tags":["1","2",...]}
```
