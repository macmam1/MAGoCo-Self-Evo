"""
Skills System Core Models
Professional skill registry with versioning, dependencies, security, marketplace
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid


class SkillCategory(str, Enum):
    """Skill categories for organization"""
    AUTOMATION = "automation"
    CODING = "coding"
    DATA_PROCESSING = "data_processing"
    WEB_SCRAPING = "web_scraping"
    API_INTEGRATION = "api_integration"
    FILE_OPERATIONS = "file_operations"
    SYSTEM_ADMIN = "system_admin"
    AI_ML = "ai_ml"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    DEVELOPMENT = "development"
    SECURITY = "security"
    MONITORING = "monitoring"
    CUSTOM = "custom"


class SkillType(str, Enum):
    """Skill execution type"""
    FUNCTION = "function"           # Python function
    WORKFLOW = "workflow"           # DAG workflow
    AGENT = "agent"                 # Autonomous agent
    TEMPLATE = "template"           # Reusable template
    PROMPT = "prompt"               # Prompt template
    TOOL = "tool"                   # External tool wrapper
    CHAIN = "chain"                 # Skill chain/composition


class SkillStatus(str, Enum):
    """Skill lifecycle status"""
    DRAFT = "draft"
    TESTING = "testing"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class SecurityLevel(str, Enum):
    """Security sandbox level"""
    SAFE = "safe"                   # No external access, no file system
    RESTRICTED = "restricted"       # Limited external API, read-only FS
    STANDARD = "standard"           # External APIs, limited FS
    ELEVATED = "elevated"           # Full FS, system commands
    FULL = "full"                   # Full system access (admin only)


class ExecutionMode(str, Enum):
    """How the skill is executed"""
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"
    BATCH = "batch"


@dataclass
class SkillParameter:
    """Skill input parameter definition"""
    name: str
    type: str                          # "string", "integer", "float", "boolean", "object", "array", "file"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    format: Optional[str] = None       # "email", "url", "date", "uuid", etc.
    items: Optional['SkillParameter'] = None  # for arrays
    properties: Optional[Dict[str, 'SkillParameter']] = None  # for objects
    sensitive: bool = False            # Hide in logs/UI (passwords, tokens)


@dataclass
class SkillReturn:
    """Skill return value definition"""
    type: str
    description: str = ""
    properties: Optional[Dict[str, SkillParameter]] = None
    items: Optional[SkillParameter] = None
    examples: List[Any] = field(default_factory=list)


@dataclass
class SkillDependency:
    """Skill dependency on another skill or external package"""
    skill_id: Optional[str] = None      # Internal skill dependency
    package_name: Optional[str] = None  # External pip/npm package
    version_spec: str = ">="            # Version constraint
    required: bool = True
    reason: str = ""


@dataclass
class SkillExample:
    """Usage example for the skill"""
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Optional[Any] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class SkillTest:
    """Test case for skill validation"""
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Any
    expected_error: Optional[str] = None
    timeout: float = 30.0
    tags: List[str] = field(default_factory=list)


@dataclass
class SkillReview:
    """User review/rating for a skill"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    rating: int = 5                     # 1-5
    title: str = ""
    content: str = ""
    version: str = ""
    helpful_votes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    verified: bool = False              # Verified purchaser/user


