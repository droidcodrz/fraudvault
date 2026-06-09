import io
from dataclasses import dataclass
from pathlib import Path

import structlog
import torch
from PIL import Image

logger = structlog.get_logger()

MODEL_NAMES = [
    "Organika/sdxl-detector",
    "umm-maybe/AI-image-detector",
    "dima806/ai_vs_human_generated_image_detection",
]

AI_LABEL_KEYWORDS = (
    "fake",
    "artificial",
    "ai",
    "generated",
    "synthetic",
    "deepfake",
    "not_real",
    "not real",
)


@dataclass
class AIModelBundle:
    model_name: str
    model: object
    processor: object
    ai_class_index: int


def _find_ai_class_index(id2label: dict) -> int:
    for idx, label in id2label.items():
        label_lower = str(label).lower().replace(" ", "_")
        if any(kw in label_lower for kw in AI_LABEL_KEYWORDS):
            return int(idx)
    if len(id2label) == 2:
        for idx, label in id2label.items():
            if str(label).lower() not in ("real", "human", "authentic", "natural", "photo"):
                return int(idx)
        return 1
    return max(int(k) for k in id2label.keys())


def load_models(cache_dir: str) -> list[AIModelBundle]:
    """Load all available AI detection models into an ensemble."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    loaded: list[AIModelBundle] = []

    try:
        from transformers import AutoModelForImageClassification, AutoImageProcessor
    except ImportError:
        logger.warning("transformers_not_installed", msg="AI detection disabled")
        return loaded

    for model_name in MODEL_NAMES:
        try:
            processor = AutoImageProcessor.from_pretrained(model_name, cache_dir=str(cache_path))
            model = AutoModelForImageClassification.from_pretrained(model_name, cache_dir=str(cache_path))
            model.eval()
            id2label = getattr(model.config, "id2label", {0: "real", 1: "fake"})
            ai_index = _find_ai_class_index(id2label)
            loaded.append(AIModelBundle(model_name, model, processor, ai_index))
            logger.info("ai_model_loaded", model=model_name, ai_class_index=ai_index)
        except Exception as exc:
            logger.warning("ai_model_load_failed", model=model_name, error=str(exc))

    if not loaded:
        logger.warning("no_ai_models_loaded", msg="AI detection disabled — download models on first run")

    return loaded


def load_model(cache_dir: str) -> list[AIModelBundle]:
    """Backward-compatible alias for load_models."""
    return load_models(cache_dir)


def _run_single_model(bundle: AIModelBundle, image: Image.Image) -> float:
    inputs = bundle.processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = bundle.model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        idx = bundle.ai_class_index
        if probs.shape[1] > idx:
            return float(probs[0][idx].item())
        return float(probs[0].max().item())


def analyse(file_bytes: bytes, ai_models: list[AIModelBundle] | None = None) -> dict:
    """Run AI-generated image detection using model ensemble (max score)."""
    if not ai_models:
        return {
            "ai_gen_score": 0.0,
            "model_used": None,
            "model_scores": {},
            "model_unavailable": True,
        }

    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        model_scores: dict[str, float] = {}

        for bundle in ai_models:
            try:
                score = _run_single_model(bundle, image)
                model_scores[bundle.model_name] = score
            except Exception as exc:
                logger.warning("ai_inference_failed", model=bundle.model_name, error=str(exc))

        if not model_scores:
            return {
                "ai_gen_score": 0.0,
                "model_used": None,
                "model_scores": {},
                "model_unavailable": True,
            }

        ai_gen_score = max(model_scores.values())
        model_used = "ensemble:" + ",".join(model_scores.keys())

        return {
            "ai_gen_score": ai_gen_score,
            "model_used": model_used,
            "model_scores": model_scores,
            "model_unavailable": False,
        }
    except Exception as exc:
        logger.warning("ai_analyse_failed", error=str(exc))
        return {
            "ai_gen_score": 0.0,
            "model_used": None,
            "model_scores": {},
            "model_unavailable": True,
        }
