# Frontend (Vite + React + TypeScript)

رابط کاربری حرفه‌ای پروژه MAGoCo-Self-Evo.

## 🏗️ ساختار

```
frontend/
├── src/
│   ├── main.tsx          # Entry point
│   ├── App.tsx           # Root component
│   ├── index.css         # Global styles + Tailwind
│   ├── i18n.ts           # i18n config (en + fa)
│   ├── api/              # API client
│   │   └── client.ts
│   ├── components/       # Reusable components
│   ├── pages/            # Page components
│   ├── hooks/            # Custom React hooks
│   ├── stores/           # Zustand stores
│   ├── lib/              # Utilities
│   │   └── utils.ts
│   └── i18n/             # Translation files
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── Dockerfile
```

## 🚀 اجرا (با Docker)

```bash
# از root
make up
```

Frontend: http://localhost:5173

## 🛠️ اجرا (محلی)

```bash
cd apps/frontend

# نصب
pnpm install
# یا npm install / yarn

# اجرا
pnpm dev
```

## 🎨 Tech Stack

- **Vite** — build tool
- **React 18** + **TypeScript** — UI framework
- **Tailwind CSS** — styling
- **shadcn/ui** — components (optional)
- **React Router** — routing
- **TanStack Query** — server state
- **Zustand** — client state
- **React Hook Form** + **Zod** — forms & validation
- **i18next** — i18n (en + fa)
- **React Flow** — workflow maker
- **Axios** — HTTP client
- **Vitest** + **Testing Library** — tests

## 📝 اضافه کردن صفحه جدید

```tsx
// src/pages/MyPage.tsx
export default function MyPage() {
  return <div>My Page</div>;
}

// src/App.tsx
import MyPage from "./pages/MyPage";
<Route path="/my-page" element={<MyPage />} />;
```

## 🌍 i18n

دو زبان فعال: `en` (پیش‌فرض) و `fa`.

ترجمه‌ها در `src/i18n.ts` (در آینده به فایل جداگانه منتقل میشه).
