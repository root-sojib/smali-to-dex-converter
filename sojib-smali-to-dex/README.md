# Sojib Bai — Smali to DEX Converter

Flask + Smali 3.0.10 + Docker. Deploy on Render using the included `render.yaml`.

## Features
- ZIP archive upload containing `.smali` files
- Multiple `.smali` files or browser folder selection
- Creates `classes.dex`
- Bengali mobile-friendly interface
- ZIP path traversal protection
- 50 MB upload limit, 200 MB extracted content limit
- Temporary job directory cleanup after download

## Deploy on Render
1. Upload this project to a GitHub repository.
2. In Render, choose **New + → Blueprint** and select the repository.
3. Render reads `render.yaml`, builds the Docker image, and deploys the service.
4. Open the generated `onrender.com` URL.

You can also create a **Web Service** manually, select the repository, choose **Docker** as the runtime, and deploy.

## Local run
Requires Docker:
```bash
docker build -t sojib-smali .
docker run --rm -p 10000:10000 sojib-smali
```
Open `http://localhost:10000`.

## Limits and notes
- Upload request maximum: 50 MB.
- Maximum extracted Smali content: 200 MB.
- Maximum Smali files per job: 10,000.
- One conversion runs at a time per worker; the Render service uses one Gunicorn worker.
- Free hosting may sleep when idle and may have limited CPU/RAM.
- Uploaded files are processed temporarily and removed after the download response closes. Do not upload private or sensitive files.
- This tool assembles Smali source into a DEX file. It does not decode APK files or convert arbitrary Java source code.
- Use only files you own or are authorized to modify.

## Engine
Smali 3.0.10 fat JAR from the `baksmali/smali` release repository. The Docker build checks the published SHA-256 checksum before installing it.
