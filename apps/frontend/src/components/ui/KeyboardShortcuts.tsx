import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Keyboard, Command } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface Shortcut {
  keys: string;
  description: string;
  category: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: "⌘ K", description: "Open Command Palette", category: "Navigation" },
  { keys: "⌘ /", description: "Show Keyboard Shortcuts", category: "Navigation" },
  { keys: "⌘ 1-9", description: "Switch to tab 1-9", category: "Navigation" },
  { keys: "⌘ Shift [", description: "Previous tab", category: "Navigation" },
  { keys: "⌘ Shift ]", description: "Next tab", category: "Navigation" },
  { keys: "⌘ B", description: "Toggle Sidebar", category: "Navigation" },
  { keys: "Enter", description: "Send message (in chat)", category: "Chat" },
  { keys: "Shift + Enter", description: "New line (in chat)", category: "Chat" },
  { keys: "⌘ ↑", description: "Edit last message", category: "Chat" },
  { keys: "Escape", description: "Close modals / Cancel", category: "General" },
  { keys: "⌘ ,", description: "Open Settings", category: "General" },
  { keys: "⌘ D", description: "Toggle Theme (Dark/Light)", category: "General" },
  { keys: "⌘ L", description: "Toggle Language (fa/en)", category: "General" },
];

function getShortcutsByCategory() {
  const categories: Record<string, Shortcut[]> = {};
  for (const shortcut of SHORTCUTS) {
    if (!categories[shortcut.category]) {
      categories[shortcut.category] = [];
    }
    categories[shortcut.category].push(shortcut);
  }
  return categories;
}

export function KeyboardShortcutsModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const categories = getShortcutsByCategory();

  if (!isOpen) return null;

  const content = (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10 glass-strong rounded-2xl border max-w-md w-full mx-4 animate-slide-up">
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5" style={{ color: "var(--accent)" }} />
            <h3 className="font-semibold" style={{ color: "var(--text-0)" }}>
              {t("shortcuts.keyboard_shortcuts")}
            </h3>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
            aria-label={t("shortcuts.close")}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          {Object.entries(categories).map(([category, shortcuts]) => (
            <div key={category} className="mb-4">
              <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-2)" }}>
                {t(`shortcuts.${category.toLowerCase()}`) || category}
              </div>
              <div className="space-y-2">
                {shortcuts.map((s, i) => (
                  <div key={i} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-white/[0.03]">
                    <span className="text-sm" style={{ color: "var(--text-1)" }}>
                      {t(`shortcuts.${s.description.toLowerCase().replace(/\s+/g, '_')}`) || s.description}
                    </span>
                    <kbd className="font-mono text-[10px] px-2 py-0.5 rounded border" style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)", color: "var(--text-0)" }}>
                      {s.keys}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}

export function useKeyboardShortcuts() {
  const { t } = useTranslation();
  const [showShortcuts, setShowShortcuts] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // ⌘ / or ? to show shortcuts
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        setShowShortcuts(true);
      }
      // Escape to close
      if (e.key === "Escape") {
        setShowShortcuts(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return { showShortcuts, setShowShortcuts };
}