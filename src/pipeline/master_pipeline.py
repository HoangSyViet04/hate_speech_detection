
import os
import re
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent


def load_module_from_path(mod_name: str, file_path: Path):
    """
    Load a module from a given file path and return the loaded module object.
    """
    try:
        spec = importlib.util.spec_from_file_location(mod_name, str(file_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        return None
    return None


def robust_import(module_candidates: List[str], filename: str, attr: str = None):
    """
    Try importing module by names in module_candidates (order matters).
    If import fails, try to load from local filename (relative to BASE_DIR).
    If attr provided, return getattr(module, attr), else return module.
    """
    for name in module_candidates:
        try:
            mod = importlib.import_module(name)
            return getattr(mod, attr) if attr else mod
        except Exception:
            continue

    # Thử load từ file local
    local_path = BASE_DIR / filename
    if local_path.exists():
        mod = load_module_from_path(module_candidates[-1], local_path)
        if mod:
            return getattr(mod, attr) if attr and hasattr(mod, attr) else (getattr(mod, attr) if attr else mod)

    return None

# Step 1: Unicode normalizer (class with process)
UnicodeNormalizer = robust_import(
    ["src.pipeline.step1_unicode_normalizer", "step1_unicode_normalizer"],
    "step1_unicode_normalizer.py",
    "process"
)

# Step 2: Placeholder process function
placeholder_process = robust_import(
    ["src.pipeline.step2_placeholder_handler", "step2_placeholder_handler"],
    "step2_placeholder_handler.py",
    "process"
)

# Step 3: Evasion handler (class)
EvasionHandler = robust_import(
    ["src.pipeline.step3_evasion_handler", "step3_evasion_handler"],
    "step3_evasion_handler.py",
    "EvasionHandler"
)

# Step 4: Elongation process function
elongation_process = robust_import(
    ["src.pipeline.step4_elongation_handler", "step4_elongation_handler"],
    "step4_elongation_handler.py",
    "process"
)

# Step 5: Emoji process function
emoji_process = robust_import(
    ["src.pipeline.step5_emoji_handler", "step5_emoji_handler"],
    "step5_emoji_handler.py",
    "process"
)

# Step 6: Teencode process function
teencode_process = robust_import(
    ["src.pipeline.step6_teencode_handler", "step6_teencode_handler"],
    "step6_teencode_handler.py",
    "process"
)

# Step 7: Negation process function
negation_process = robust_import(
    ["src.pipeline.step7_negation_handler", "step7_negation_handler"],
    "step7_negation_handler.py",
    "process"
)

# Step 8: Word segmenter class (has process)
WordSegmenter = robust_import(
    ["src.pipeline.step8_word_segmenter", "step8_word_segmenter"],
    "step8_word_segmenter.py",
    "WordSegmenter"
)

# -------------------- Config mặc định (dict, dễ chỉnh) --------------------
def default_config(dict_dir: str = "data/dictionaries") -> Dict[str, Any]:
    return {
        "dict_dir": dict_dir,
        "teencode_path": os.path.join(dict_dir, "teencode_map.yaml"),
        "emoticon_path": os.path.join(dict_dir, "emoticon_map.yaml"),
        "profanity_path": os.path.join(dict_dir, "profanity_words.yaml"),
        "leetspeak_path": os.path.join(dict_dir, "leetspeak_map.yaml"),
        "enable_leetspeak": False,
        "max_repeat": 2,
        "negation_window": 4,
        "segmenter_tool": "pyvi",
        "extract_features": True,
        "lowercase": True,
    }

# --------------------  (khởi tạo các instance cần thiết) --------------------
def init_pipeline_handlers(cfg: Dict[str, Any]) -> Dict[str, Any]:
    handlers: Dict[str, Any] = {}

    # Unicode normalizer (class)
    if UnicodeNormalizer:
        try:
            handlers["unicode"] = UnicodeNormalizer()
        except Exception:
            handlers["unicode"] = None
    else:
        handlers["unicode"] = None

    handlers["placeholder"] = placeholder_process
    
    # Evasion Handler (class)
    if EvasionHandler:
        try:
            handlers["evasion"] = EvasionHandler(dictionary_path=cfg.get("profanity_path"))
        except Exception:
            handlers["evasion"] = None
    else:
        handlers["evasion"] = None

    handlers["elongation"] = elongation_process
    handlers["emoji"] = emoji_process
    handlers["teencode"] = teencode_process
    handlers["negation"] = negation_process
    
    # Word Segmenter (class)
    if WordSegmenter:
        try:
            handlers["segmenter"] = WordSegmenter(tool=cfg.get("segmenter_tool", "pyvi"))
        except Exception:
            handlers["segmenter"] = None
    else:
        handlers["segmenter"] = None
        
    return handlers

# -------------------- Process single text --------------------
def process_text(text: str, handlers: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    original = text
    metadata: Dict[str, Any] = {}
    features: Dict[str, Any] = {}

    # Step 1: Unicode
    if handlers.get("unicode"):
        try:
            text, meta = handlers["unicode"].process(text)
        except Exception:
            meta = {"error": "unicode_failed"}
    else:
        meta = {"skipped": True}
    metadata["step1_unicode"] = meta

    # Step 2: Placeholder
    if handlers.get("placeholder"):
        try:
            text, meta = handlers["placeholder"](text)
        except Exception:
            text, meta = text, {"error": "placeholder_failed"}
    else:
        text, meta = text, {"skipped": True}
    metadata["step2_placeholder"] = meta

    # Step 3: Evasion
    if handlers.get("evasion"):
        try:
            text, meta = handlers["evasion"].process(text)
        except Exception:
            text, meta = text, {"error": "evasion_failed"}
    else:
        text, meta = text, {"skipped": True}
    metadata["step3_evasion"] = meta

    # Step 4: Elongation
    if handlers.get("elongation"):
        try:
            text, meta = handlers["elongation"](text, max_repeat=cfg.get("max_repeat", 2), extract_features=cfg.get("extract_features", True))
        except Exception:
            text, meta = text, {"error": "elongation_failed"}
    else:
        text, meta = text, {"skipped": True}
    metadata["step4_elongation"] = meta
    if isinstance(meta, dict):
        features.update(meta.get("intensity_features", {}))

    # Step 5: Emoji
    if handlers.get("emoji"):
        try:
            text, meta = handlers["emoji"](text, emoticon_map_path=cfg.get("emoticon_path"))
        except Exception:
            text, meta = text, {"error": "emoji_failed"}
    else:
        text, meta = text, {"skipped": True}
    metadata["step5_emoji"] = meta
    if isinstance(meta, dict):
        features.update(meta.get("emoji_features", {}))

    # Step 6: Teencode
    if handlers.get("teencode"):
        try:
            text, meta = handlers["teencode"](text, teencode_path=cfg.get("teencode_path"))
        except Exception:
            text, meta = text, {"error": "teencode_failed"}
    else:
        text, meta = text, {"skipped": True}
    metadata["step6_teencode"] = meta

    # Step 7: Negation
    if handlers.get("negation"):
        try:
            text, meta = handlers["negation"](text, window_size=cfg.get("negation_window", 4))
        except Exception:
            text, meta = text, {"error": "negation_failed"}
    else:
        text, meta = text, {"skipped": True}
    metadata["step7_negation"] = meta
    if isinstance(meta, dict):
        features["negation_count"] = meta.get("negation_count", 0)

    # Step 8: Word Segmentation
    if handlers.get("segmenter"):
        try:
            text, meta = handlers["segmenter"].process(text)
        except Exception:
            text, meta = text, {"error": "segmenter_failed"}
    else:
        meta = {"skipped": True}
    metadata["step8_segmenter"] = meta
    if isinstance(meta, dict):
        features["compound_count"] = meta.get("compound_count", 0)

    return {"original": original, "cleaned": text, "features": features, "metadata": metadata}

# -------------------- Batch helper --------------------
def process_batch(texts: List[str], handlers: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [process_text(t, handlers, cfg) for t in texts]

# -------------------- Quick test --------------------
if __name__ == "__main__":
    cfg = default_config()
    handlers = init_pipeline_handlers(cfg)

    tests = [
        "xin chào",
        "đm thg này ngu vl",
        "g.iế.t người đi",
        "nguuuuuu quááááá!! !",
        "@user123 mày xem https://abc.com đi",
        "tao không thích mày",
        "thằng này t. ox. ic thật",
    ]
    print("MASTER PIPELINE - TEST (DANH SÁCH CÂU)")


    results = process_batch(tests, handlers, cfg)
    for r in results:
        print("\n---")
        print("Input: ", r["original"])
        print("Output:", r["cleaned"])

