# Stage 1: Build environment with Poetry
FROM python:3.9-slim as builder

ENV POETRY_VERSION="1.7.1" # Pin a specific Poetry version for reproducibility
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_NO_INTERACTION="1" # Ensure Poetry doesn't ask for interactive input
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

# Install dependencies (without installing the project itself yet, and no dev dependencies for runtime)
# Using --no-ansi for cleaner logs in CI
RUN poetry install --no-root --no-dev --no-ansi

# Stage 2: Runtime environment
FROM python:3.9-slim as runtime

# Environment variables for the runtime
ENV PYTHONUNBUFFERED="1" # Ensures print statements appear without delay
ENV PYTHONDONTWRITEBYTECODE="1" # Prevents .pyc file generation

WORKDIR /app

# Copy the virtual env from the builder stage. This contains all dependencies.
COPY --from=builder /app/.venv/ /.venv/
# Copy the application code into the container
COPY . .

# Activate the virtual environment by adjusting PATH
# This makes `release-tool` (installed by poetry into .venv/bin) directly executable.
ENV PATH="/app/.venv/bin:$PATH"

# Set the entrypoint for the release tool
ENTRYPOINT ["release-tool"]
# Default command if the image is run without arguments
CMD ["--help"]
