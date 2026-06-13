import { useTranslation } from "react-i18next";

function App() {
  const { t, i18n } = useTranslation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      <div className="container mx-auto px-4 py-16">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            {t("app.title")}
          </h1>
          <p className="text-xl text-slate-300">{t("app.subtitle")}</p>
        </header>

        <main className="max-w-4xl mx-auto">
          <section className="bg-slate-800/50 backdrop-blur rounded-2xl p-8 mb-6 border border-slate-700">
            <h2 className="text-2xl font-semibold mb-4">🚀 {t("app.status")}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-3xl mb-2">✅</div>
                <div className="text-sm text-slate-400">Backend</div>
                <div className="text-green-400 font-mono text-xs">FastAPI</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-3xl mb-2">✅</div>
                <div className="text-sm text-slate-400">Frontend</div>
                <div className="text-green-400 font-mono text-xs">Vite + React</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-4">
                <div className="text-3xl mb-2">🔜</div>
                <div className="text-sm text-slate-400">Agent Core</div>
                <div className="text-yellow-400 font-mono text-xs">Coming soon</div>
              </div>
            </div>
          </section>

          <section className="bg-slate-800/50 backdrop-blur rounded-2xl p-8 border border-slate-700">
            <h2 className="text-2xl font-semibold mb-4">⚙️ {t("app.actions")}</h2>
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
            </div>
          </section>
        </main>

        <footer className="text-center mt-12 text-slate-500 text-sm">
          v0.1.0 — MAGoCo-Self-Evo
        </footer>
      </div>
    </div>
  );
}

export default App;
