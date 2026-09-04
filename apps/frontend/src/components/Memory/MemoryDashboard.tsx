import { useState, useEffect } from "react";
import { Brain, Search, Plus, Database, Network, Clock, RefreshCw, TrendingUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button, Badge, Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";

interface MemoryStats {
  total_memories: number;
  by_type: Record<string, number>;
  episodic_count: number;
  kg_nodes: number;
  kg_edges: number;
  document_chunks: number;
  vector_store: string;
}

export function MemoryDashboard() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "search" | "graph" | "episodic" | "rag">("overview");

  const fetchStats = async () => {
    try {
      const response = await fetch("/api/v1/memory/stats");
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: "overview", label: t("memory.overview"), icon: TrendingUp },
    { id: "search", label: t("memory.search"), icon: Search },
    { id: "graph", label: t("memory.knowledge_graph"), icon: Network },
    { id: "episodic", label: t("memory.episodic"), icon: Clock },
    { id: "rag", label: t("memory.rag"), icon: Database },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="animate-spin h-12 w-12 border-b-2 border-current" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center">
            <Brain className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="font-medium text-sm text-white">{t("memory_system")}</h2>
            <p className="text-xs text-text-2">{t("memory_subtitle")}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-xs">
            {stats?.vector_store || "unknown"}
          </Badge>
          <Button variant="outline" size="sm" onClick={fetchStats}>
            <RefreshCw className="h-4 w-4 mr-1" /> {t("refresh")}
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-white/5 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors",
              "hover:text-white hover:border-[var(--accent)]",
              activeTab === tab.id
                ? "text-[var(--accent)] border-[var(--accent)]"
                : "text-text-2 border-transparent"
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
            {(tab.id === "overview" && stats) && (
              <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded-full font-medium"
                    style={{ background: "color-mix(in srgb, var(--accent) 15%, transparent)", color: "var(--accent)" }}>
                {stats.total_memories}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "overview" && <OverviewTab stats={stats} />}
        {activeTab === "search" && <SearchTab />}
        {activeTab === "graph" && <GraphTab />}
        {activeTab === "episodic" && <EpisodicTab />}
        {activeTab === "rag" && <RAGTab />}
      </div>
    </div>
  );
}

function OverviewTab({ stats }: { stats: MemoryStats | null }) {
  const { t } = useTranslation();

  if (!stats) return null;

  const statCards = [
    { key: "total", label: t("memory.total_memories"), value: stats.total_memories, icon: Brain, color: "#7c5cff" },
    { key: "episodic", label: t("memory.episodic_count"), value: stats.episodic_count, icon: Clock, color: "#f5a524" },
    { key: "kg_nodes", label: t("memory.kg_nodes"), value: stats.kg_nodes, icon: Network, color: "#22d3ee" },
    { key: "chunks", label: t("memory.document_chunks"), value: stats.document_chunks, icon: Database, color: "#34d399" },
  ];

  return (
    <div className="p-6 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {statCards.map((s) => (
            <Card key={s.key} className="relative overflow-hidden">
              <div className="flex items-center justify-between mb-3">
                <s.icon className="h-5 w-5" style={{ color: s.color }} />
                <Badge variant="secondary" className="text-[10px]">
                  {s.value}
                </Badge>
              </div>
              <div className="text-2xl font-bold" style={{ color: s.color }}>
                {s.value}
              </div>
              <div className="text-[11px] mt-1" style={{ color: "var(--text-2)" }}>
                {s.label}
              </div>
            </Card>
          ))}
        </div>

        {/* Memory Types Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("memory.by_type")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(stats.by_type || {}).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                  <span className="text-sm font-medium capitalize" style={{ color: "var(--text-0)" }}>
                    {type}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {count}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("memory.quick_actions")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl border hover:border-[var(--accent)] transition-colors"
                      style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}>
                <Search className="h-4 w-4" style={{ color: "var(--accent)" }} />
                <span style={{ color: "var(--text-0)" }}>{t("memory.search_memories")}</span>
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl border hover:border-[var(--accent)] transition-colors"
                      style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}>
                <Network className="h-4 w-4" style={{ color: "var(--accent)" }} />
                <span style={{ color: "var(--text-0)" }}>{t("memory.explore_graph")}</span>
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl border hover:border-[var(--accent)] transition-colors"
                      style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}>
                <Database className="h-4 w-4" style={{ color: "var(--accent)" }} />
                <span style={{ color: "var(--text-0)" }}>{t("memory.manage_rag")}</span>
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl border hover:border-[var(--accent)] transition-colors"
                      style={{ background: "var(--bg-2)", borderColor: "var(--border-glass)" }}>
                <Clock className="h-4 w-4" style={{ color: "var(--accent)" }} />
                <span style={{ color: "var(--text-0)" }}>{t("memory.view_episodic")}</span>
              </button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function SearchTab() {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchType, setSearchType] = useState<"hybrid" | "vector" | "keyword">("hybrid");

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const response = await fetch("/api/v1/memory/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          top_k: 20,
          use_vector: searchType !== "keyword",
          use_keyword: searchType !== "vector",
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setResults(data);
      }
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-4">
      <div className="mb-4 flex gap-2">
        <div className="flex-1 relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder={t("memory.search_placeholder")}
            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-4 py-3 focus:ring-2 focus:ring-primary pl-10"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-text-2" />
        </div>
        <select
          value={searchType}
          onChange={(e) => setSearchType(e.target.value as any)}
          className="bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
        >
          <option value="hybrid">{t("memory.hybrid")}</option>
          <option value="vector">{t("memory.vector")}</option>
          <option value="keyword">{t("memory.keyword")}</option>
        </select>
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="px-4 py-2 bg-gradient-to-r from-accent to-accent-2 text-black font-medium rounded-lg hover:shadow-lg disabled:opacity-50"
        >
          {loading ? t("searching") : t("search")}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3">
        {results.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-64 text-text-2">
            <Search className="w-12 h-12 mb-3 opacity-30" />
            <p>{t("memory.no_results")}</p>
          </div>
        )}
        {results.map((r, i) => (
          <MemoryResultCard key={i} result={r} index={i + 1} />
        ))}
      </div>
    </div>
  );
}

function GraphTab() {
  const { t } = useTranslation();
  const [entity, setEntity] = useState("");
  const [graph, setGraph] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchGraph = async () => {
    if (!entity.trim()) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/memory/memory-graph/${encodeURIComponent(entity)}?max_depth=2`);
      if (response.ok) {
        const data = await response.json();
        setGraph(data);
      }
    } catch (error) {
      console.error("Graph fetch failed:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-4">
      <div className="mb-4 flex gap-2">
        <input
          type="text"
          value={entity}
          onChange={(e) => setEntity(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && fetchGraph()}
          placeholder={t("memory.graph_entity_placeholder")}
          className="flex-1 bg-gray-800/50 border border-white/10 rounded-lg px-4 py-3 focus:ring-2 focus:ring-primary"
        />
        <button
          onClick={fetchGraph}
          disabled={loading || !entity.trim()}
          className="px-4 py-2 bg-gradient-to-r from-accent to-accent-2 text-black font-medium rounded-lg"
        >
          {loading ? t("loading") : t("explore")}
        </button>
      </div>

      <div className="flex-1">
        {graph && (
          <div className="h-full bg-gray-900/50 rounded-xl border border-white/5 overflow-hidden">
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <h3 className="font-medium">{t("memory.graph_for")} "{entity}"</h3>
              <span className="text-xs text-text-2">
                {graph.nodes?.length || 0} {t("nodes")}, {graph.edges?.length || 0} {t("edges")}
              </span>
            </div>
            <div className="h-[calc(100%-60px)] p-4">
              {graph.nodes && graph.nodes.length > 0 ? (
                <div className="h-full grid grid-cols-2 md:grid-cols-3 gap-3 overflow-y-auto">
                  {graph.nodes.map((n: any, i: number) => (
                    <div key={n.id} className="p-3 rounded-lg border hover:border-[var(--accent)] cursor-pointer transition-colors"
                         style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                      <div className="font-medium truncate">{n.label}</div>
                      <div className="text-[10px] text-text-2 mt-1">{n.type}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-text-2">
                  <p>{t("memory.no_graph_data")}</p>
                </div>
              )}
            </div>
          </div>
        )}
        {!graph && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-text-2">
            <Network className="w-16 h-16 mb-4 opacity-30" />
            <p>{t("memory.enter_entity")}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function EpisodicTab() {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/v1/memory/episodic/sessions?limit=50");
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  return (
    <div className="flex flex-col h-full p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">{t("memory.episodic_sessions")}</h3>
        <button
          onClick={fetchSessions}
          disabled={loading}
          className="px-3 py-1.5 text-xs rounded-lg border hover:border-[var(--accent)]"
        >
          {loading ? t("loading") : t("refresh")}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-64 text-text-2">
            <Clock className="w-12 h-12 mb-3 opacity-30" />
            <p>{t("memory.no_sessions")}</p>
          </div>
        )}

        <div className="space-y-2">
          {sessions.map((session: any) => (
            <EpisodicSessionCard key={session.session_id} session={session} />
          ))}
        </div>
      </div>
    </div>
  );
}

function RAGTab() {
  const { t } = useTranslation();
  const [documentId, setDocumentId] = useState("");
  const [content, setContent] = useState("");
  const [chunks, setChunks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const addChunk = async () => {
    if (!documentId.trim() || !content.trim()) return;
    setLoading(true);
    try {
      const response = await fetch("/api/v1/memory/chunks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: documentId, content }),
      });
      if (response.ok) {
        const data = await response.json();
        setChunks(prev => [{ id: data.id, document_id: documentId, content }, ...prev]);
        setContent("");
      }
    } catch (error) {
      console.error("Add chunk failed:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-4">
      <div className="mb-4 space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            placeholder={t("memory.document_id")}
            className="flex-1 bg-gray-800/50 border border-white/10 rounded-lg px-4 py-3 focus:ring-2 focus:ring-primary"
          />
          <input
            type="text"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={t("memory.chunk_content")}
            className="flex-1 bg-gray-800/50 border border-white/10 rounded-lg px-4 py-3 focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={addChunk}
            disabled={loading || !documentId.trim() || !content.trim()}
            className="px-4 py-3 bg-gradient-to-r from-accent to-accent-2 text-black font-medium rounded-lg"
          >
            {t("memory.add_chunk")}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {chunks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 text-text-2">
            <Database className="w-12 h-12 mb-3 opacity-30" />
            <p>{t("memory.no_chunks")}</p>
          </div>
        )}

        <div className="space-y-2">
          {chunks.map((chunk: any, i: number) => (
            <div key={i} className="p-3 rounded-lg border hover:border-[var(--accent)]"
                 style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-text-2">{chunk.document_id}</span>
                <Badge variant="secondary" className="text-[10px]">#{i + 1}</Badge>
              </div>
              <p className="text-sm text-text-0 line-clamp-2">{chunk.content}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MemoryResultCard({ result, index }: { result: any; index: number }) {
  const { t } = useTranslation();
  const entry = result.entry;
  const typeColors: Record<string, string> = {
    semantic: "#7c5cff",
    episodic: "#f5a524",
    working: "#22d3ee",
    kg: "#8b5cf6",
    procedural: "#34d399",
  };

  return (
    <div className="p-3 rounded-lg border hover:border-[var(--accent)] transition-colors"
         style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Badge variant="secondary" className="text-[10px] shrink-0" style={{ backgroundColor: typeColors[entry.type] + "20" }}>
            #{index}
          </Badge>
          <Badge variant="outline" className="text-[10px] shrink-0 capitalize" style={{ borderColor: typeColors[entry.type] }}>
            {entry.type}
          </Badge>
          <span className="text-[10px] text-text-2 shrink-0">
            {Math.round(result.score * 100)}%
          </span>
        </div>
        <Badge variant="outline" className="text-[10px]">{result.match_type}</Badge>
      </div>
      <p className="text-sm text-text-0 line-clamp-3">{entry.content}</p>
      <div className="flex items-center gap-2 mt-2 text-[10px] text-text-2">
        {entry.tags && entry.tags.size > 0 && (
          <span className="flex gap-1">
            {Array.from(entry.tags).slice(0, 3).map(tag => (
              <Badge key={tag} variant="outline" className="text-[9px] px-1.5 py-0.5">#{tag}</Badge>
            ))}
          </span>
        )}
        {entry.session_id && (
          <span>💬 {entry.session_id.slice(0, 8)}</span>
        )}
      </div>
    </div>
  );
}

function EpisodicSessionCard({ session }: { session: any }) {
  const { t } = useTranslation();
  const formatDate = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleString();
  };

  return (
    <div className="p-3 rounded-lg border hover:border-[var(--accent)] cursor-pointer transition-colors"
         style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: "linear-gradient(135deg, #f5a524, #f97316)" }}>
            <Clock className="h-4 w-4 text-white" />
          </div>
          <div>
            <div className="font-medium truncate max-w-xs" style={{ color: "var(--text-0)" }}>
              {session.session_id}
            </div>
            <div className="text-xs text-text-2">
              {session.message_count} {t("messages")} · {formatDate(session.last_seen)}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Badge variant="outline" className="text-[10px]">
            {session.message_count} msgs
          </Badge>
        </div>
      </div>
    </div>
  );
}