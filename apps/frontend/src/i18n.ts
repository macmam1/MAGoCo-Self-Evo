import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      app: {
        title: "MAGoCo-Self-Evo",
        subtitle: "Multi-Agent Go-Coordinator with Self-Evolution",
        status: "Setup Status",
        actions: "Quick Actions",
      },
      nav: {
        dashboard: "Command Center",
        chat: "Agent Chat",
        ide: "Coding IDE",
        workflows: "Workflows",
        approvals: "Approvals",
        integrations: "Integrations",
        history: "History",
        settings: "Settings",
      },
      groups: { general: "General", operations: "Operations", system: "System" },
      topbar: { search: "Search or jump to…" },
      hero: {
        greeting: "Good evening, Operator",
        sub: "I'm Rune, where should we start today?",
        example: "Example: Summarise my last agent run and suggest next steps…",
        previous: "Previous chats",
      },
    },
  },
  fa: {
    translation: {
      app: {
        title: "MAGoCo-Self-Evo",
        subtitle: "هماهنگ‌کننده چندعاملی با خودتکاملی",
        status: "وضعیت راه‌اندازی",
        actions: "اقدامات سریع",
      },
      nav: {
        dashboard: "مرکز فرمان",
        chat: "گفتگو با ایجنت",
        ide: "محیط کدنویسی",
        workflows: "ورک‌فلوها",
        approvals: "تأییدها",
        integrations: "اتصال‌ها",
        history: "تاریخچه",
        settings: "تنظیمات",
      },
      groups: { general: "عمومی", operations: "عملیات", system: "سیستم" },
      topbar: { search: "جستجو یا پرش به…" },
      hero: {
        greeting: "عصر بخیر، اپراتور",
        sub: "من رون هستم، امروز از کجا شروع کنیم؟",
        example: "مثال: آخرین اجرای ایجنت را خلاصه کن و قدم بعدی را پیشنهاد بده…",
        previous: "گفتگوهای قبلی",
      },
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
