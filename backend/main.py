import io
import os
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, ImageStat
from huggingface_hub import snapshot_download

app = FastAPI(title="TruthLens API", version="2.0.0")
MODEL_ID = os.getenv("HF_MODEL_ID", "abacusai/Smaug-AI-Image-Detector")
detector = None
model_error = None


@app.on_event("startup")
def load_model():
    global detector, model_error
    try:
        model_path = snapshot_download(MODEL_ID)
        sys.path.insert(0, model_path)
        from smaug_image_detect import SmaugImageDetect
        detector = SmaugImageDetect.from_pretrained(model_path)
        model_error = None
    except Exception as exc:
        model_error = f"{type(exc).__name__}: {exc}"
        print(f"TruthLens model load failed: {model_error}", flush=True)


@app.get("/")
def root():
    return {"service": "TruthLens API", "model": MODEL_ID}


@app.get("/health")
def health():
    return {
        "status": "ok" if detector is not None else "starting_or_model_error",
        "model": MODEL_ID,
        "model_loaded": detector is not None,
        "error": model_error,
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if detector is None:
        raise HTTPException(status_code=503, detail="AI model is not ready. Check /health.")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload an image file.")
    raw = await file.read()
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is larger than 12 MB.")
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image.")

    stats = ImageStat.Stat(image.resize((128, 128)))
    math_features = {
        "mean_rgb": [round(x, 2) for x in stats.mean],
        "stddev_rgb": [round(x, 2) for x in stats.stddev],
        "width": image.width,
        "height": image.height,
    }

    suffix = ".jpg"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name
            image.save(temp_path, format="JPEG", quality=95)
        score = float(detector(temp_path))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {type(exc).__name__}: {exc}")
    finally:
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    score = max(0.0, min(1.0, score))
    verdict = "ai" if score >= 0.5 else "real"
    confidence = score if verdict == "ai" else 1.0 - score
    return {
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "ai_probability": round(score, 4),
        "model": MODEL_ID,
        "math_features": math_features,
        "warning": "Probabilistic estimate, not proof. Detector accuracy depends on image source and editing.",
    }
