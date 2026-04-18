"""
ViHateGuard - FastAPI Backend
Hỗ trợ 2 model:
  1. Bi-LSTM (load 1 lần khi startup)
  2. Qwen2.5 qua Ollama (gọi HTTP tới Ollama server)
Frontend/Telegram Bot chọn model qua tham số "model".
"""

import os
import sys
import json
import torch
import httpx
import numpy as np
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional

# ---- Cấu hình đường dẫn ----
BASE_DIR = Path(__file__).resolve().parent.parent  # project root

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline import master_pipeline
from src.models.bilstm_model import BiLSTMClassifier

# ---- Cấu hình model ----
MODEL_PATH = BASE_DIR / "models_best" / "best_model.pth"
VOCAB_PATH = BASE_DIR / "models_best" / "bilstm_best_vocab.json"
DICT_DIR = BASE_DIR / "data" / "dictionaries"

EMBEDDING_DIM = 512
HIDDEN_DIM = 256
MAX_LEN = 220
THRESHOLD_HATE = 0.65
THRESHOLD_OFFENSIVE = 0.60
CLASSES = {0: "CLEAN", 1: "OFFENSIVE", 2: "HATE"}
LABELS_VI = {0: "Sạch", 1: "Thô lỗ", 2: "Thù ghét"}

# ---- Ollama config ----
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")

AVAILABLE_MODELS = ["bilstm", "qwen2.5"]

# ---- Global resources (load 1 lần) ----
_resources: dict = {}
_ollama_client: httpx.AsyncClient = None


