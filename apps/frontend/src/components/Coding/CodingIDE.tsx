import { useState } from "react";
import Editor, { DiffEditor } from "@monaco-editor/react";
import { Folder, FileText, Play, Check, RefreshCw, GitCompare, Save, FileCode } from "lucide-react";

interface FileNode {
  name: string;
  type: "file" | "folder";
  content?: string;
  children?: FileNode[];
}

export function CodingIDE() {
  const [selectedFile, setSelectedFile] = useState<string>("app/main.py");
  const [showDiff, setShowDiff] = useState<boolean>(false);
  
  // Dummy file structure for mockup, we'll connect this to DB/backend file API later
  const files: FileNode[] = [
    {
      name: "app",
      type: "folder",
      children: [
        {
          name: "main.py",
          type: "file",
          content: '"""FastAPI Main Entry"""\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef read_root():\n    return {"status": "ok"}\n'
        },
        {
          name: "config.py",
          type: "file",
          content: 'class Settings:\n    DATABASE_URL = "sqlite:///./test.db"\nsettings = Settings()\n'
        }
      ]
    },
    {
      name: "README.md",
      type: "file",
      content: "# MAGoCo-Self-Evo\nAutonomous Agent Workspace.\n"
    }
  ];

  const fileContents: Record<string, string> = {
    "app/main.py": '"""FastAPI Main Entry"""\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef read_root():\n    return {"status": "ok"}\n',
    "app/config.py": 'class Settings:\n    DATABASE_URL = "sqlite:///./test.db"\nsettings = Settings()\n',
    "README.md": "# MAGoCo-Self-Evo\nAutonomous Agent Workspace.\n"
  };

  const modifiedContents: Record<string, string> = {
    "app/main.py": '"""FastAPI Main Entry"""\nfrom fastapi import FastAPI\nfrom app.db import init_db\n\napp = FastAPI()\n\n@app.on_event("startup")\nasync def startup():\n    await init_db()\n\n@app.get("/")\ndef read_root():\n    return {"status": "ok", "version": "1.0.0"}\n',
    "app/config.py": 'class Settings:\n    DATABASE_URL = "sqlite:///./test.db"\n    DEBUG = True\nsettings = Settings()\n',
    "README.md": "# MAGoCo-Self-Evo\nAutonomous Agent Workspace with real-time IDE.\n"
  };

  const [code, setCode] = useState<string>(fileContents[selectedFile] || "");

  const handleFileClick = (path: string) => {
    setSelectedFile(path);
    setCode(fileContents[path] || "");
  };

  return (
    <div className="flex h-full w-full bg-[#0a0a0f] text-slate-200 overflow-hidden">
      {/* 1. File Tree Panel (Left) */}
      <div className="w-64 border-r border-[#1f1f2e] bg-[#0f0f17] flex flex-col">
        <div className="p-4 border-b border-[#1f1f2e] flex items-center justify-between">
          <span className="font-semibold text-sm tracking-wide">Workspace</span>
          <RefreshCw className="h-4 w-4 text-slate-400 cursor-pointer hover:text-white transition-colors" />
        </div>
        <div className="flex-1 p-2 overflow-y-auto space-y-1">
          {files.map((node, idx) => (
            <div key={idx}>
              {node.type === "folder" ? (
                <div>
                  <div className="flex items-center gap-2 px-2 py-1.5 text-slate-400 font-medium text-sm">
                    <Folder className="h-4 w-4 text-amber-500" />
                    <span>{node.name}</span>
                  </div>
                  <div className="pl-4 space-y-1">
                    {node.children?.map((child, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => handleFileClick(`${node.name}/${child.name}`)}
                        className={`w-full flex items-center gap-2 px-2 py-1 text-sm rounded transition-all duration-200 ${
                          selectedFile === `${node.name}/${child.name}`
                            ? "bg-[#1f1f2e] text-indigo-400 border-l-2 border-indigo-500"
                            : "text-slate-400 hover:bg-[#15151f] hover:text-slate-200"
                        }`}
                      >
                        <FileText className="h-3.5 w-3.5" />
                        <span>{child.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => handleFileClick(node.name)}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded transition-all duration-200 ${
                    selectedFile === node.name
                      ? "bg-[#1f1f2e] text-indigo-400 border-l-2 border-indigo-500"
                      : "text-slate-400 hover:bg-[#15151f] hover:text-slate-200"
                  }`}
                >
                  <FileText className="h-4 w-4 text-indigo-500" />
                  <span>{node.name}</span>
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 2. Editor Panel (Center) */}
      <div className="flex-1 flex flex-col bg-[#0d0d13]">
        <div className="p-3 border-b border-[#1f1f2e] bg-[#0f0f17] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileCode className="h-4 w-4 text-indigo-400" />
            <span className="text-sm font-semibold">{selectedFile}</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowDiff(!showDiff)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold border transition-all ${
                showDiff
                  ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400"
                  : "border-[#1f1f2e] text-slate-400 hover:text-slate-200"
              }`}
            >
              <GitCompare className="h-3.5 w-3.5" />
              <span>Diff View</span>
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 transition-all">
              <Save className="h-3.5 w-3.5" />
              <span>Save</span>
            </button>
          </div>
        </div>
        <div className="flex-1 relative overflow-hidden">
          {showDiff ? (
            <DiffEditor
              original={fileContents[selectedFile] || ""}
              modified={modifiedContents[selectedFile] || ""}
              language={selectedFile.endsWith(".py") ? "python" : "markdown"}
              theme="vs-dark"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 14,
              }}
            />
          ) : (
            <Editor
              value={code}
              onChange={(value) => setCode(value || "")}
              language={selectedFile.endsWith(".py") ? "python" : "markdown"}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: "on",
                roundedSelection: false,
                scrollBeyondLastLine: false,
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
