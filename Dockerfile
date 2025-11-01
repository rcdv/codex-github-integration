# Minimal Alpine-based OpenAI Codex environment
FROM alpine:latest

ARG HOST_UID=1000
ARG HOST_GID=1000

# Install minimal runtime dependencies
RUN apk add --no-cache \
    nodejs \
    npm \
    git \
    curl \
    ca-certificates \
    bash \
    sudo \
    shadow \
    python3 && \
    # Install build dependencies temporarily for mcp compilation
    apk add --no-cache --virtual .build-deps build-base libffi-dev && \
    # Install Docker CLI and SSH client
    curl -fsSL https://download.docker.com/linux/static/stable/aarch64/docker-27.4.1.tgz | \
    tar xz -C /usr/local/bin --strip-components=1 docker/docker && \
    apk add --no-cache openssh-client && \
    # Install uv (ultra-fast Python package manager) to /usr/local/bin
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    # Install MCP Python SDK to system Python using uv
    /usr/local/bin/uv pip install --system --break-system-packages "mcp[cli]" && \
    # Remove build dependencies after compilation
    apk del .build-deps

# Create docker group and dev user
RUN addgroup -g 998 docker 2>/dev/null || true && \
    addgroup -g $HOST_GID dev && \
    adduser -D -u $HOST_UID -G dev -s /bin/bash dev && \
    addgroup dev docker && \
    echo "dev ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER dev
WORKDIR /home/dev

# Setup SSH configuration
RUN mkdir -p /home/dev/.ssh && \
    chmod 700 /home/dev/.ssh && \
    ssh-keyscan -t rsa,ed25519 github.com >> /home/dev/.ssh/known_hosts 2>/dev/null || true

# Configure npm global prefix
RUN npm config set prefix /home/dev/.npm-global

# Setup PATH
ENV PATH="/home/dev/.npm-global/bin:/home/dev/.local/bin:${PATH}"
RUN echo 'export PATH="/home/dev/.npm-global/bin:/home/dev/.local/bin:${PATH}"' >> /home/dev/.bashrc && \
    echo 'export PATH="/home/dev/.npm-global/bin:/home/dev/.local/bin:${PATH}"' >> /home/dev/.profile

# Install OpenAI Codex CLI
RUN npm install -g @openai/codex

USER root
RUN rm -rf /tmp/* /var/cache/apk/* /home/dev/.cache

USER dev
WORKDIR /workspace
CMD ["/bin/bash"]