def _load_resources():
    """Load BiLSTM model, vocab, pipeline handlers một lần."""
    # Vocab
    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)

    # Device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Model
    model = BiLSTMClassifier(len(vocab), EMBEDDING_DIM, HIDDEN_DIM, 3)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device(device)))
    model.to(device)
    model.eval()

    # Pipeline
    pipeline_cfg = master_pipeline.default_config(dict_dir=str(DICT_DIR))
    handlers = master_pipeline.init_pipeline_handlers(pipeline_cfg)

    _resources.update({
        "model": model,
        "vocab": vocab,
        "device": device,
        "handlers": handlers,
        "pipeline_cfg": pipeline_cfg,
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load resources khi startup, giải phóng khi shutdown."""
    global _ollama_client
    _load_resources()
    _ollama_client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=120.0)
    print(f"[ViHateGuard] BiLSTM loaded on {_resources['device']}  |  Vocab size: {len(_resources['vocab'])}")
    print(f"[ViHateGuard] Ollama endpoint: {OLLAMA_BASE_URL}  |  Model: {OLLAMA_MODEL}")
    yield
    await _ollama_client.aclose()
    _resources.clear()


# ---- FastAPI App ----
app = FastAPI(
    title="ViHateGuard API",
    description="API phát hiện ngôn từ thù ghét tiếng Việt (BiLSTM + Qwen2.5)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---- Schema ----
class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Văn bản cần phân tích")
    model: Optional[str] = Field("bilstm", description="Model: bilstm hoặc qwen2.5")


class PredictResponse(BaseModel):
    label: str
    label_vi: str
    confidence: float
    probabilities: dict
    cleaned_text: str
    model_used: str


# ==================== BiLSTM ====================
def _bilstm_predict(text: str) -> dict:
    model = _resources["model"]
    vocab = _resources["vocab"]
    device = _resources["device"]
    handlers = _resources["handlers"]
    cfg = _resources["pipeline_cfg"]

    # 1. Pipeline
    result = master_pipeline.process_text(text, handlers, cfg)
    cleaned_text = result["cleaned"]

    # 2. Encode
    words = cleaned_text.split()
    indices = [vocab.get(w, 1) for w in words]  # 1 = <UNK>
    if len(indices) < MAX_LEN:
        indices += [0] * (MAX_LEN - len(indices))
    else:
        indices = indices[:MAX_LEN]

    tensor_input = torch.tensor([indices], dtype=torch.long).to(device)

    # 3. Inference
    with torch.no_grad():
        logits = model(tensor_input)
        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

    # 4. Threshold moving
    prob_clean, prob_offensive, prob_hate = float(probs[0]), float(probs[1]), float(probs[2])

    if prob_hate > THRESHOLD_HATE:
        pred_idx = 2
    elif prob_offensive > THRESHOLD_OFFENSIVE:
        pred_idx = 1
    else:
        if prob_hate > prob_offensive and prob_hate > prob_clean:
            pred_idx = 2
        elif prob_offensive > prob_clean:
            pred_idx = 1
        else:
            pred_idx = 0

    return {
        "label": CLASSES[pred_idx],
        "label_vi": LABELS_VI[pred_idx],
        "confidence": float(probs[pred_idx]),
        "probabilities": {
            "clean": prob_clean,
            "offensive": prob_offensive,
            "hate": prob_hate,
        },
        "cleaned_text": cleaned_text,
        "model_used": "bilstm",
    }


# ==================== Qwen2.5 (Ollama) ====================
QWEN_SYSTEM_PROMPT = """Bạn là hệ thống phân loại ngôn từ thù ghét tiếng Việt. 
Phân loại bình luận vào ĐÚNG 1 trong 3 nhãn: CLEAN, OFFENSIVE, HATE.

Định nghĩa:
- CLEAN: Bình luận bình thường, không xúc phạm.
- OFFENSIVE: Có ngôn từ thô tục, xúc phạm nhẹ nhưng không nhắm vào nhóm người cụ thể.
- HATE: Ngôn từ thù ghét, kích động bạo lực, phân biệt đối xử nhắm vào cá nhân hoặc nhóm người.

Trả lời CHÍNH XÁC theo format JSON (không markdown, không giải thích):
{"label": "CLEAN hoặc OFFENSIVE hoặc HATE", "confidence": 0.0-1.0, "probabilities": {"clean": 0.0-1.0, "offensive": 0.0-1.0, "hate": 0.0-1.0}}"""


async def _qwen_predict(text: str) -> dict:
    """Gọi Ollama Qwen2.5 để phân loại."""
    handlers = _resources["handlers"]
    cfg = _resources["pipeline_cfg"]

    # Chạy pipeline trước để frontend thấy cleaned_text
    result = master_pipeline.process_text(text, handlers, cfg)
    cleaned_text = result["cleaned"]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": QWEN_SYSTEM_PROMPT},
            {"role": "user", "content": f"Phân loại bình luận sau:\n\"{text}\""},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }

    try:
        resp = await _ollama_client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["message"]["content"]
        parsed = json.loads(content)

        label = parsed.get("label", "CLEAN").upper().strip()
        if label not in CLASSES.values():
            label = "CLEAN"

        label_idx = {v: k for k, v in CLASSES.items()}.get(label, 0)
        confidence = float(parsed.get("confidence", 0.5))

        probs = parsed.get("probabilities", {})
        prob_clean = float(probs.get("clean", 1.0 if label == "CLEAN" else 0.0))
        prob_offensive = float(probs.get("offensive", 1.0 if label == "OFFENSIVE" else 0.0))
        prob_hate = float(probs.get("hate", 1.0 if label == "HATE" else 0.0))

        return {
            "label": label,
            "label_vi": LABELS_VI[label_idx],
            "confidence": confidence,
            "probabilities": {
                "clean": prob_clean,
                "offensive": prob_offensive,
                "hate": prob_hate,
            },
            "cleaned_text": cleaned_text,
            "model_used": "qwen2.5",
        }
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Không thể kết nối tới Ollama. Hãy chắc chắn Ollama đang chạy (ollama serve) và đã pull model qwen2.5.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Qwen2.5: {e}")


# ---- Endpoints ----
@app.get("/")
async def root():
    """Serve frontend HTML."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "ViHateGuard API is running. POST /predict to classify text."}


@app.get("/health")
async def health():
    """Kiểm tra trạng thái API và các model."""
    ollama_ok = False
    try:
        resp = await _ollama_client.get("/api/tags")
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            ollama_ok = any(OLLAMA_MODEL in m for m in models)
    except Exception:
        pass

    return {
        "status": "ok",
        "device": _resources.get("device", "unknown"),
        "models": {
            "bilstm": True,
            "qwen2.5": ollama_ok,
        },
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    """Phân loại bình luận: CLEAN / OFFENSIVE / HATE."""
    model_name = (req.model or "bilstm").lower().strip()

    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"Model không hợp lệ. Chọn: {AVAILABLE_MODELS}")

    try:
        if model_name == "qwen2.5":
            result = await _qwen_predict(req.text)
        else:
            result = _bilstm_predict(req.text)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Run ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.api:app", host="0.0.0.0", port=8000, reload=False)
