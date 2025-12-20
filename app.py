import streamlit as st
import torch
import torch.nn as nn
import json
import numpy as np
import pandas as pd
import os
import sys

# --- 1. CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Thêm BASE_DIR vào sys.path để Python nhìn thấy gói 'src'
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Import master_pipeline từ src/pipeline
try:
    # Cách import chuẩn khi BASE_DIR đã ở trong sys.path
    from src.pipeline import master_pipeline
except ImportError as e:
    st.error(f"Lỗi Import Pipeline: {e}")
    st.info(f"Đang tìm kiếm tại: {BASE_DIR}")
    st.stop()

# Đường dẫn tài nguyên model và vocab
MODEL_PATH = os.path.join(BASE_DIR, 'models_best', 'best_model.pth')
VOCAB_PATH = os.path.join(BASE_DIR, 'models_best', 'bilstm_best_vocab.json')
DICT_DIR = os.path.join(BASE_DIR, 'data', 'dictionaries')

# Cấu hình Model
EMBEDDING_DIM = 512
HIDDEN_DIM = 256
MAX_LEN = 220
CLASSES = {0: "CLEAN (Sạch)", 1: "OFFENSIVE (Thô lỗ)", 2: "HATE (Thù ghét)"}

# --- 2. ĐỊNH NGHĨA MODEL ---
try:
    from src.models.bilstm_model import BiLSTMClassifier
except ImportError as e:
    st.error(f"Lỗi Import Model Class: {e}")
    st.stop()

# --- 3. HÀM MÃ HÓA VĂN BẢN (SỬ DỤNG MASTER PIPELINE) ---
def encode_text_with_pipeline(text, vocab, max_len, handlers, cfg):
    """
    Xử lý văn bản qua Pipeline chuẩn -> Map sang index -> Padding
    """
    # 1. Chạy qua Pipeline (Chuẩn hóa, Evasion, Teencode, Tách từ...)
    # master_pipeline.process_text trả về dict chứa text sạch và metadata
    result = master_pipeline.process_text(text, handlers, cfg)
    cleaned_text = result["cleaned"]
    
    # 2. Map từ sang số (Vocabulary Mapping)
    words = cleaned_text.split()
    indices = [vocab.get(w, 1) for w in words] # 1 là <UNK>
    
    # 3. Padding
    if len(indices) < max_len:
        indices += [0] * (max_len - len(indices))
    else:
        indices = indices[:max_len]
        
    return torch.tensor([indices], dtype=torch.long), cleaned_text, result["metadata"]

# --- 4. LOAD RESOURCE (CACHE ĐỂ CHẠY NHANH) ---
@st.cache_resource
def load_resources():
    resources = {}
    
    # A. Load Model & Vocab
    try:
        if not os.path.exists(VOCAB_PATH):
            st.error(f"Không tìm thấy file từ điển tại: {VOCAB_PATH}")
            return None
            
        with open(VOCAB_PATH, 'r', encoding='utf-8') as f:
            vocab = json.load(f)
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if not os.path.exists(MODEL_PATH):
            st.error(f"Không tìm thấy file model tại: {MODEL_PATH}")
            return None

        model = BiLSTMClassifier(len(vocab), EMBEDDING_DIM, HIDDEN_DIM, 3)
        model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device(device)))
        model.to(device)
        model.eval()
        
        resources["model"] = model
        resources["vocab"] = vocab
        resources["device"] = device
    except Exception as e:
        st.error(f"Lỗi load Model/Vocab: {e}")
        return None

    # B. Load Pipeline Handlers
    try:
        # Kiểm tra thư mục từ điển
        if not os.path.exists(DICT_DIR):
             st.warning(f"Cảnh báo: Không tìm thấy thư mục từ điển tại '{DICT_DIR}'. Pipeline sẽ chạy với cấu hình mặc định.")
        
        # Tạo config cho pipeline trỏ vào thư mục dictionaries
        pipeline_cfg = master_pipeline.default_config(dict_dir=DICT_DIR)
        
        # Khởi tạo các module xử lý (load từ điển teencode, emoji,...)
        handlers = master_pipeline.init_pipeline_handlers(pipeline_cfg)
        
        resources["handlers"] = handlers
        resources["pipeline_cfg"] = pipeline_cfg
    except Exception as e:
        st.error(f"Lỗi khởi tạo Pipeline: {e}")
        return None
        
    return resources

