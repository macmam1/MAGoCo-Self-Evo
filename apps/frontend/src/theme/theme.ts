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
];

const KEY = "magoco-theme";

export function getTheme(): string {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && THEMES.some((t) => t.id === saved)) return saved;
  } catch {
    /* ssr / private mode */
  }
  return "midnight";
}

export function applyTheme(id: string) {
  const theme = THEMES.find((t) => t.id === id) ?? THEMES[0];
  document.documentElement.dataset.theme = theme.id;
  document.documentElement.style.colorScheme = theme.dark ? "dark" : "light";
  try {
    localStorage.setItem(KEY, theme.id);
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new CustomEvent("magoco:theme", { detail: theme.id }));
}
