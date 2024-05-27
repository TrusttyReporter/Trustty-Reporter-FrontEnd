# Use a more recent and slim Python image
FROM python:3.11-slim-bullseye

# Install Poetry
RUN pip install poetry==1.6.1

RUN poetry config virtualenvs.create false
# Set the working directory
WORKDIR /code

# Copy only the necessary files for Poetry to install dependencies
COPY ./pyproject.toml ./poetry.lock* ./

# Install dependencies without creating a virtual environment
RUN poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application code
COPY app ./app
COPY wsgi.py ./

RUN poetry install --no-interaction --no-ansi

# Expose the port the app will run on
EXPOSE 5000

# Install Gunicorn
RUN pip install --no-cache-dir gunicorn gevent

# Start the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app", "--workers", "1", "--worker-class", "gevent", "--threads", "2", "--timeout", "240"]