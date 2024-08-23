FROM ubuntu:22.04
ENV LANG C.UTF-8
ENV TZ=Africa/Lagos
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    nano \
    git  \
    libpq-dev  \
    make \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    libcairo2  \
    libpango-1.0-0  \
    libpangocairo-1.0-0  \
    libgdk-pixbuf2.0-0  \
    libffi-dev  \
    fonts-bebas-neue \
    shared-mime-info \
    supervisor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Employing the layer caching strategy
COPY requirements.txt /
RUN pip3 install --upgrade setuptools
RUN pip3 install --no-cache-dir -r /requirements.txt

RUN apt-get remove -y git

# Move the source code into the main folder
COPY . /app

# Change working directory 
WORKDIR /app

CMD [ "uvicorn", "main:app", "--host","0.0.0.0", "--port", "8080", "--workers", "1", "--reload"]