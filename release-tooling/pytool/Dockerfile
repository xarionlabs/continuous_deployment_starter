# Stage 1: Build environment with Poetry
FROM python:3.9-slim as builder

# Pin a specific Poetry version for reproducibility
ENV POETRY_VERSION="1.7.1"
ENV POETRY_HOME="/opt/poetry"
# Ensure Poetry doesn't ask for interactive input
ENV POETRY_NO_INTERACTION="1"
# Configure Poetry to create virtual environment in project directory
ENV POETRY_VENV_IN_PROJECT="1"
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install Poetry
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && echo "Installing Poetry version $POETRY_VERSION" \
    && curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
    && apt-get remove -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only files necessary for dependency installation first to leverage Docker cache
# poetry.lock* handles cases where poetry.lock might not exist on a fresh init (though it should)
COPY pyproject.toml poetry.lock* ./

# Install dependencies only first (for better caching)
RUN poetry install --only main --no-root --no-ansi

# Copy source code and install the project
COPY . .
RUN poetry install --only main --no-ansi

# Stage 2: Runtime environment
FROM python:3.9-slim as runtime

# Environment variables for the runtime
# Ensures print statements appear without delay
ENV PYTHONUNBUFFERED="1"
# Prevents .pyc file generation
ENV PYTHONDONTWRITEBYTECODE="1"

WORKDIR /app

# Copy the virtual env from the builder stage. This contains all dependencies.
COPY --from=builder /root/.cache/pypoetry/virtualenvs/ /opt/poetry/venvs/
# Copy the application code into the container
COPY . .

# Find and activate the virtual environment
RUN VENV_PATH=$(find /opt/poetry/venvs -name "release-tool-*" -type d | head -1) && \
    echo "Found virtual environment at: $VENV_PATH" && \
    ln -sf "$VENV_PATH" /app/.venv && \
    # Fix the shebang in the release-tool script to point to the correct python
    sed -i '1s|.*|#!/app/.venv/bin/python|' /app/.venv/bin/release-tool

# Activate the virtual environment by adjusting PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set the entrypoint for the release tool
ENTRYPOINT ["release-tool"]
# Default command if the image is run without arguments
CMD ["--help"]
