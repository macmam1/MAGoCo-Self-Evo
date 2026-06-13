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
