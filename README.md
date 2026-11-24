---
title: TruthLens API
emoji: 🔎
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# TruthLens API

FastAPI backend for the TruthLens Android app. Runs the open-source
`abacusai/Smaug-AI-Image-Detector` model locally in the Space container.
No Hugging Face Inference Providers token or paid inference credits are used.

The first startup downloads approximately 0.9 GB of model files and can take
several minutes. On free CPU hardware inference may be slow, and free Spaces
can sleep when inactive. The model is loaded at startup; check `/health`.

## API
- `GET /health`
- `POST /analyze` with multipart field `file`

The model returns an AI-generated probability in [0, 1]. The response also
includes basic mathematical image statistics. Scores are probabilistic, not proof.

## Hardware
CPU Basic may work but startup time and inference speed depend on the free
hardware currently allocated by Hugging Face. No paid hardware is requested.
