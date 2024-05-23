# Use a more recent and slim Python image
FROM python:3.11-slim-bullseye

# Install Poetry
RUN pip install poetry==1.6.1

RUN poetry config virtualenvs.create false
# Set the working directory
WORKDIR /app

# Copy only the necessary files for Poetry to install dependencies
COPY ./pyproject.toml ./poetry.lock* ./

# Install dependencies without creating a virtual environment
RUN poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application code
COPY ./app ./app

RUN poetry install --no-interaction --no-ansi

# Expose the port the app will run on
EXPOSE 5000

# Install Gunicorn
#RUN pip install --no-cache-dir gunicorn

# Start the application with Gunicorn
#CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app", "--workers", "4", "--threads", "4"]

CMD exec uvicorn wsgi:app --host 0.0.0.0 --port 8080