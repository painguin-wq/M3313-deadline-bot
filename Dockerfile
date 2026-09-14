FROM python:3.12-bookworm
STOPSIGNAL SIGINT
WORKDIR /app

# make ru_RU.UTF-8 locale available
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install \
    --no-install-recommends -y locales && rm -r /var/lib/apt/lists/* && \
    printf "en_US.UTF-8 UTF-8\nru_RU.UTF-8 UTF-8" >/etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py DEADLINES.json ./
CMD ["python3", "-u", "main.py"]
