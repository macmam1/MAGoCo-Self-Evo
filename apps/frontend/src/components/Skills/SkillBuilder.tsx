import { useState, useEffect } from "react";
import { X, Plus, Minus, Save, FileCode, Download, Upload } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Button, Badge, Card, CardHeader, CardTitle, CardContent, Input, Textarea, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";

const semverValid = (version: string): boolean => {
  const semverRegex = /^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$/;
  return semverRegex.test(version);
};

interface SkillBuilderProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialSkill?: any;
}

export function SkillBuilder({ isOpen, onClose, onSuccess, initialSkill }: SkillBuilderProps) {
  const { t } = useTranslation();
  const [activeStep, setActiveStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [formData, setFormData] = useState({
    name: initialSkill?.name || "",
    display_name: initialSkill?.display_name || "",
    description: initialSkill?.description || "",
    version: initialSkill?.version || "1.0.0",
    category: initialSkill?.category || "custom",
    type: initialSkill?.type || "function",
    tags: initialSkill?.tags ? Array.from(initialSkill.tags) : [],
    newTag: "",
    author: initialSkill?.author || "",
    author_email: initialSkill?.author_email || "",
    organization: initialSkill?.organization || "",
    license: initialSkill?.license || "MIT",
    homepage: initialSkill?.homepage || "",
    repository: initialSkill?.repository || "",
    entry_point: initialSkill?.entry_point || "main",
    code_path: initialSkill?.code_path || "skill.py",
    requirements: initialSkill?.requirements || [],
    newRequirement: "",
    system_requirements: initialSkill?.system_requirements || [],
    execution_mode: initialSkill?.execution_mode || "sync",
    timeout: initialSkill?.timeout || 30,
    max_memory_mb: initialSkill?.max_memory_mb || 512,
    max_cpu_percent: initialSkill?.max_cpu_percent || 50,
    security_level: initialSkill?.security_level || "restricted",
    allowed_domains: initialSkill?.allowed_domains || [],
    newDomain: "",
    allowed_commands: initialSkill?.allowed_commands || [],
    newCommand: "",
    parameters: initialSkill?.parameters || [],
    returns: initialSkill?.returns || { type: "any", description: "" },
    dependencies: initialSkill?.dependencies || [],
    newDependency: { skill_id: "", version_spec: ">=", required: true },
    tests: initialSkill?.tests || [],
    examples: initialSkill?.examples || [],
    min_core_version: initialSkill?.min_core_version || "0.3.0",
    compatible_platforms: initialSkill?.compatible_platforms || ["linux", "macos", "windows"],
    price: initialSkill?.price || 0,
    currency: initialSkill?.currency || "USD",
    is_public: initialSkill?.is_public !== false,
    featured: initialSkill?.featured || false,
    code_content: initialSkill?.code_content || "",
  });

  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (step === 1) {
      if (!formData.name.trim()) newErrors.name = t("skills.name_required");
      if (!formData.display_name.trim()) newErrors.display_name = t("skills.display_name_required");
      if (!formData.description.trim()) newErrors.description = t("skills.description_required");
      if (!formData.author.trim()) newErrors.author = t("skills.author_required");
      if (!semverValid(formData.version)) newErrors.version = t("skills.invalid_version");
    }
    
    if (step === 2) {
      if (!formData.entry_point.trim()) newErrors.entry_point = t("skills.entry_point_required");
      if (!formData.code_path.trim()) newErrors.code_path = t("skills.code_path_required");
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateStep(1) || !validateStep(2) || !validateStep(3)) return;
    
    setLoading(true);
    try {
      const response = await fetch("/api/v1/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        onSuccess();
        onClose();
      } else {
        const error = await response.json();
        setErrors({ submit: error.detail || t("skills.create_failed") });
      }
    } catch (error) {
      setErrors({ submit: t("skills.create_error") });
    } finally {
      setLoading(false);
    }
  };

  const nextStep = () => {
    if (validateStep(activeStep)) {
      setActiveStep(prev => Math.min(prev + 1, 4));
    }
  };

  const prevStep = () => {
    setActiveStep(prev => Math.max(prev - 1, 1));
  };

  const addTag = () => {
    if (formData.newTag.trim() && !formData.tags.includes(formData.newTag.trim())) {
      setFormData(prev => ({ ...prev, tags: [...prev.tags, prev.newTag.trim()], newTag: "" }));
    }
  };

  const removeTag = (tag: string) => {
    setFormData(prev => ({ ...prev, tags: prev.tags.filter(t => t !== tag) }));
  };

  const addRequirement = () => {
    if (formData.newRequirement.trim() && !formData.requirements.includes(formData.newRequirement.trim())) {
      setFormData(prev => ({ ...prev, requirements: [...prev.requirements, prev.newRequirement.trim()], newRequirement: "" }));
    }
  };

  const removeRequirement = (req: string) => {
    setFormData(prev => ({ ...prev, requirements: prev.requirements.filter(r => r !== req) }));
  };

  const addDomain = () => {
    if (formData.newDomain.trim() && !formData.allowed_domains.includes(formData.newDomain.trim())) {
      setFormData(prev => ({ ...prev, allowed_domains: [...prev.allowed_domains, prev.newDomain.trim()], newDomain: "" }));
    }
  };

  const removeDomain = (domain: string) => {
    setFormData(prev => ({ ...prev, allowed_domains: prev.allowed_domains.filter(d => d !== domain) }));
  };

  const addCommand = () => {
    if (formData.newCommand.trim() && !formData.allowed_commands.includes(formData.newCommand.trim())) {
      setFormData(prev => ({ ...prev, allowed_commands: [...prev.allowed_commands, prev.newCommand.trim()], newCommand: "" }));
    }
  };

  const removeCommand = (cmd: string) => {
    setFormData(prev => ({ ...prev, allowed_commands: prev.allowed_commands.filter(c => c !== cmd) }));
  };

  const addDependency = () => {
    if (formData.newDependency.skill_id.trim()) {
      setFormData(prev => ({
        ...prev,
        dependencies: [...prev.dependencies, { ...prev.newDependency }],
        newDependency: { skill_id: "", version_spec: ">=", required: true },
      }));
    }
  };

  const removeDependency = (index: number) => {
    setFormData(prev => ({ ...prev, dependencies: prev.dependencies.filter((_, i) => i !== index) }));
  };

  const addParameter = () => {
    setFormData(prev => ({
      ...prev,
      parameters: [...prev.parameters, {
        name: "",
        type: "string",
        description: "",
        required: true,
        default: null,
      }],
    }));
  };

  const removeParameter = (index: number) => {
    setFormData(prev => ({ ...prev, parameters: prev.parameters.filter((_, i) => i !== index) }));
  };

  const updateParameter = (index: number, field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      parameters: prev.parameters.map((p, i) => i === index ? { ...p, [field]: value } : p),
    }));
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialSkill ? t("skills.edit_skill") : t("skills.create_skill")}
      size="xl"
    >
      <div className="max-h-[85vh] overflow-y-auto">
        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-6">
          {[1, 2, 3, 4].map((step) => (
            <div key={step} className="flex items-center">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                  activeStep >= step
                    ? "bg-[var(--accent)] text-white"
                    : "bg-white/10 text-text-2"
                )}
              >
                {step}
              </div>
              {step < 4 && (
                <div
                  className={cn(
                    "w-16 h-0.5 mx-2",
                    activeStep > step ? "bg-[var(--accent)]" : "bg-white/10"
                  )}
                />
              )}
            ))}
          </div>

          {/* Step 1: Basic Info */}
          {activeStep === 1 && (
            <div className="space-y-4">
              <h3 className="font-medium">{t("skills.basic_info")}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.name")} *</label>
                  <input
                    value={formData.name}
                    onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className={cn("w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary", errors.name && "border-red-500")}
                    placeholder="my-awesome-skill"
                  />
                  {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.display_name")} *</label>
                  <input
                    value={formData.display_name}
                    onChange={e => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
                    className={cn("w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary", errors.display_name && "border-red-500")}
                    placeholder="My Awesome Skill"
                  />
                  {errors.display_name && <p className="text-red-400 text-xs mt-1">{errors.display_name}</p>}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t("skills.version")} *</label>
                <input
                  value={formData.version}
                  onChange={e => setFormData(prev => ({ ...prev, version: e.target.value }))}
                  className={cn("w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary", errors.version && "border-red-500")}
                  placeholder="1.0.0"
                />
                {errors.version && <p className="text-red-400 text-xs mt-1">{errors.version}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t("skills.description")} *</label>
                <textarea
                  value={formData.description}
                  onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  rows={3}
                  className={cn("w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary", errors.description && "border-red-500")}
                  placeholder={t("skills.description_placeholder")}
                />
                {errors.description && <p className="text-red-400 text-xs mt-1">{errors.description}</p>}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.author")} *</label>
                  <input
                    value={formData.author}
                    onChange={e => setFormData(prev => ({ ...prev, author: e.target.value }))}
                    className={cn("w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary", errors.author && "border-red-500")}
                  />
                  {errors.author && <p className="text-red-400 text-xs mt-1">{errors.author}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.author_email")}</label>
                  <input
                    value={formData.author_email}
                    onChange={e => setFormData(prev => ({ ...prev, author_email: e.target.value }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.organization")}</label>
                  <input
                    value={formData.organization}
                    onChange={e => setFormData(prev => ({ ...prev, organization: e.target.value }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.license")}</label>
                  <input
                    value={formData.license}
                    onChange={e => setFormData(prev => ({ ...prev, license: e.target.value }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.category")}</label>
                  <select
                    value={formData.category}
                    onChange={e => setFormData(prev => ({ ...prev, category: e.target.value }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  >
                    <option value="automation">Automation</option>
                    <option value="coding">Coding</option>
                    <option value="data_processing">Data Processing</option>
                    <option value="web_scraping">Web Scraping</option>
                    <option value="api_integration">API Integration</option>
                    <option value="file_operations">File Operations</option>
                    <option value="system_admin">System Admin</option>
                    <option value="ai_ml">AI/ML</option>
                    <option value="communication">Communication</option>
                    <option value="productivity">Productivity</option>
                    <option value="development">Development</option>
                    <option value="security">Security</option>
                    <option value="monitoring">Monitoring</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Technical Config */}
          {activeStep === 2 && (
            <div className="space-y-4">
              <h3 className="font-medium">{t("skills.technical_config")}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.type")}</label>
                  <select
                    value={formData.type}
                    onChange={e => setFormData(prev => ({ ...prev, type: e.target.value }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  >
                    <option value="function">Function</option>
                    <option value="workflow">Workflow</option>
                    <option value="agent">Agent</option>
                    <option value="template">Template</option>
                    <option value="prompt">Prompt</option>
                    <option value="tool">Tool</option>
                    <option value="chain">Chain</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.entry_point")} *</label>
                  <input
                    value={formData.entry_point}
                    onChange={e => setFormData(prev => ({ ...prev, entry_point: e.target.value }))}
                    className={cn("w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary", errors.entry_point && "border-red-500")}
                    placeholder="main"
                  />
                  {errors.entry_point && <p className="text-red-400 text-xs mt-1">{errors.entry_point}</p>}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.code_path")} *</label>
                  <input
                    value={formData.code_path}
                    onChange={e => setFormData(prev => ({ ...prev, code_path: e.target.value }))}
                    className={cn("w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary", errors.code_path && "border-red-500")}
                    placeholder="skill.py"
                  />
                  {errors.code_path && <p className="text-red-400 text-xs mt-1">{errors.code_path}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.execution_mode")}</label>
                  <select
                    value={formData.execution_mode}
                    onChange={e => setFormData(prev => ({ ...prev, execution_mode: e.target.value }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  >
                    <option value="sync">Sync</option>
                    <option value="async">Async</option>
                    <option value="streaming">Streaming</option>
                    <option value="batch">Batch</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.timeout")} (s)</label>
                  <input
                    type="number"
                    value={formData.timeout}
                    onChange={e => setFormData(prev => ({ ...prev, timeout: parseFloat(e.target.value) }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    min="1"
                    max="3600"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.max_memory_mb")}</label>
                  <input
                    type="number"
                    value={formData.max_memory_mb}
                    onChange={e => setFormData(prev => ({ ...prev, max_memory_mb: parseInt(e.target.value) }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    min="64"
                    max="8192"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.max_cpu_percent")}</label>
                  <input
                    type="number"
                    value={formData.max_cpu_percent}
                    onChange={e => setFormData(prev => ({ ...prev, max_cpu_percent: parseInt(e.target.value) }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                    min="1"
                    max="100"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.security_level")}</label>
                  <select
                    value={formData.security_level}
                    onChange={e => setFormData(prev => ({ ...prev, security_level: e.target.value }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  >
                    <option value="safe">Safe (No network, no FS, no subprocess)</option>
                    <option value="restricted">Restricted (Limited network, FS, no subprocess)</option>
                    <option value="standard">Standard (Network, FS, limited subprocess)</option>
                    <option value="elevated">Elevated (Full access except admin)</option>
                    <option value="full">Full (Admin only)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">{t("skills.timeout")}</label>
                  <input
                    type="number"
                    value={formData.timeout}
                    onChange={e => setFormData(prev => ({ ...prev, timeout: parseFloat(e.target.value) }))}
                    className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Interface & Dependencies */}
          {activeStep === 3 && (
            <div className="space-y-6">
              <h3 className="font-medium">{t("skills.interface_dependencies")}</h3>
              
              {/* Parameters */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">{t("skills.parameters")}</h4>
                  <Button variant="outline" size="sm" onClick={addParameter}>
                    <Plus className="h-4 w-4 mr-1" /> {t("add_parameter")}
                  </Button>
                </div>
                <div className="space-y-3">
                  {formData.parameters.map((param: any, i: number) => (
                    <div key={i} className="p-4 rounded-lg border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="font-medium">{t("parameter")} #{i + 1}</h5>
                        <button onClick={() => removeParameter(i)} className="text-red-400 hover:text-red-300">×</button>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-sm font-medium mb-1">{t("name")}</label>
                          <input
                            value={param.name}
                            onChange={e => updateParameter(i, "name", e.target.value)}
                            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                            placeholder="param_name"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">{t("type")}</label>
                          <select
                            value={param.type}
                            onChange={e => updateParameter(i, "type", e.target.value)}
                            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                          >
                            <option value="string">string</option>
                            <option value="integer">integer</option>
                            <option value="float">float</option>
                            <option value="boolean">boolean</option>
                            <option value="object">object</option>
                            <option value="array">array</option>
                            <option value="file">file</option>
                          </select>
                        </div>
                        <div className="md:col-span-2">
                          <label className="block text-sm font-medium mb-1">{t("description")}</label>
                          <input
                            value={param.description}
                            onChange={e => updateParameter(i, "description", e.target.value)}
                            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">{t("required")}</label>
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={param.required}
                              onChange={e => updateParameter(i, "required", e.target.checked)}
                              className="rounded border-white/20"
                            />
                            <span className="text-sm">{t("required")}</span>
                          </label>
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">{t("default")}</label>
                          <input
                            value={param.default ?? ""}
                            onChange={e => updateParameter(i, "default", e.target.value)}
                            className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Returns */}
                  <div className="pt-4 border-t border-white/5">
                    <h4 className="font-medium mb-3">{t("skills.returns")}</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">{t("return_type")}</label>
                        <input
                          value={formData.returns?.type || "any"}
                          onChange={e => setFormData(prev => ({ ...prev, returns: { ...prev.returns, type: e.target.value } }))}
                          className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">{t("return_description")}</label>
                        <input
                          value={formData.returns?.description || ""}
                          onChange={e => setFormData(prev => ({ ...prev, returns: { ...prev.returns, description: e.target.value } }))}
                          className="w-full bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Dependencies */}
                  <div className="pt-4 border-t border-white/5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">{t("skills.dependencies")}</h4>
                      <Button variant="outline" size="sm" onClick={addDependency}>
                        <Plus className="h-4 w-4 mr-1" /> {t("add_dependency")}
                      </Button>
                    </div>
                    <div className="space-y-3">
                      {formData.dependencies.map((dep: any, i: number) => (
                        <div key={i} className="flex gap-2 p-3 rounded-lg border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                          <input
                            value={dep.skill_id}
                            onChange={e => setFormData(prev => ({ ...prev, dependencies: prev.dependencies.map((d, j) => j === i ? { ...d, skill_id: e.target.value } : d) }))}
                            placeholder="skill-id"
                            className="flex-1 bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                          />
                          <input
                            value={dep.version_spec}
                            onChange={e => setFormData(prev => ({ ...prev, dependencies: prev.dependencies.map((d, j) => j === i ? { ...d, version_spec: e.target.value } : d) }))}
                            placeholder=">=1.0.0"
                            className="w-32 bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                          />
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={dep.required}
                              onChange={e => setFormData(prev => ({ ...prev, dependencies: prev.dependencies.map((d, j) => j === i ? { ...d, required: e.target.checked } : d) }))}
                              className="rounded border-white/20"
                            />
                            <span className="text-sm">{t("required")}</span>
                          </label>
                          <button onClick={() => removeDependency(i)} className="text-red-400 hover:text-red-300">×</button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Code & Publish */}
          {activeStep === 4 && (
            <div className="space-y-6">
              <h3 className="font-medium">{t("skills.code_publish")}</h3>
              
              <div className="space-y-4">
                <label className="block text-sm font-medium mb-1">{t("skills.code_editor")}</label>
                <textarea
                  value={formData.code_content}
                  onChange={e => setFormData(prev => ({ ...prev, code_content: e.target.value }))}
                  rows={20}
                  className="w-full bg-gray-900/50 border border-white/10 rounded-lg px-4 py-3 font-mono text-sm focus:ring-2 focus:ring-primary resize-none"
                  placeholder="# Enter your skill code here\ndef main(input_data):\n    # Your skill logic here\n    return {\"result\": \"success\"}"
                  spellCheck={false}
                />
              </div>

              <div className="flex items-center gap-4 p-4 rounded-xl border" style={{ background: "var(--bg-1)", borderColor: "var(--border-glass)" }}>
                <div className="flex-1">
                  <h4 className="font-medium">{t("skills.publish_options")}</h4>
                  <div className="flex items-center gap-4 mt-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.is_public}
                        onChange={e => setFormData(prev => ({ ...prev, is_public: e.target.checked }))}
                        className="rounded border-white/20"
                      />
                      <span>{t("skills.is_public")}</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.featured}
                        onChange={e => setFormData(prev => ({ ...prev, featured: e.target.checked }))}
                        className="rounded border-white/20"
                      />
                      <span>{t("skills.featured")}</span>
                    </label>
                    <div>
                      <label className="block text-sm font-medium mb-1">{t("skills.price")}</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={formData.price}
                          onChange={e => setFormData(prev => ({ ...prev, price: parseFloat(e.target.value) }))}
                          className="w-24 bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                          min="0"
                          step="0.01"
                        />
                        <select
                          value={formData.currency}
                          onChange={e => setFormData(prev => ({ ...prev, currency: e.target.value }))}
                          className="w-24 bg-gray-800/50 border border-white/10 rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary"
                        >
                          <option value="USD">USD</option>
                          <option value="EUR">EUR</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between pt-6 border-t border-white/5">
            <Button variant="outline" onClick={prevStep} disabled={activeStep === 1}>
              ← {t("previous")}
            </Button>
            <div className="flex items-center gap-2">
              {activeStep < 4 ? (
                <Button onClick={nextStep}>{t("next")} →</Button>
              ) : (
                <Button variant="primary" onClick={handleSubmit} disabled={loading}>
                  {loading ? t("saving") : (initialSkill ? t("skills.update_skill") : t("skills.create_skill"))}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}