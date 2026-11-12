# Jenkins with Docker CLI pre-installed
# Base: jenkins/jenkins:lts-jdk17
# Adds: Docker CLI, Docker Compose v2, useful plugins

FROM jenkins/jenkins:lts-jdk17

USER root

# Install Docker CLI and useful tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    jq \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (not daemon — uses host socket)
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Add jenkins user to docker group (if needed for socket access)
RUN groupadd -f docker && usermod -aG docker jenkins

# Install Docker Compose v2 as plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Pre-install Jenkins plugins
# Skip initial setup wizard via JAVA_OPTS in compose
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false -Xmx512m"

# Copy plugins list
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt

RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt 2>/dev/null || \
    echo "[Jenkins] Plugin install may have partial failures — check on first run"

USER jenkins
