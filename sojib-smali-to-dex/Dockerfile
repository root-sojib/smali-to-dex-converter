FROM eclipse-temurin:17-jre-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    SMALI_JAR=/opt/smali/smali.jar

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/smali /app

# Official Smali 3.0.10 fat JAR release asset; verify its published SHA-256.
RUN curl -fL --retry 3 \
    https://github.com/baksmali/smali/releases/download/v3.0.10/smali-3.0.10-fat.jar \
    -o /opt/smali/smali.jar \
    && echo "32fa0e88a6c397b3922201adf5f3e534fbaed5a663c71d0c558c3ddce0af844a  /opt/smali/smali.jar" | sha256sum -c -

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY . .

EXPOSE 10000
CMD ["sh", "-c", "gunicorn --workers 1 --threads 4 --timeout 150 --bind 0.0.0.0:${PORT:-10000} app:app"]
