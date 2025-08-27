from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import requests
import hashlib
import time
from typing import List, Optional
import os
from dotenv import load_dotenv
load_dotenv()
from backend.generator import generate_test_cases, extract_text_from_files 

app = FastAPI()
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Allow frontend (React/HTML/any)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⚠️ Replace with your real secret key from hCaptcha Dashboard
HCAPTCHA_SECRET = os.getenv("HCAPTCHA_SECRET_KEY")


def verify_hcaptcha(token: str) -> bool:
    """
    Verify hCaptcha token with hCaptcha servers.
    """
    url = "https://hcaptcha.com/siteverify"
    data = {"secret": HCAPTCHA_SECRET, "response": token}
    try:
        resp = requests.post(url, data=data)
        result = resp.json()
        return result.get("success", False)
    except Exception as e:
        print("hCaptcha verification error:", e)
        return False

FRONTEND_DIR = "frontend"

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse("frontend/index.html")
    # return "Hello, World!"

@app.get("/input.html", include_in_schema=False)
async def serve_input():
    return FileResponse(f"{FRONTEND_DIR}/input.html")

@app.get("/cases.html", include_in_schema=False)
async def serve_cases():
    return FileResponse(f"{FRONTEND_DIR}/cases.html")

@app.get("/data.html", include_in_schema=False)
async def serve_data():
    return FileResponse(f"{FRONTEND_DIR}/data.html")

@app.post("/process")
async def process_request(
    hcaptcha_token: str = Form(..., alias="h-captcha-response"),
    input_text: Optional[str] = Form(""),
    files: Optional[List[UploadFile]] = File(None)
):
    # 1. Verify hCaptcha
    if not verify_hcaptcha(hcaptcha_token):
        # return {"error": "❌ Captcha verification failed"}
        return FileResponse(f"{FRONTEND_DIR}/input.html")

    # 2. Process uploaded files (optional)
    file_hashes = []
    file_objects = []
    if files:
        for f in files:
            content = await f.read()
            file_hashes.append({"filename": f.filename, "md5": hashlib.md5(content).hexdigest()})
            f.file.seek(0)  # reset pointer for reuse
            file_objects.append(f)  # pass UploadFile, not f.file

    # 3. Call your generator
    result = generate_test_cases(input_text=input_text, uploaded_files=file_objects)
    print(result)
    # 4. Return result
    return {
        "status": "✅ success",
        "captcha": "verified",
        "file_hashes": file_hashes,
        "output": result,
        "timestamp": time.time()
    }
