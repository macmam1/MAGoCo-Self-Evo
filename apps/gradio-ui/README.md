# Gradio UI — رابط ساده

رابط کاربری ساده بر پایه Gradio. مناسب برای:
- 🚀 Hugging Face Spaces (رایگان)
- 👥 کاربران غیرفنی
- 🧪 دمو و تست سریع

## 🏗️ ساختار

```
gradio-ui/
├── app.py              # Gradio app
├── requirements.txt
└── Dockerfile
```

## 🚀 اجرا

### با Docker
```bash
docker-compose up gradio
```

### محلی
```bash
cd apps/gradio-ui
pip install -r requirements.txt
python app.py
```

UI در: http://localhost:7860

## 🤗 استقرار روی Hugging Face Spaces

```bash
# ساخت Space با SDK: Docker
# کپی محتوای این پوشه
# Push کن
git remote add hf https://huggingface.co/spaces/USERNAME/MAGoCo-Self-Evo
git push hf main
```

⚠️ **نکته:** در `app.py` باید `BACKEND_URL` به public URL تغییر کنه.
