import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { 
  Plus, Minus, RotateCcw, Download, Upload, 
  Trash2, Copy, Settings, Play, Pause,
  Square, GitBranch, Diamond, Circle, 
  ChevronDown, ChevronUp, MoreHorizontal,
  X, Check, AlertTriangle
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/Modal";

export interface WorkflowNode {
  id: string;
  type: "task" | "condition" | "parallel" | "subworkflow" | "start" | "end";
  position: { x: number; y: number };
  data: {
    label: string;
    description?: string;
    config?: Record<string, any>;
    inputs?: string[];
    outputs?: string[];
  };
  selected?: boolean;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: "default" | "conditional" | "parallel";
  label?: string;
  condition?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  viewport: { x: number; y: number; zoom: number };
  createdAt: number;
  updatedAt: number;
  version: number;
}

const NODE_WIDTH = 200;
const NODE_HEIGHT = 80;
const HANDLE_RADIUS = 8;

const NODE_TYPES = [
  { type: "task", label: "Task", icon: Square, color: "#7c5cff", description: "Execute an action or command" },
  { type: "condition", label: "Condition", icon: Diamond, color: "#f5a524", description: "Branch based on condition" },
  { type: "parallel", label: "Parallel", icon: GitBranch, color: "#22d3ee", description: "Run multiple branches simultaneously" },
  { type: "subworkflow", label: "Sub-workflow", icon: Square, color: "#34d399", description: "Call another workflow" },
  { type: "start", label: "Start", icon: Circle, color: "#34d399", description: "Workflow entry point" },
  { type: "end", label: "End", icon: Circle, color: "#f87171", description: "Workflow exit point" },
];

export function WorkflowBuilder() {
  const { t } = useTranslation();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [workflow, setWorkflow] = useState<Workflow>({
    id: "new-workflow",
    name: "Untitled Workflow",
    description: "",
    nodes: [
      { id: "start-1", type: "start", position: { x: 400, y: 100 }, data: { label: "Start" } },
    ],
    edges: [],
    viewport: { x: 0, y: 0, zoom: 1 },
    createdAt: Date.now(),
    updatedAt: Date.now(),
    version: 1,
  });
  
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [connectingFrom, setConnectingFrom] = useState<{ nodeId: string; handle: "source" | "target" } | null>(null);
  const [showNodePalette, setShowNodePalette] = useState(false);
  const [showNodeConfig, setShowNodeConfig] = useState(false);
  const [showWorkflowSettings, setShowWorkflowSettings] = useState(false);
  const [history, setHistory] = useState<Workflow[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [isDirty, setIsDirty] = useState(false);
  
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const isPanningRef = useRef(false);
  const panStartRef = useRef<{ x: number; y: number } | null>(null);
  
  // Save to history
  const saveToHistory = useCallback((newWorkflow: Workflow) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push(newWorkflow);
      return newHistory.slice(-50);
    });
    setHistoryIndex(prev => Math.min(prev + 1, 49));
    setIsDirty(true);
  }, [historyIndex]);
  
  // Update workflow with history
  const updateWorkflow = useCallback((updater: (w: Workflow) => Workflow) => {
    setWorkflow(prev => {
      const updated = updater({ ...prev, updatedAt: Date.now(), version: prev.version + 1 });
      saveToHistory(updated);
      return updated;
    });
  }, [saveToHistory]);
  
  // Canvas rendering
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    
    const { viewport } = workflow;
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);
    
    // Apply viewport transform
    ctx.save();
    ctx.translate(viewport.x, viewport.y);
    ctx.scale(viewport.zoom, viewport.zoom);
    
    // Draw grid
    drawGrid(ctx, rect.width / viewport.zoom, rect.height / viewport.zoom, viewport);
    
    // Draw edges
    workflow.edges.forEach(edge => {
      drawEdge(ctx, edge, workflow.nodes);
    });
    
    // Draw connection in progress
    if (connectingFrom) {
      const sourceNode = workflow.nodes.find(n => n.id === connectingFrom.nodeId);
      if (sourceNode) {
        const sourcePos = getHandlePosition(sourceNode, connectingFrom.handle === "source" ? "source" : "target");
        const mousePos = getMousePosition();
        if (mousePos) {
          ctx.beginPath();
          ctx.moveTo(sourcePos.x, sourcePos.y);
          ctx.bezierCurveTo(
            sourcePos.x + 100, sourcePos.y,
            mousePos.x - 100, mousePos.y,
            mousePos.x, mousePos.y
          );
          ctx.strokeStyle = "var(--accent)";
          ctx.lineWidth = 2;
          ctx.setLineDash([5, 5]);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }
    }
    
    // Draw nodes
    workflow.nodes.forEach(node => {
      drawNode(ctx, node, node.id === selectedNodeId);
    });
    
    ctx.restore();
  }, [workflow, selectedNodeId, connectingFrom]);
  
  function drawGrid(ctx: CanvasRenderingContext2D, width: number, height: number, viewport: Workflow["viewport"]) {
    const gridSize = 20;
    const startX = -viewport.x / viewport.zoom;
    const startY = -viewport.y / viewport.zoom;
    
    ctx.strokeStyle = "rgba(255,255,255,0.02)";
    ctx.lineWidth = 1;
    
    ctx.beginPath();
    for (let x = startX % gridSize; x < width / viewport.zoom + gridSize; x += gridSize) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height / viewport.zoom);
    }
    for (let y = startY % gridSize; y < height / viewport.zoom + gridSize; y += gridSize) {
      ctx.moveTo(0, y);
      ctx.lineTo(width / viewport.zoom, y);
    }
    ctx.stroke();
  }
  
  function drawNode(ctx: CanvasRenderingContext2D, node: WorkflowNode, isSelected: boolean) {
    const { position, type, data } = node;
    const nodeType = NODE_TYPES.find(nt => nt.type === type) || NODE_TYPES[0];
    const x = position.x;
    const y = position.y;
    const w = NODE_WIDTH;
    const h = NODE_HEIGHT;
    const radius = 12;
    
    // Shadow
    ctx.shadowColor = "rgba(0,0,0,0.3)";
    ctx.shadowBlur = 10;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 4;
    
    // Background
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.fillStyle = "var(--bg-2)";
    ctx.fill();
    
    // Border
    ctx.strokeStyle = isSelected ? "var(--accent)" : "var(--border-glass)";
    ctx.lineWidth = isSelected ? 2 : 1;
    ctx.stroke();
    
    // Top accent bar
    const nodeTypeInfo = NODE_TYPES.find(nt => nt.type === type) || NODE_TYPES[0];
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w, y + 4);
    ctx.lineTo(x, y + 4);
    ctx.closePath();
    ctx.fillStyle = nodeTypeInfo.color;
    ctx.fill();
    
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;
    
    // Icon
    const Icon = NODE_TYPES.find(nt => nt.type === type)?.icon || Square;
    // Draw icon placeholder (since we can't render React components on canvas)
    ctx.fillStyle = nodeTypeInfo.color;
    ctx.beginPath();
    ctx.arc(x + 24, y + 24, 10, 0, Math.PI * 2);
    ctx.fill();
    
    // Label
    ctx.fillStyle = "var(--text-0)";
    ctx.font = "500 14px var(--font-body)";
    ctx.textBaseline = "middle";
    ctx.fillText(data.label, x + 50, y + 24);
    
    // Description
    if (data.description) {
      ctx.fillStyle = "var(--text-2)";
      ctx.font = "11px var(--font-body)";
      ctx.fillText(data.description, x + 50, y + 44);
    }
    
    // Selection indicator
    if (isSelected) {
      ctx.strokeStyle = "var(--accent)";
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(x - 2, y - 2, NODE_WIDTH + 4, NODE_HEIGHT + 4);
      ctx.setLineDash([]);
    }
    
    // Handles
    drawHandle(ctx, x, y + h / 2, "source");
    drawHandle(ctx, x + w, y + h / 2, "target");
  }
  
  function drawHandle(ctx: CanvasRenderingContext2D, x: number, y: number, type: "source" | "target") {
    ctx.beginPath();
    ctx.arc(x, y, HANDLE_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = "var(--bg-1)";
    ctx.fill();
    ctx.strokeStyle = "var(--accent)";
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Inner dot
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = "var(--accent)";
    ctx.fill();
  }
  
  function drawEdge(ctx: CanvasRenderingContext2D, edge: WorkflowEdge, nodes: WorkflowNode[]) {
    const sourceNode = nodes.find(n => n.id === edge.source);
    const targetNode = nodes.find(n => n.id === edge.target);
    if (!sourceNode || !targetNode) return;
    
    const sourcePos = getHandlePosition(sourceNode, "source");
    const targetPos = getHandlePosition(targetNode, "target");
    
    const isConditional = edge.type === "conditional";
    const isParallel = edge.type === "parallel";
    
    ctx.beginPath();
    ctx.moveTo(sourcePos.x, sourcePos.y);
    
    const midX = (sourcePos.x + targetPos.x) / 2;
    const midY = (sourcePos.y + targetPos.y) / 2;
    
    if (sourcePos.y === targetPos.y) {
      // Horizontal
      ctx.bezierCurveTo(
        sourcePos.x + 100, sourcePos.y,
        targetPos.x - 100, targetPos.y,
        targetPos.x, targetPos.y
      );
    } else {
      // Curved
      ctx.bezierCurveTo(
        sourcePos.x, midY,
        targetPos.x, midY,
        targetPos.x, targetPos.y
      );
    }
    
    ctx.strokeStyle = "var(--border-glass)";
    ctx.lineWidth = 2;
    
    if (edge.type === "conditional") {
      ctx.setLineDash([8, 4]);
      ctx.strokeStyle = "#f5a524";
    } else if (edge.type === "parallel") {
      ctx.strokeStyle = "#22d3ee";
    }
    
    ctx.stroke();
    ctx.setLineDash([]);
    
    // Arrow head
    drawArrowHead(ctx, sourcePos, targetPos);
    
    // Edge label
    if (edge.label || edge.condition) {
      const midX = (sourcePos.x + targetPos.x) / 2;
      const midY = (sourcePos.y + targetPos.y) / 2;
      ctx.fillStyle = "var(--text-2)";
      ctx.font = "10px var(--font-body)";
      ctx.textAlign = "center";
      ctx.fillText(edge.label || edge.condition || "", midX, midY - 10);
    }
  }
  
  function drawArrowHead(ctx: CanvasRenderingContext2D, from: { x: number; y: number }, to: { x: number; y: number }) {
    const angle = Math.atan2(to.y - from.y, to.x - from.x);
    const headLen = 12;
    
    ctx.beginPath();
    ctx.moveTo(to.x, to.y);
    ctx.lineTo(
      to.x - headLen * Math.cos(angle - Math.PI / 6),
      to.y - headLen * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
      to.x - headLen * Math.cos(angle + Math.PI / 6),
      to.y - headLen * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fillStyle = "var(--border-glass)";
    ctx.fill();
  }
  
  function getHandlePosition(node: WorkflowNode, handle: "source" | "target"): { x: number; y: number } {
    const { x, y } = node.position;
    if (handle === "source") {
      return { x: x + NODE_WIDTH, y: y + NODE_HEIGHT / 2 };
    }
    return { x, y: y + NODE_HEIGHT / 2 };
  }
  
  function getMousePosition(): { x: number; y: number } | null {
    if (!canvasRef.current || !connectingFrom) return null;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const { viewport } = workflow;
    // This is simplified - in real implementation, track mouse position globally
    return null;
  }
  
  // Event handlers
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const { viewport } = workflow;
    const x = (e.clientX - rect.left - viewport.x) / viewport.zoom;
    const y = (e.clientY - rect.top - viewport.y) / viewport.zoom;
    
    // Check if clicked on a node
    let clickedNode = null;
    for (const node of workflow.nodes) {
      if (x >= node.position.x && x <= node.position.x + NODE_WIDTH &&
          y >= node.position.y && y <= node.position.y + NODE_HEIGHT) {
        clickedNode = node;
        break;
      }
    }
    
    if (clickedNode) {
      setSelectedNodeId(clickedNode.id);
      setSelectedEdgeId(null);
    } else {
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
    }
    
    setShowNodePalette(false);
  }, [workflow]);
  
  const handleCanvasMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button !== 0) return; // Only left click
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const { viewport } = workflow;
    const x = (e.clientX - rect.left - viewport.x) / viewport.zoom;
    const y = (e.clientY - rect.top - viewport.y) / viewport.zoom;
    
    // Check node handles
    for (const node of workflow.nodes) {
      const handle = getHandleAtPosition(node, x, y);
      if (handle) {
        setConnectingFrom({ nodeId: node.id, handle: handle });
        return;
      }
    }
    
    // Check node drag
    for (const node of workflow.nodes) {
      if (x >= node.position.x && x <= node.position.x + NODE_WIDTH &&
          y >= node.position.y && y <= node.position.y + NODE_HEIGHT) {
        setDraggingNodeId(node.id);
        dragStartRef.current = { x, y };
        setSelectedNodeId(node.id);
        return;
      }
    }
    
    // Start panning
    isPanningRef.current = true;
    panStartRef.current = { x: e.clientX, y: e.clientY };
  }, [workflow]);
  
  const handleCanvasMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const { viewport } = workflow;
    const x = (e.clientX - rect.left - viewport.x) / viewport.zoom;
    const y = (e.clientY - rect.top - viewport.y) / viewport.zoom;
    
    // Drag node
    if (draggingNodeId) {
      const dragStart = dragStartRef.current;
      if (dragStart) {
        const dx = x - dragStart.x;
        const dy = y - dragStart.y;
        
        updateWorkflow(w => ({
          ...w,
          nodes: w.nodes.map(n => 
            n.id === draggingNodeId 
              ? { ...n, position: { x: n.position.x + dx, y: n.position.y + dy } }
              : n
          )
        }));
        
        dragStartRef.current = { x, y };
      }
      return;
    }
    
    // Pan
    if (isPanningRef.current && panStartRef.current) {
      const dx = e.clientX - panStartRef.current.x;
      const dy = e.clientY - panStartRef.current.y;
      
      updateWorkflow(w => ({
        ...w,
        viewport: {
          ...w.viewport,
          x: w.viewport.x + dx,
          y: w.viewport.y + dy,
        }
      }));
      
      panStartRef.current = { x: e.clientX, y: e.clientY };
    }
  }, [workflow, draggingNodeId, updateWorkflow]);
  
  const handleCanvasMouseUp = useCallback(() => {
    setDraggingNodeId(null);
    dragStartRef.current = null;
    isPanningRef.current = false;
    panStartRef.current = null;
    
    // Handle connection completion
    if (connectingFrom) {
      // In real implementation, check if dropped on valid target
      setConnectingFrom(null);
    }
  }, [connectingFrom]);
  
  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const { viewport } = workflow;
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.1, Math.min(3, viewport.zoom * zoomFactor));
    
    // Zoom towards mouse position
    const worldX = (mouseX - viewport.x) / viewport.zoom;
    const worldY = (mouseY - viewport.y) / viewport.zoom;
    
    const newViewportX = mouseX - worldX * newZoom;
    const newViewportY = mouseY - worldY * newZoom;
    
    updateWorkflow(w => ({
      ...w,
      viewport: {
        x: newViewportX,
        y: newViewportY,
        zoom: newZoom,
      }
    }));
  }, [workflow, updateWorkflow]);
  
  // Add node from palette
  const addNode = useCallback((type: WorkflowNode["type"]) => {
    const centerX = (-workflow.viewport.x + canvasRef.current?.width / 2 / workflow.viewport.zoom) || 400;
    const centerY = (-workflow.viewport.y + canvasRef.current?.height / 2 / workflow.viewport.zoom) || 300;
    
    const nodeType = NODE_TYPES.find(nt => nt.type === type);
    const newNode: WorkflowNode = {
      id: `${type}-${Date.now()}`,
      type,
      position: { x: centerX, y: centerY },
      data: {
        label: NODE_TYPES.find(nt => nt.type === type)?.label || type,
        description: nodeType?.description,
      },
    };
    
    updateWorkflow(w => ({
      ...w,
      nodes: [...w.nodes, newNode],
    }));
    
    setShowNodePalette(false);
  }, [workflow, updateWorkflow]);
  
  // Delete selected
  const deleteSelected = useCallback(() => {
    if (selectedNodeId) {
      updateWorkflow(w => ({
        ...w,
        nodes: w.nodes.filter(n => n.id !== selectedNodeId),
        edges: w.edges.filter(e => e.source !== selectedNodeId && e.target !== selectedNodeId),
      }));
      setSelectedNodeId(null);
    }
    if (selectedEdgeId) {
      updateWorkflow(w => ({
        ...w,
        edges: w.edges.filter(e => e.id !== selectedEdgeId),
      }));
      setSelectedEdgeId(null);
    }
  }, [selectedNodeId, selectedEdgeId, updateWorkflow]);
  
  // Undo/Redo
  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setWorkflow(history[newIndex]);
      setHistoryIndex(newIndex);
    }
  }, [history, historyIndex]);
  
  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      setWorkflow(history[newIndex]);
      setHistoryIndex(newIndex);
    }
  }, [history, historyIndex]);
  
  // Zoom controls
  const zoomIn = useCallback(() => {
    updateWorkflow(w => ({
      ...w,
      viewport: { ...w.viewport, zoom: Math.min(3, w.viewport.zoom * 1.2) }
    }));
  }, [updateWorkflow]);
  
  const zoomOut = useCallback(() => {
    updateWorkflow(w => ({
      ...w,
      viewport: { ...w.viewport, zoom: Math.max(0.1, w.viewport.zoom / 1.2) }
    }));
  }, [updateWorkflow]);
  
  const resetView = useCallback(() => {
    updateWorkflow(w => ({
      ...w,
      viewport: { x: 0, y: 0, zoom: 1 }
    }));
  }, [updateWorkflow]);
  
  // Initialize canvas size
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (canvas && container) {
      const resize = () => {
        const rect = container.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
        renderCanvas();
      };
      resize();
      window.addEventListener("resize", resize);
      return () => window.removeEventListener("resize", resize);
    }
  }, [renderCanvas]);
  
  // Render loop
  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);
  
  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        if (e.shiftKey) redo(); else undo();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        // Save workflow
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        deleteSelected();
      }
      if (e.key === "Escape") {
        setShowNodePalette(false);
        setShowNodeConfig(false);
        setShowWorkflowSettings(false);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [undo, redo, deleteSelected]);
  
  return (
    <div className="flex flex-col h-full" ref={containerRef}>
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-white/5 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="font-medium text-sm text-white">{workflow.name}</h2>
          {isDirty && <Badge variant="secondary" className="text-[10px]">{t("workflow.unsaved")}</Badge>}
        </div>
        
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={undo} disabled={historyIndex <= 0} title={t("workflow.undo")}>
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={redo} disabled={historyIndex >= history.length - 1} title={t("workflow.redo")}>
            <RotateCcw className="h-4 w-4" style={{ transform: "rotate(180deg)" }} />
          </Button>
          
          <div className="w-px h-6 bg-white/10 mx-1" />
          
          <Button variant="ghost" size="sm" onClick={zoomOut} title={t("workflow.zoom_out")}>
            <Minus className="h-4 w-4" />
          </Button>
          <span className="px-2 text-xs text-text-2" style={{ minWidth: "40px", textAlign: "center" }}>
            {Math.round(workflow.viewport.zoom * 100)}%
          </span>
          <Button variant="ghost" size="sm" onClick={zoomIn} title={t("workflow.zoom_in")}>
            <Plus className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={resetView} title={t("workflow.reset_view")}>
            <RotateCcw className="h-4 w-4" />
          </Button>
          
          <div className="w-px h-6 bg-white/10 mx-1" />
          
          <Button variant="outline" size="sm" onClick={() => setShowNodePalette(true)}>
            <Plus className="h-4 w-4 mr-1" /> {t("workflow.add_node")}
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowWorkflowSettings(true)}>
            <Settings className="h-4 w-4 mr-1" /> {t("workflow.settings")}
          </Button>
          <Button variant="primary" size="sm" onClick={() => {}}>
            <Play className="h-4 w-4 mr-1" /> {t("workflow.run")}
          </Button>
        </div>
      </div>
      
      {/* Canvas */}
      <div className="flex-1 relative overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-full cursor-crosshair"
          onClick={handleCanvasClick}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
          onWheel={handleWheel}
        />
        
        {/* Mini-map placeholder */}
        <div className="absolute bottom-4 right-4 w-48 h-32 bg-black/50 rounded-lg border border-white/10 p-2">
          <div className="text-[10px] text-text-2 text-center pt-2">{t("workflow.minimap")}</div>
        </div>
      </div>
      
      {/* Status bar */}
      <div className="flex items-center justify-between p-2 border-t border-white/5 text-xs text-text-2">
        <span>{workflow.nodes.length} nodes, {workflow.edges.length} edges</span>
        <span>v{workflow.version}</span>
      </div>
      
      {/* Node Palette Modal */}
      <Modal
        isOpen={showNodePalette}
        onClose={() => setShowNodePalette(false)}
        title={t("workflow.add_node")}
        size="lg"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 p-2">
          {NODE_TYPES.map(nodeType => {
            const Icon = nodeType.icon;
            return (
              <button
                key={nodeType.type}
                onClick={() => addNode(nodeType.type)}
                className={cn(
                  "p-4 rounded-xl border text-left transition-colors hover:border-[var(--accent)]",
                  "flex flex-col items-center gap-2"
                )}
                style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}
              >
                <div className="w-12 h-12 rounded-lg flex items-center justify-center" 
                     style={{ background: `color-mix(in srgb, ${nodeType.color} 20%, transparent)` }}>
                  <Icon className="h-6 w-6" style={{ color: nodeType.color }} />
                </div>
                <span className="font-medium text-sm" style={{ color: "var(--text-0)" }}>
                  {nodeType.label}
                </span>
                <span className="text-[10px] text-center" style={{ color: "var(--text-2)" }}>
                  {nodeType.description}
                </span>
              </button>
            );
          })}
        </div>
      </Modal>
      
      {/* Node Config Modal */}
      <Modal
        isOpen={showNodeConfig && !!selectedNodeId}
        onClose={() => { setShowNodeConfig(false); setSelectedNodeId(null); }}
        title={t("workflow.node_config")}
        size="md"
      >
        {selectedNodeId && (
          <NodeConfigPanel
            node={workflow.nodes.find(n => n.id === selectedNodeId)!}
            onSave={(data) => {
              updateWorkflow(w => ({
                ...w,
                nodes: w.nodes.map(n => 
                  n.id === selectedNodeId ? { ...n, data: { ...n.data, ...data } } : n
                )
              }));
              setShowNodeConfig(false);
              setSelectedNodeId(null);
            }}
            onClose={() => { setShowNodeConfig(false); setSelectedNodeId(null); }}
          />
        )}
      </Modal>
      
      {/* Workflow Settings Modal */}
      <Modal
        isOpen={showWorkflowSettings}
        onClose={() => setShowWorkflowSettings(false)}
        title={t("workflow.settings")}
        size="md"
      >
        <WorkflowSettingsPanel
          workflow={workflow}
          onSave={(data) => {
            updateWorkflow(w => ({ ...w, ...data }));
            setShowWorkflowSettings(false);
          }}
          onClose={() => setShowWorkflowSettings(false)}
        />
      </Modal>
    </div>
  );
}

