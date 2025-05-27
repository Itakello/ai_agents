# Stage 1: Build stage (with dev dependencies for potential build steps if needed)
FROM python:3.13-slim AS builder

# Set working directory
WORKDIR /app

# Install poetry (or use pip if you stick to requirements.txt directly)
# RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock* README.md ./
# If not using poetry, copy requirements files instead:
COPY requirements.txt requirements-dev.txt ./

# Install dependencies
# Using pip for simplicity with requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # If you had build-time dev dependencies, you might install them here
    # && pip install --no-cache-dir -r requirements-dev.txt
    # Or with Poetry:
    # && poetry config virtualenvs.create false \
    # && poetry install --no-dev --no-interaction --no-ansi

# Copy the rest of the application code
COPY src ./src
# Copy other necessary files like .env.example, LICENSE, etc., if they need to be in the image
# COPY .env.example ./.env.example

# Stage 2: Final stage (runtime image)
FROM python:3.13-slim

WORKDIR /app

# Create a non-root user for security
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Copy built artifacts and necessary code from builder stage
COPY --from=builder /app/src ./src
COPY --from=builder /app/requirements.txt ./
# If you installed directly into site-packages in builder, you might copy the venv or site-packages
# COPY --from=builder /app/.venv ./.venv
# Or copy installed packages if not using a venv explicitly in the image
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Ensure scripts in .local/bin are discoverable and owned correctly if created by pip install --user
ENV PATH="/home/appuser/.local/bin:${PATH}"
RUN mkdir -p /home/appuser/.local/bin && chown -R appuser:appuser /home/appuser

# Install runtime dependencies (should already be included if copied from site-packages)
# If you only copied requirements.txt, you'd install again:
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main.py (if it's in the root, which it is in this template)
COPY main.py ./

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose port (if your application listens on a port, e.g., a web service component)
# EXPOSE 8000

# Command to run the application
# It's good practice to have an .env file mounted or secrets injected in a real deployment
# For development/testing, you might copy .env.example as .env, but AVOID for production images.
# COPY .env.example .env
CMD ["python", "main.py"]
