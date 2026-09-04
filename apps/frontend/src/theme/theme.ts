export interface ThemeMeta {
  id: string;
  name: string;
  blurb: string;
  dark: boolean;
  /** 3 swatch colors for the preview card */
  preview: [string, string, string];
}

export const THEMES: ThemeMeta[] = [
  {
    id: "fusion",
    name: "Fusion",
    blurb: "Ask Rune × NeuroNest × LucidAI — pro command center",
    dark: true,
    preview: ["#0a0a10", "#7c5cff", "#f5a524"],
  },
  {
    id: "midnight",
    name: "Midnight",
    blurb: "Deep-space dark, violet + teal glow",
    dark: true,
    preview: ["#0a0a0f", "#7c5cff", "#00e0c6"],
  },
  {
    id: "linear",
    name: "Linear",
    blurb: "Neutral engineering minimal, monochrome",
    dark: true,
    preview: ["#08090c", "#e2e8f0", "#5e6ad2"],
  },
  {
    id: "light",
    name: "Daybreak",
    blurb: "Clean professional light",
    dark: false,
    preview: ["#f7f8fa", "#4f46e5", "#0ea5e9"],
  },
  {
    id: "system",
    name: "System",
    blurb: "Follows your OS automatically",
    dark: true,
    preview: ["#0a0a10", "#f7f8fa", "#7c5cff"],
  },
];

export interface FontMeta {
  id: string;
  name: string;
  sample: string;
  stack: string;
}

export const FONTS: FontMeta[] = [
  {
    id: "sans",
    name: "Sans Serif",
    sample: "Aa Bb Cc",
    stack: '"Vazirmatn", "Inter", system-ui, sans-serif',
  },
  {
    id: "serif",
    name: "Serif",
    sample: "Aa Bb Cc",
    stack: 'Georgia, "Times New Roman", serif',
  },
  {
    id: "mono",
    name: "Mono",
    sample: "Aa Bb Cc",
    stack: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
  },
];

export type Density = "default" | "compact";

const THEME_KEY = "magoco-theme";
const FONT_KEY = "magoco-font";
const DENSITY_KEY = "magoco-density";
const LANG_KEY = "magoco-lang";

function load(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

function prefersLight(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: light)").matches
  );
}

function resolveTheme(id: string): string {
  if (id === "system") return prefersLight() ? "light" : "fusion";
  return THEMES.some((t) => t.id === id) ? id : "fusion";
}

function paint(themeId: string) {
  const meta = THEMES.find((t) => t.id === themeId) ?? THEMES[0];
  const dark = themeId === "system" ? !prefersLight() : meta.dark;
  document.documentElement.dataset.theme = themeId === "system" ? resolveTheme("system") : themeId;
  document.documentElement.dataset.themeMode = themeId;
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
}

export function getTheme(): string {
  return load(THEME_KEY, "fusion");
}

export function applyTheme(id: string) {
  save(THEME_KEY, id);
  paint(id);
  window.dispatchEvent(new CustomEvent("magoco:theme", { detail: id }));
}

/** Follows OS changes while "System" is active. Call once at startup. */
export function watchSystemTheme() {
  if (typeof window === "undefined" || !window.matchMedia) return;
  window.matchMedia("(prefers-color-scheme: light)").addEventListener?.("change", () => {
    if (getTheme() === "system") {
      paint("system");
      window.dispatchEvent(new CustomEvent("magoco:theme", { detail: "system" }));
    }
  });
}

// ---- Fonts ----

export function getFont(): string {
  const id = load(FONT_KEY, "sans");
  return FONTS.some((f) => f.id === id) ? id : "sans";
}

export function applyFont(id: string) {
  const font = FONTS.find((f) => f.id === id) ?? FONTS[0];
  document.documentElement.style.setProperty("--font-body", font.stack);
  save(FONT_KEY, font.id);
  window.dispatchEvent(new CustomEvent("magoco:font", { detail: font.id }));
}

// ---- Density ----

export function getDensity(): Density {
  return load(DENSITY_KEY, "default") === "compact" ? "compact" : "default";
}

export function applyDensity(d: Density) {
  document.documentElement.dataset.density = d;
  save(DENSITY_KEY, d);
  window.dispatchEvent(new CustomEvent("magoco:density", { detail: d }));
}

// ---- Language (fa/en + RTL) ----

export function getLang(): string {
  const v = load(LANG_KEY, "en");
  return v === "fa" ? "fa" : "en";
}

export function applyLang(lang: string) {
  const v = lang === "fa" ? "fa" : "en";
  save(LANG_KEY, v);
  document.documentElement.lang = v;
  document.documentElement.dir = v === "fa" ? "rtl" : "ltr";
  window.dispatchEvent(new CustomEvent("magoco:lang", { detail: v }));
  return v;
}

/** Apply every persisted preference. Call once at startup. */
export function applyAllPreferences() {
  paint(load(THEME_KEY, "fusion"));
  const font = FONTS.find((f) => f.id === load(FONT_KEY, "sans")) ?? FONTS[0];
  document.documentElement.style.setProperty("--font-body", font.stack);
  document.documentElement.dataset.density = load(DENSITY_KEY, "default");
  const lang = load(LANG_KEY, "en") === "fa" ? "fa" : "en";
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
}
