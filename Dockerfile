FROM python:3.10.6-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    ghostscript \
    python3-tk \
    libgl1-mesa-glx \
    libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH "/usr/src/app:${PYTHONPATH}"
ENV GRADIO_SERVER_NAME "0.0.0.0"
ENV GRADIO_SERVER_PORT "7860"
ENV PORT "7860"
ENV TXT "custom"

# Set work directory
WORKDIR /usr/src/app

# Copy project
COPY . .

# Install dependencies
RUN python3 -m venv /opt/venv
RUN . /opt/venv/bin/activate && pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
ENV PATH="/opt/venv/bin:$PATH"

# Expose port
EXPOSE 7860

# Run server
CMD ["python3", "langchainApp.py"]