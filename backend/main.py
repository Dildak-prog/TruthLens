import io
import os
import requests
from PIL import Image, ImageStat
from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="TruthLens API", version="1.0.0")
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL_ID = os.getenv("HF_MODEL_ID", "")

@app.get("/health")
def health():
    return {"status": "ok", "model_configured": bool(HF_TOKEN and HF_MODEL_ID)}

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

    if not HF_TOKEN or not HF_MODEL_ID:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "model": "not-configured",
            "message": "A model and Hugging Face token must be configured on the server.",
            "math_features": math_features,
        }

    url = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL_ID}"
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "image/jpeg"},
            data=raw,
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Model provider error: {exc}")
    except ValueError:
        raise HTTPException(status_code=502, detail="Model returned an unreadable response.")

    if not isinstance(payload, list) or not payload:
        raise HTTPException(status_code=502, detail=f"Unexpected model response: {payload}")
    best = max(payload, key=lambda item: float(item.get("score", 0)))
    label = str(best.get("label", "")).lower()
    score = float(best.get("score", 0))
    if any(word in label for word in ("artificial", "generated", "ai", "fake", "synthetic")):
        verdict = "ai"
    elif any(word in label for word in ("real", "human", "photo", "authentic")):
        verdict = "real"
    else:
        verdict = "unknown"
    return {
        "verdict": verdict,
        "confidence": score,
        "model": HF_MODEL_ID,
        "top_label": best.get("label"),
        "math_features": math_features,
        "warning": "Model scores are probabilistic and depend on the model's training data.",
    }
