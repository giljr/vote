FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
# Copy project
COPY . /app/
# Expose port
EXPOSE 8000
# Run server (production style)
CMD ["gunicorn", "first_project.wsgi:application", "--bind", "0.0.0.0:8000"]