"""
ViHateGuard - Telegram Bot
Bot lắng nghe tin nhắn trong group, gọi FastAPI backend để phân tích,
tự động xóa tin nhắn HATE và cảnh cáo người dùng.

Bot KHÔNG load model trực tiếp → chỉ gọi API backend.
→ Nếu sau này đổi model (Ollama, PhoBERT...), bot không cần sửa.
"""

import os
import sys
import logging
import httpx
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# ---- Logging ----
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ViHateGuard_Bot")

# ---- Config ----
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("api_token", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").strip()

if not BOT_TOKEN:
    logger.error("Không tìm thấy api_token trong .env!")
    sys.exit(1)

# ---- HTTP client (reuse connection) ----
http_client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)


# ---- Handlers ----
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start."""
    await update.message.reply_text(
        "🛡️ *ViHateGuard Bot* đã sẵn sàng!\n\n"
        "Tôi sẽ tự động kiểm tra tin nhắn trong nhóm.\n"
        "Tin nhắn chứa ngôn từ thù ghét sẽ bị xóa và cảnh cáo.\n\n"
        "Gửi `/check <nội dung>` để kiểm tra thủ công.",
        parse_mode="Markdown",
    )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /check <text> - kiểm tra thủ công."""
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Dùng: `/check <nội dung cần kiểm tra>`", parse_mode="Markdown")
        return

    result = await _call_predict(text)
    if result is None:
        await update.message.reply_text("Không thể kết nối tới API backend.")
        return

    label = result["label"]
    label_vi = result["label_vi"]
    confidence = result["confidence"]
    p = result["probabilities"]

    icon = {"CLEAN": "✅", "OFFENSIVE": "⚠️", "HATE": "🚫"}.get(label, "❓")

    msg = (
        f"{icon} *{label}* — {label_vi}\n"
        f"Độ tin cậy: `{confidence:.1%}`\n\n"
        f"Sạch: `{p['clean']:.1%}` | Thô lỗ: `{p['offensive']:.1%}` | Thù ghét: `{p['hate']:.1%}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lắng nghe mọi tin nhắn text trong group."""
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    if not text or text.startswith("/"):
        return

    # Gọi API backend
    result = await _call_predict(text)
    if result is None:
        return  # API không phản hồi → bỏ qua, không spam group

    label = result["label"]

    if label == "HATE":
        user = message.from_user
        user_name = user.full_name if user else "Người dùng"

        # Xóa tin nhắn vi phạm
        try:
            await message.delete()
            logger.info(f"Đã xóa tin nhắn HATE từ {user_name} (id={user.id}): {text[:50]}...")
        except Exception as e:
            logger.warning(f"Không thể xóa tin nhắn: {e}")

        # Gửi cảnh cáo
        try:
            warning = (
                f"🚫*Cảnh cáo* — Thằng {user_name}\n\n"
                f"Bình luận của bạn đã bị xóa do vi phạm tiêu chuẩn cộng đồng.\n"
                f"Vui lòng giữ ngôn từ lịch sự."
            )
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=warning,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Không thể gửi cảnh cáo: {e}")


async def _call_predict(text: str) -> dict | None:
    """Gọi backend POST /predict, trả về dict hoặc None nếu lỗi."""
    try:
        resp = await http_client.post("/predict", json={"text": text})
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"API trả về status {resp.status_code}")
    except Exception as e:
        logger.error(f"Lỗi gọi API: {e}")
    return None


# ---- Main ----
def main():
    logger.info(f"Khởi động ViHateGuard Bot | API: {API_BASE_URL}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("check", check_command))

    # Lắng nghe mọi tin nhắn text trong group (không phải command)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            handle_group_message,
        )
    )

    # Cho phép check cả tin nhắn private (DM)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            _handle_private_message,
        )
    )

    app.run_polling(drop_pending_updates=True)


async def _handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cho phép người dùng gửi tin nhắn riêng để kiểm tra."""
    text = update.message.text.strip()
    if not text:
        return

    result = await _call_predict(text)
    if result is None:
        await update.message.reply_text("Không thể kết nối tới API backend.")
        return

    label = result["label"]
    label_vi = result["label_vi"]
    confidence = result["confidence"]
    p = result["probabilities"]

    icon = {"CLEAN": "", "OFFENSIVE": "", "HATE": ""}.get(label, "❓")

    msg = (
        f"{icon} *{label}* — {label_vi}\n"
        f"Độ tin cậy: `{confidence:.1%}`\n\n"
        f"Sạch: `{p['clean']:.1%}` | Thô lỗ: `{p['offensive']:.1%}` | Thù ghét: `{p['hate']:.1%}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


if __name__ == "__main__":
    main()
