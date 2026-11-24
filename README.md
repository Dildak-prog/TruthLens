---
title: TruthLens AI Detector
emoji: 🔎
colorFrom: blue
colorTo: purple
sdk: gradio
app_file: app.py
pinned: false
models:
  - abacusai/Smaug-AI-Image-Detector
---

# TruthLens

Free-tier Gradio + ZeroGPU deployment of the open-source Smaug AI image detector.
The Android client calls `POST /analyze` with multipart field `file`.

The first inference downloads the model and may take a while. ZeroGPU has daily
usage quotas; availability and speed depend on Hugging Face's free-tier limits.
Scores are probabilistic and must not be treated as proof.
