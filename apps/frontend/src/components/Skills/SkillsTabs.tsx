import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface SkillsTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  tabs?: { id: string; label: string; icon: any }[];
}

export function SkillsTabs({ activeTab, onTabChange, tabs = [] }: SkillsTabsProps) {
  const { t } = useTranslation();

  const defaultTabs = [
    { id: "all", label: t("skills.all"), icon: null },
    { id: "installed", label: t("skills.installed"), icon: null },
    { id: "marketplace", label: t("skills.marketplace"), icon: null },
    { id: "my_skills", label: t("skills.my_skills"), icon: null },
    { id: "compositions", label: t("skills.compositions"), icon: null },
  ];

  const displayTabs = tabs.length > 0 ? tabs : defaultTabs;

  return (
    <div className="flex border-b border-white/5 overflow-x-auto">
      {displayTabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
            "hover:text-[var(--accent)] hover:border-[var(--accent)]",
            activeTab === tab.id
              ? "text-[var(--accent)] border-[var(--accent)]"
              : "text-[var(--text-2)] border-transparent"
          )}
        >
          {tab.icon && <tab.icon className="h-4 w-4" />}
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}