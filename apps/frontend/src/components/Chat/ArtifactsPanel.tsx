import { useState, useEffect } from "react";
import { X, Copy, Download, FileCode, FileText, Image, ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface Artifact {
  id: string;
  type: "code" | "text" | "image" | "html";
  title: string;
  content: string;
  language?: string;
  createdAt: number;
  messageId: string;
}

export function ArtifactsPanel({ 
  artifacts = [], 
  onClose, 
  isOpen,
  onCopy,
  onDownload 
}: { 
  artifacts: Artifact[]; 
  onClose: () => void; 
  isOpen: boolean;
  onCopy?: (content: string) => void;
  onDownload?: (artifact: Artifact) => void;
}) {
  const { t } = useTranslation();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!isOpen || artifacts.length === 0) return null;

  return (
    <div className="fixed right-0 top-0 bottom-0 z-40 flex flex-col animate-slide-right">
      <div className="absolute left-0 top-0 bottom-0 w-full bg-black/50" onClick={onClose} aria-hidden="true" />
      
      <div className="relative flex flex-col w-full max-w-xl h-full bg-white/5 border-l border-white/10 backdrop-blur-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <FileCode className="h-5 w-5" style={{ color: "var(--accent)" }} />
            <h3 className="font-semibold" style={{ color: "var(--text-0)" }}>
              {t("artifacts.title")}
              <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded-full font-medium" 
                    style={{ background: "color-mix(in srgb, var(--accent) 20%, transparent)", color: "var(--accent)" }}>
                {artifacts.length}
              </span>
            </h3>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Artifacts List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {artifacts.map((artifact, index) => (
            <ArtifactCard
              key={artifact.id}
              artifact={artifact}
              index={index + 1}
              isExpanded={expandedId === artifact.id}
              onToggle={() => setExpandedId(expandedId === artifact.id ? null : artifact.id)}
              onCopy={onCopy}
              onDownload={onDownload}
            />
          ))}
        </div>

        {/* Empty state */}
        {artifacts.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full p-8 text-text-2/4">
            <FileCode className="w-12 h-12 mb-3" />
            <p>{t("artifacts.empty")}</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface ArtifactCardProps {
  artifact: Artifact;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
  onCopy?: (content: string) => void;
  onDownload?: (artifact: Artifact) => void;
}

function ArtifactCard({ artifact, index, isExpanded, onToggle, onCopy, onDownload }: ArtifactCardProps) {
  const { t } = useTranslation();
  const iconMap = {
    code: FileCode,
    text: FileText,
    image: Image,
    html: FileCode,
  };
  const Icon = iconMap[artifact.type];

  const getLanguageLabel = (lang?: string) => {
    if (!lang) return t("artifacts.unknown_lang");
    const labels: Record<string, string> = {
      python: "Python",
      javascript: "JavaScript",
      typescript: "TypeScript",
      jsx: "JSX",
      tsx: "TSX",
      html: "HTML",
      css: "CSS",
      json: "JSON",
      markdown: "Markdown",
      sql: "SQL",
      bash: "Bash",
      shell: "Shell",
      rust: "Rust",
      go: "Go",
      java: "Java",
      cpp: "C++",
      c: "C",
    };
    return labels[lang.toLowerCase()] || lang.toUpperCase();
  };

  return (
    <div className="rounded-xl border overflow-hidden transition-all duration-200"
         style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded" 
                style={{ background: "color-mix(in srgb, var(--accent) 15%, transparent)", color: "var(--accent)" }}>
            #{index}
          </span>
          <Icon className="h-4 w-4 shrink-0" style={{ color: "var(--accent-2)" }} />
          <span className="font-medium truncate flex-1" style={{ color: "var(--text-0)" }}>
            {artifact.title || t("artifacts.untitled")}
          </span>
          {artifact.language && (
            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" 
                  style={{ background: "var(--bg-2)", color: "var(--text-1)" }}>
              {getLanguageLabel(artifact.language)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {artifact.type === "code" && onCopy && (
            <Button variant="ghost" size="sm" onClick={() => onCopy?.(artifact.content)} className="h-7 w-7 p-0" 
                    aria-label={t("artifacts.copy")}>
              <Copy className="h-3.5 w-3.5" />
            </Button>
          )}
          {onDownload && (
            <Button variant="ghost" size="sm" onClick={() => onDownload?.(artifact)} className="h-7 w-7 p-0"
                    aria-label={t("artifacts.download")}>
              <Download className="h-3.5 w-3.5" />
            </Button>
          )}
          <ChevronRight className={cn("h-4 w-4 transition-transform", isExpanded && "rotate-90")} 
                       style={{ color: "var(--text-2)" }} />
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-white/5 p-3 bg-white/[0.02] animate-slide-down">
          {artifact.type === "image" ? (
            <img 
              src={artifact.content} 
              alt={artifact.title} 
              className="max-w-full h-auto rounded-lg border border-white/10"
              style={{ maxHeight: "400px" }}
            />
          ) : artifact.type === "html" ? (
            <div className="rounded-lg border border-white/10 overflow-hidden" style={{ minHeight: "200px" }}>
              <iframe 
                srcDoc={artifact.content} 
                className="w-full h-[300px] border-0"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          ) : (
            <pre className="rounded-lg bg-black/50 p-3 overflow-x-auto max-h-[400px]">
              <code className={artifact.language ? `language-${artifact.language}` : ""}>
                {artifact.content}
              </code>
            </pre>
          )}
        </div>
      )}
    </div>
  );
}