@dataclass
class SkillAnalytics:
    """Usage analytics for a skill"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    avg_memory_mb: float = 0.0
    unique_users: int = 0
    last_executed: Optional[datetime] = None
    error_rate: float = 0.0
    popularity_score: float = 0.0       # Calculated metric


@dataclass
class SkillManifest:
    """Complete skill definition (stored in manifest.json)"""
    # Identity
    id: str
    name: str
    display_name: str
    description: str
    version: str                        # Semver
    
    # Classification
    category: SkillCategory
    type: SkillType
    tags: Set[str] = field(default_factory=set)
    
    # Author/Publisher
    author: str = ""
    author_email: str = ""
    organization: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    
    # Technical
    type: SkillType = SkillType.FUNCTION
    entry_point: str = "main"           # Function/class name
    code_path: str = ""                 # Relative to skill root
    requirements: List[str] = field(default_factory=list)  # pip packages
    system_requirements: List[str] = field(default_factory=list)  # system deps
    
    # Execution
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    timeout: float = 30.0               # seconds
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    security_level: SecurityLevel = SecurityLevel.RESTRICTED
    allowed_domains: List[str] = field(default_factory=list)  # for network access
    allowed_commands: List[str] = field(default_factory=list)  # for shell
    
    # Interface
    parameters: List[SkillParameter] = field(default_factory=list)
    returns: SkillReturn = field(default_factory=lambda: SkillReturn(type="any"))
    
    # Dependencies
    dependencies: List[SkillDependency] = field(default_factory=list)
    
    # Quality
    status: SkillStatus = SkillStatus.DRAFT
    tests: List[SkillTest] = field(default_factory=list)
    examples: List[SkillExample] = field(default_factory=list)
    min_core_version: str = "0.3.0"
    compatible_platforms: List[str] = field(default_factory=lambda: ["linux", "macos", "windows"])
    
    # Marketplace
    price: float = 0.0                  # 0 = free
    currency: str = "USD"
    is_public: bool = True
    featured: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0
    
    # Analytics
    analytics: SkillAnalytics = field(default_factory=SkillAnalytics)
    
    # Hash for integrity
    content_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, (set,)):
                data[key] = list(value)
            elif isinstance(value, (datetime,)):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
            elif hasattr(value, 'to_dict'):
                data[key] = value.to_dict()
            elif isinstance(value, list) and value and hasattr(value[0], 'to_dict'):
                data[key] = [v.to_dict() for v in value]
            else:
                data[key] = value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillManifest":
        # Convert enums
        for key in ["category", "type", "execution_mode", "status", "security_level"]:
            if key in data and isinstance(data[key], str):
                enum_class = {
                    "category": SkillCategory,
                    "type": SkillType,
                    "execution_mode": ExecutionMode,
                    "status": SkillStatus,
                    "security_level": SecurityLevel,
                }[key]
                data[key] = enum_class(data[key])
        
        # Convert nested objects
        if "parameters" in data:
            data["parameters"] = [SkillParameter(**p) for p in data["parameters"]]
        if "returns" in data and isinstance(data["returns"], dict):
            data["returns"] = SkillReturn(**data["returns"])
        if "dependencies" in data:
            data["dependencies"] = [SkillDependency(**d) for d in data["dependencies"]]
        if "tests" in data:
            data["tests"] = [SkillTest(**t) for t in data["tests"]]
        if "examples" in data:
            data["examples"] = [SkillExample(**e) for e in data["examples"]]
        if "analytics" in data and isinstance(data["analytics"], dict):
            data["analytics"] = SkillAnalytics(**data["analytics"])
        
        # Convert timestamps
        for key in ["created_at", "updated_at", "published_at"]:
            if key in data and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert tags
        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = set(data["tags"])
        
        return cls(**data)
    
    def compute_hash(self) -> str:
        """Compute content hash for integrity verification"""
        import hashlib
        content = f"{self.id}{self.version}{self.entry_point}{self.code_path}{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class SkillInstance:
    """Runtime instance of a skill"""
    manifest: SkillManifest
    config: Dict[str, Any] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)  # Injected at runtime
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    use_count: int = 0
    
    # Runtime state
    is_active: bool = True
    last_error: Optional[str] = None
    consecutive_failures: int = 0


@dataclass
class SkillComposition:
    """Composition of multiple skills into a pipeline"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    skills: List[str] = field(default_factory=list)  # Skill IDs in order
    connections: List[Dict[str, str]] = field(default_factory=list)  # output -> input mappings
    parallel_groups: List[List[str]] = field(default_factory=list)  # Parallel execution groups
    conditionals: List[Dict[str, Any]] = field(default_factory=list)  # Conditional execution
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SkillSearchQuery:
    """Search query for skill discovery"""
    query: str = ""
    category: Optional[SkillCategory] = None
    type: Optional[SkillType] = None
    tags: Optional[Set[str]] = None
    author: Optional[str] = None
    min_rating: float = 0.0
    max_price: float = float('inf')
    free_only: bool = False
    featured_only: bool = False
    verified_only: bool = False
    compatible_version: Optional[str] = None
    security_level: Optional[SecurityLevel] = None
    sort_by: str = "relevance"  # relevance, rating, downloads, updated, created
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


@dataclass
class SkillSearchResult:
    skill: SkillManifest
    score: float
    matched_fields: List[str]
    highlights: Dict[str, List[str]] = field(default_factory=dict)