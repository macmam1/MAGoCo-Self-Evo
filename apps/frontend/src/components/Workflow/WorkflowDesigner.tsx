import { useState, useCallback } from "react";
import ReactFlow, {
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  Connection
} from "reactflow";
import "reactflow/dist/style.css";
import { Plus, Play, Save, Cpu, Database, Send, Zap } from "lucide-react";

const initialNodes: Node[] = [
  {
    id: "1",
    data: { label: "Trigger: Telegram Message" },
    position: { x: 100, y: 100 },
    style: { background: "#1f1f2e", color: "#fff", border: "1px solid #6366f1", borderRadius: "8px", padding: "12px" }
  },
  {
    id: "2",
    data: { label: "Agent: ReAct Coordinator" },
    position: { x: 350, y: 100 },
    style: { background: "#1f1f2e", color: "#fff", border: "1px solid #10b981", borderRadius: "8px", padding: "12px" }
  },
  {
    id: "3",
    data: { label: "Tool: Python Execution Sandbox" },
    position: { x: 600, y: 50 },
    style: { background: "#1f1f2e", color: "#fff", border: "1px solid #f59e0b", borderRadius: "8px", padding: "12px" }
  },
  {
    id: "4",
    data: { label: "Action: Reply to Telegram" },
    position: { x: 600, y: 180 },
    style: { background: "#1f1f2e", color: "#fff", border: "1px solid #ec4899", borderRadius: "8px", padding: "12px" }
  }
];

const initialEdges: Edge[] = [
  { id: "e1-2", source: "1", target: "2", animated: true, style: { stroke: "#6366f1" } },
  { id: "e2-3", source: "2", target: "3", animated: true, style: { stroke: "#10b981" } },
  { id: "e2-4", source: "2", target: "4", animated: true, style: { stroke: "#10b981" } }
];

export function WorkflowDesigner() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    []
  );

  return (
    <div className="flex h-full w-full bg-[#0a0a0f] text-slate-200">
      {/* Sidebar Tools */}
      <div className="w-64 border-r border-[#1f1f2e] bg-[#0f0f17] p-4 flex flex-col gap-4">
        <h3 className="font-semibold text-sm tracking-wide text-slate-300">Nodes Library</h3>
        <div className="space-y-2">
          <div className="p-3 bg-[#15151f] hover:bg-[#1f1f2e] border border-[#2d2d3d] rounded-lg cursor-pointer transition-all flex items-center gap-2">
            <Zap className="h-4 w-4 text-indigo-400" />
            <span className="text-xs font-medium">Trigger Node</span>
          </div>
          <div className="p-3 bg-[#15151f] hover:bg-[#1f1f2e] border border-[#2d2d3d] rounded-lg cursor-pointer transition-all flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-medium">Agent Node</span>
          </div>
          <div className="p-3 bg-[#15151f] hover:bg-[#1f1f2e] border border-[#2d2d3d] rounded-lg cursor-pointer transition-all flex items-center gap-2">
            <Database className="h-4 w-4 text-amber-400" />
            <span className="text-xs font-medium">Memory/Tool Node</span>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 flex flex-col relative bg-[#0a0a0f]">
        <div className="p-3 border-b border-[#1f1f2e] bg-[#0f0f17] flex items-center justify-between z-10">
          <span className="text-sm font-semibold text-indigo-400">Workflow Designer</span>
          <div className="flex gap-2">
            <button className="flex items-center gap-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition-all">
              <Play className="h-3.5 w-3.5" />
              Run Test
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-all">
              <Save className="h-3.5 w-3.5" />
              Save Workflow
            </button>
          </div>
        </div>
        <div className="flex-1 w-full h-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
          >
            <Background color="#1f1f2e" gap={16} />
            <Controls />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