# --- 5. GIAO DIỆN CHÍNH ---
def main():
    st.set_page_config(page_title="ViHateGuard Demo", page_icon="🛡️", layout="wide")
    
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1963/1963636.png", width=100)
        st.title("ViHateGuard")
        st.info("Hệ thống phát hiện ngôn từ thù ghét tiếng Việt sử dụng Deep Learning (Bi-LSTM) kết hợp Pipeline xử lý ngôn ngữ mạng.")
        st.markdown("---")
        st.markdown("- Hoàng Sỹ Việt")

    st.title("🛡️ Demo Phân Loại Bình Luận Độc Hại")
    st.markdown("---")

    # Load toàn bộ tài nguyên
    res = load_resources()
    if res is None:
        st.stop()

    model = res["model"]
    vocab = res["vocab"]
    device = res["device"]
    handlers = res["handlers"]
    cfg = res["pipeline_cfg"]

    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.subheader("📝 Nhập nội dung kiểm tra ")
        
        sample_text = st.selectbox(
            "Chọn câu mẫu hoặc nhập mới:",
            [
                "",
                "Sản phẩm này dùng rất tốt, mình rất thích.",
                "Shop làm ăn như cái quần què, phí tiền.",
                "Bọn này kỳ này sống chó thật, cút đi.",
                "Mày nói chuyện ngu vãi chưởng",
                "Đ.m bọn này chếtttttttttt hết đi, r.á.c r.ư.ở.i xh",
                "Nhìn mặt con này ngu ngục vãi chưởng.",
                "thằng này t. ox. ic thật"
            ]
        )
        
        input_val = sample_text if sample_text else ""
        input_text = st.text_area("Nội dung bình luận:", value=input_val, height=150, placeholder="Nhập bình luận tại đây...")
        
        analyze_btn = st.button("🔍 Phân tích ngay", type="primary")

    with col2:
        st.subheader("📊 Kết quả dự đoán")
        if analyze_btn and input_text.strip():
            with st.spinner("Đang chạy Pipeline xử lý & Suy luận..."):
                try:
                    # --- BƯỚC 1: XỬ LÝ QUA PIPELINE & MÃ HÓA ---
                    tensor_input, cleaned_text, metadata = encode_text_with_pipeline(
                        input_text, vocab, MAX_LEN, handlers, cfg
                    )
                    tensor_input = tensor_input.to(device)

                    # --- BƯỚC 2: DỰ ĐOÁN (INFERENCE) ---
                    with torch.no_grad():
                        logits = model(tensor_input)
                        probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

                    # --- BƯỚC 3: HẬU XỬ LÝ (THRESHOLD MOVING) ---
                    prob_clean = probs[0]
                    prob_offensive = probs[1]
                    prob_hate = probs[2]
                    
                    # Ngưỡng quyết định (Có thể tinh chỉnh)
                    THRESHOLD_HATE = 0.65
                    THRESHOLD_OFFENSIVE = 0.60
                    
                    if prob_hate > THRESHOLD_HATE:
                        pred_idx = 2
                    elif prob_offensive > THRESHOLD_OFFENSIVE:
                        pred_idx = 1
                    else:
                        # Fallback về argmax hoặc logic ưu tiên
                        if prob_hate > prob_offensive and prob_hate > prob_clean:
                             pred_idx = 2
                        elif prob_offensive > prob_clean:
                             pred_idx = 1
                        else:
                             pred_idx = 0
                    
                    label = CLASSES[pred_idx]
                    
                    # --- HIỂN THỊ KẾT QUẢ ---
                    if pred_idx == 0:
                        st.success(f"✅ **{label}**")
                    elif pred_idx == 1:
                        st.warning(f"⚠️ **{label}**")
                    else:
                        st.error(f"🚫 **{label}**")
                    
                    # Hiển thị độ tin cậy
                    st.metric("Độ tin cậy", f"{probs[pred_idx]:.2%}")

                    # Biểu đồ cột
                    chart_df = pd.DataFrame({
                        "Nhãn": ["Sạch", "Thô lỗ", "Thù ghét"],
                        "Xác suất": probs,
                        "Màu": ["#2ecc71", "#f1c40f", "#e74c3c"]
                    })
                    st.bar_chart(chart_df.set_index("Nhãn")["Xác suất"])

                except Exception as e:
                    st.error(f"Có lỗi xảy ra: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    main()