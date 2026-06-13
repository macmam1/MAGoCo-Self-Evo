import { useTranslation } from "react-i18next";
import { Link, Route, Routes } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import ForbiddenPage from "@/pages/ForbiddenPage";
import ProtectedRoute from "@/components/auth/ProtectedRoute";

function Home() {
  const { t, i18n } = useTranslation();
  const { user, isAuthenticated, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      <div className="container mx-auto px-4 py-16">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            {t("app.title")}
          </h1>
          <p className="text-xl text-slate-300">{t("app.subtitle")}</p>
          {isAuthenticated && user && (
            <p className="text-sm text-slate-400 mt-2">
              خوش آمدید، <span className="text-blue-400">{user.username}</span> ({user.role})
            </p>
          )}
        </header>

        <main className="max-w-4xl mx-auto space-y-6">
          <section className="bg-slate-800/50 backdrop-blur rounded-2xl p-8 border border-slate-700">
            <h2 className="text-2xl font-semibold mb-4">🚀 وضعیت پروژه</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatusCard label="Backend" status="ok" tech="FastAPI" />
              <StatusCard label="Frontend" status="ok" tech="Vite + React" />
              <StatusCard label="Auth" status="ok" tech="JWT" />
              <StatusCard label="Agent Core" status="pending" tech="CrewAI" />
            </div>
          </section>

          <section className="bg-slate-800/50 backdrop-blur rounded-2xl p-8 border border-slate-700">
            <h2 className="text-2xl font-semibold mb-4">⚙️ اقدامات</h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => i18n.changeLanguage("en")}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
              >
                English
              </button>
              <button
                onClick={() => i18n.changeLanguage("fa")}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition"
              >
                فارسی
              </button>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
              >
                📚 API Docs
              </a>
              {isAuthenticated ? (
                <button
                  onClick={() => void logout()}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition"
                >
                  خروج
                </button>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
                  >
                    ورود
                  </Link>
                  <Link
                    to="/register"
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition"
                  >
                    ثبت‌نام
                  </Link>
                </>
              )}
            </div>
          </section>
        </main>

        <footer className="text-center mt-12 text-slate-500 text-sm">
          v0.2.0 — MAGoCo-Self-Evo
        </footer>
      </div>
    </div>
  );
}

function StatusCard({ label, status, tech }: { label: string; status: "ok" | "pending"; tech: string }) {
  return (
    <div className="bg-slate-900/50 rounded-lg p-4">
      <div className="text-3xl mb-2">{status === "ok" ? "✅" : "🔜"}</div>
      <div className="text-sm text-slate-400">{label}</div>
      <div
        className={`font-mono text-xs ${status === "ok" ? "text-green-400" : "text-yellow-400"}`}
      >
        {tech}
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forbidden" element={<ForbiddenPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
      <Route
        path="*"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