// Helper components
function getHandleAtPosition(node: WorkflowNode, x: number, y: number): "source" | "target" | null {
  const { position } = node;
  const sourceHandle = { x: position.x + NODE_WIDTH, y: position.y + NODE_HEIGHT / 2 };
  const targetHandle = { x: position.x, y: position.y + NODE_HEIGHT / 2 };
  
  const dist = (a: { x: number; y: number }, b: { x: number; y: number }) => 
    Math.hypot(a.x - b.x, a.y - b.y);
  
  if (dist({ x, y }, { x: position.x + NODE_WIDTH, y: position.y + NODE_HEIGHT / 2 }) < HANDLE_RADIUS * 2) {
    return "source";
  }
  if (dist({ x, y }, { x: position.x, y: position.y + NODE_HEIGHT / 2 }) < HANDLE_RADIUS * 2) {
    return "target";
  }
  return null;
}

function NodeConfigPanel({ node, onSave, onClose }: { node: WorkflowNode; onSave: (data: Partial<WorkflowNode["data"]>) => void; onClose: () => void }) {
  const { t } = useTranslation();
  const [label, setLabel] = useState(node.data.label);
  const [description, setDescription] = useState(node.data.description || "");
  
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: "var(--text-0)" }}>
          {t("workflow.node_label")}
        </label>
        <input
          value={label}
          onChange={e => setLabel(e.target.value)}
          className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
          placeholder={t("workflow.node_label_placeholder")}
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: "var(--text-0)" }}>
          {t("workflow.node_description")}
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={3}
          className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
          placeholder={t("workflow.node_description_placeholder")}
        />
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onClose}>{t("cancel")}</Button>
        <Button onClick={() => onSave({ label, description })}>{t("save")}</Button>
      </div>
    </div>
  );
}

function WorkflowSettingsPanel({ workflow, onSave, onClose }: { workflow: Workflow; onSave: (data: Partial<Workflow>) => void; onClose: () => void }) {
  const { t } = useTranslation();
  const [name, setName] = useState(workflow.name);
  const [description, setDescription] = useState(workflow.description || "");
  
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: "var(--text-0)" }}>
          {t("workflow.name")}
        </label>
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: "var(--text-0)" }}>
          {t("workflow.description")}
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={3}
          className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
        />
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onClose}>{t("cancel")}</Button>
        <Button onClick={() => onSave({ name, description })}>{t("save")}</Button>
      </div>
    </div>
  );
}

export { NODE_TYPES };