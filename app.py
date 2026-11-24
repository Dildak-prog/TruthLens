import base64
import io
import os
import sys
import tempfile

import gradio as gr
import spaces
from fastapi import File, HTTPException, UploadFile
from PIL import Image, ImageStat
from huggingface_hub import snapshot_download

MODEL_ID = "abacusai/Smaug-AI-Image-Detector"
_detector = None


def get_detector():
    global _detector
    if _detector is None:
        model_path = snapshot_download(MODEL_ID)
        sys.path.insert(0, model_path)
        from smaug_image_detect import SmaugImageDetect
        _detector = SmaugImageDetect.from_pretrained(model_path)
    return _detector


@spaces.GPU
def score_image(image_path: str) -> float:
    detector = get_detector()
    return float(detector(image_path))


app = gr.Server()


@app.get("/")
def root():
    return {
        "service": "TruthLens API",
        "model": MODEL_ID,
        "health": "/health",
        "analyze": "/analyze",
    }


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "model_loaded": _detector is not None}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
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

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temp_path = tmp.name
            image.save(temp_path, format="JPEG", quality=95)
        ai_probability = max(0.0, min(1.0, score_image(temp_path)))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {type(exc).__name__}: {exc}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    verdict = "ai" if ai_probability >= 0.5 else "real"
    confidence = ai_probability if verdict == "ai" else 1.0 - ai_probability
    return {
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "ai_probability": round(ai_probability, 4),
        "model": MODEL_ID,
        "math_features": math_features,
        "warning": "Probabilistic estimate, not proof. Detectors can make mistakes.",
    }


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)
