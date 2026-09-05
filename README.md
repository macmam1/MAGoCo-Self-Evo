# MAGoCo-Self-Evo

> **Multi-Agent Go-Coordinator with Self-Evolution & Multi-Interface Platform**
> پلتفرم multi-agent با قابلیت خودتکامهی، کدینگ IDE، چت، داشبورد تنظیمات، اتصال به شبکه‌های اجتماعی (تلگرام) و اتوماسیون.

---

## ⚡️ وضعیت فعلی پروژه (شاخه `feat/v2-unified-ui`)

| بخش | وضعیت | توضیح |
|------|--------|--------|
| **Chat Core** | ✅ Working | Streaming thinking، Artifacts، fork/edit، model switcher، i18n fa/en |
| **Agent Browser** | ✅ Working | Playwright + `/ws/browser` screenshot streaming + confirm modals |
| **Workflow Engine** | ✅ Working | Canvas DAG builder + executor (parallel/conditional/retry) + ۵ تمپلیت + API |
| **Memory System** | ✅ Working | LanceDB+SQLite+JSONL، vector/keyword/hybrid search، KG، episodic، RAG + UI ۵ تب |
| **Skills System** | ✅ Working | Registry + versioning + sandboxed executor + marketplace + builder + API |
| **Integrations** | ✅ Working | Registry سبک + `/integrations-registry` API + seed + dashboard (marketplace/webhooks/OAuth) |
| **Agent Growth (حلقه بسته)** | ✅ Working | Auto-track chat/browser/workflow → pattern mining → suggestion → Apply→draft skill |
| **Feature Registry** | ✅ Working | Manifest + enable/disable + dependency + `/api/v1/features/*` |
| **UI Shell** | ✅ Working | ۱۳ barrel export، تم/فونت/چگالی/زبان، ⌘K، shortcuts، Modal |
| **Backend API** | ✅ Working | FastAPI + WebSocket chat/browser + ده‌ها router |
| **LLM Integration** | ⚠️ Partial | Gateway موجود؛ اتصال واقعی 9Router/OpenAI نیازمند کلید و تست زنده است |

---

## 🏗️ ساختار کلان (ماژولار)

```
MAGoCo-Self-Evo/
├── apps/
│   ├── backend/               # FastAPI + WebSocket + REST API
│   ├── frontend/              # Vite + React + TypeScript + TailwindCSS + Monaco + ReactFlow
│   └── gradio-ui/             # Gradio lightweight alternative UI
├── packages/
│   ├── magoco-core/           # Core Engine: Agent + Tools + Memory + ReAct + Skills + LLM Gateway
│   └── magoco-workflows/      # Workflow DAG Execution Engine
├── gateways/                  # External Communication Bridges (Telegram)
├── docs/                      # Architectural Documentation & Project Status Log
├── install.sh                 # 1-Click Auto Installer Script
└── docker-compose.yml         # Production Multi-Stage Docker Compose
```

## 🎨 قابلیت‌های اصلی

| دسته | ویژگی‌ها |
|------|----------|
| **Agent Chat** | Streaming زنده، بلوک‌های تفکر (Thinking Blocks)، Tool Calls |
| **Vibe-Coding IDE** | Monaco Editor + File Tree + Diff Preview + AI Code Generation |
| **Workflow Designer** | ReactFlow Drag & Drop، ۵ نوع گره (Agent/Tool/Condition/Input/Output) |
| **Skills Marketplace** | YAML Frontmatter Parser، Dynamic Loader، Auto-discovery |
| **Human-in-the-Loop** | Approval Gates (تأیید/رد)، Planning Panel, Clarification |
| **Integrations Panel** | Slack, GitHub, Gmail, Notion, HubSpot, وب‌هوک‌ها |
| **Execution History** | Audit Trail کامل با لاگ‌ها، وضعیت، زمان‌بندی |
| **Telegram Gateway** | Bot + Approval Inline Buttons + Voice + Topics |
| **Self-Evolution** | Reflection, Pattern Mining, Skill Generation, Knowledge Distillation |
| **Multi-Agent** | ۵ نقش ایجنت تخصصی (Coordinator, Architect, Coder, Reviewer, Researcher) |
| **3-Layer Memory** | Working Context, Full Conversation, Distilled Knowledge Graph |
| **LLM Gateway** | OpenAI, Ollama, 9ROUTER (بسترچند مدل) با fallback |

## 🚀 شروع سریع

### نصب Production (Docker)

```bash
git clone https://github.com/macmam1/MAGoCo-Self-Evo.git
cd MAGoCo-Self-Evo
cp .env.example .env    # ویرایش برای اضافه کردن LLM API Keyها
docker-compose up -d --build
curl http://localhost:8000/health
```

### یا نصب یکخطی (One-Line)

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/macmam1/MAGoCo-Self-Evo/main/install.sh)"
```

**لینک‌های سرویس:**
- 🌐 **Frontend**: http://localhost:5173
- ⚙️ **Backend API**: http://localhost:8000
- 📝 **Swagger Docs**: http://localhost:8000/docs
- 🩺 **Health Check**: http://localhost:8000/health

## 📚 مستندات

- [معماری کامل (Master Blueprint)](docs/MASTER_BLUEPRINT.md)
- [وضعیت پروژه و Handover برای ایجنت‌های بعدی](docs/PROJECT_STATUS_LOG.md)
- [راهنما و تنظیمات Backend](apps/backend/README.md)

## 📄 License

MIT