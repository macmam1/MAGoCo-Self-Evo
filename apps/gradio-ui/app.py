"""Gradio UI — رابط ساده برای کار با agent ها.

این رابط جایگزین ساده‌تری برای frontend اصلی هست.
مناسب برای:
- نصب روی Hugging Face Spaces
- کاربران غیرفنی
- دمو و تست سریع
"""
import os

import gradio as gr
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


def check_backend_health() -> str:
    """Check if backend is reachable."""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/v1/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return f"✅ Backend OK — {data.get('service')} ({data.get('environment')})"
        return f"⚠️ Backend returned {response.status_code}"
    except Exception as e:
        return f"❌ Backend not reachable: {e}"


def chat_with_agent(message: str, history: list) -> str:
    """Placeholder for agent chat (will be implemented with Agent Core)."""
    if not message.strip():
        return "لطفاً یه پیام بنویس."
    return f"🤖 [Placeholder] Agent Core هنوز پیاده‌سازی نشده.\n\nپیام شما: {message}"


# ===== Build Gradio UI =====
with gr.Blocks(title="MAGoCo-Self-Evo", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🤖 MAGoCo-Self-Evo
        **Multi-Agent Go-Coordinator with Self-Evolution**

        رابط ساده — هنوز در حال توسعه
        """
    )

    with gr.Tab("💬 چت"):
        gr.Markdown("### چت با agent")
        chatbot = gr.ChatInterface(
            fn=chat_with_agent,
            title="Agent Chat",
            description="اینجا با agent ها چت کن (به‌زودی)",
        )

    with gr.Tab("🔧 وضعیت سیستم"):
        gr.Markdown("### وضعیت backend")
        health_btn = gr.Button("🔄 بررسی سلامت")
        health_output = gr.Textbox(label="", interactive=False)
        health_btn.click(fn=check_backend_health, outputs=health_output)

        gr.Markdown("### راهنما")
        gr.Markdown(
            """
            - **Frontend حرفه‌ای**: http://localhost:5173
            - **API Docs**: http://localhost:8000/docs
            - **Backend**: FastAPI (port 8000)
            """
        )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
