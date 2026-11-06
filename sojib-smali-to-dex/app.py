import os
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path, PurePosixPath
from flask import Flask, render_template, request, send_file, after_this_request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit

SMALI_JAR = os.environ.get("SMALI_JAR", "/opt/smali/smali.jar")
MAX_FILES = 10000
MAX_UNZIPPED = 200 * 1024 * 1024
PROCESS_TIMEOUT = 120

@app.get("/")
def home():
    return render_template("index.html")

def safe_extract_smali_zip(zip_path: Path, destination: Path):
    total = 0
    count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = item.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("ZIP-এর মধ্যে নিরাপদ নয় এমন file path পাওয়া গেছে।")
            if not name.lower().endswith(".smali"):
                continue
            if item.file_size > MAX_UNZIPPED:
                raise ValueError("একটি ফাইলের আকার অনুমোদিত সীমার বেশি।")
            total += item.file_size
            count += 1
            if total > MAX_UNZIPPED:
                raise ValueError("ZIP extract করার মোট আকার ২০০ MB-এর বেশি।")
            if count > MAX_FILES:
                raise ValueError("ZIP-এ ১০,০০০টির বেশি Smali ফাইল রয়েছে।")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    return count

def save_uploaded_smali(uploaded_files, destination: Path):
    count = 0
    total = 0
    for uploaded in uploaded_files:
        if not uploaded or not uploaded.filename:
            continue
        # Browser folder upload sends relative paths in filename.
        raw_name = uploaded.filename.replace("\\", "/")
        path = PurePosixPath(raw_name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Upload-এ অনিরাপদ file path পাওয়া গেছে।")
        if not raw_name.lower().endswith(".smali"):
            continue
        data = uploaded.read(MAX_UNZIPPED + 1)
        total += len(data)
        count += 1
        if len(data) > MAX_UNZIPPED or total > MAX_UNZIPPED:
            raise ValueError("Smali ফাইলগুলোর মোট আকার ২০০ MB-এর বেশি।")
        if count > MAX_FILES:
            raise ValueError("১০,০০০টির বেশি Smali ফাইল আপলোড করা যাবে না।")
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return count

@app.post("/convert")
def convert():
    work = Path(tempfile.mkdtemp(prefix="smali_job_"))
    smali_dir = work / "input"
    smali_dir.mkdir()
    dex_file = work / "classes.dex"

    try:
        zip_upload = request.files.get("zip_file")
        uploaded_files = request.files.getlist("files")
        has_zip = bool(zip_upload and zip_upload.filename)
        has_files = any(f and f.filename for f in uploaded_files)

        if has_zip and has_files:
            raise ValueError("একবারে ZIP অথবা Smali ফাইল/Folder—একটি পদ্ধতি ব্যবহার করুন।")
        if has_zip:
            if not zip_upload.filename.lower().endswith(".zip"):
                raise ValueError("শুধু .zip ফাইল আপলোড করুন।")
            zip_path = work / "upload.zip"
            zip_upload.save(zip_path)
            count = safe_extract_smali_zip(zip_path, smali_dir)
        elif has_files:
            count = save_uploaded_smali(uploaded_files, smali_dir)
        else:
            raise ValueError("প্রথমে একটি ZIP অথবা Smali ফাইল/Folder নির্বাচন করুন।")

        if count == 0:
            raise ValueError("কোনো .smali ফাইল পাওয়া যায়নি।")

        result = subprocess.run(
            ["java", "-jar", SMALI_JAR, "assemble", str(smali_dir), "-o", str(dex_file)],
            capture_output=True, text=True, timeout=PROCESS_TIMEOUT, check=False
        )
        if result.returncode != 0 or not dex_file.exists():
            details = (result.stderr or result.stdout or "Unknown assembler error").strip()
            raise ValueError("Conversion ব্যর্থ হয়েছে:\n" + details[-5000:])

        if dex_file.stat().st_size == 0:
            raise ValueError("তৈরি হওয়া DEX ফাইলটি খালি।")

        response = send_file(
            dex_file, as_attachment=True, download_name="classes.dex",
            mimetype="application/octet-stream"
        )
        response.call_on_close(lambda: shutil.rmtree(work, ignore_errors=True))
        return response

    except subprocess.TimeoutExpired:
        shutil.rmtree(work, ignore_errors=True)
        return render_template("index.html", error="Conversion সময়সীমা (২ মিনিট) অতিক্রম করেছে। ফাইল ছোট করে আবার চেষ্টা করুন।"), 408
    except (ValueError, zipfile.BadZipFile, OSError) as exc:
        shutil.rmtree(work, ignore_errors=True)
        return render_template("index.html", error=str(exc)), 400
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        app.logger.exception("Unexpected conversion error")
        return render_template("index.html", error="সার্ভারে সমস্যা হয়েছে। ফাইল পরীক্ষা করে আবার চেষ্টা করুন।"), 500

@app.errorhandler(413)
def too_large(_error):
    return render_template("index.html", error="Upload limit ৫০ MB। ছোট ফাইল ব্যবহার করুন।"), 413

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
