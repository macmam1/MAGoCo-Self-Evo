"""
Integrations System Core Models
Professional integration registry with OAuth, webhooks, MCP, connectors marketplace
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid


class IntegrationCategory(str, Enum):
    """Integration categories for organization"""
    COMMUNICATION = "communication"          # Slack, Discord, Teams, Email
    CRM = "crm"                              # Salesforce, HubSpot, Pipedrive
    PROJECT_MANAGEMENT = "project_management" # Jira, Asana, Trello, Linear
    DEVELOPMENT = "development"              # GitHub, GitLab, Bitbucket
    CI_CD = "ci_cd"                          # Jenkins, GitHub Actions, GitLab CI
    CLOUD = "cloud"                          # AWS, GCP, Azure, DigitalOcean
    DATABASE = "database"                    # PostgreSQL, MongoDB, Redis, Snowflake
    MONITORING = "monitoring"                # Datadog, Prometheus, Grafana, Sentry
    PAYMENT = "payment"                      # Stripe, PayPal, Square
    STORAGE = "storage"                      # S3, GCS, Dropbox, Google Drive
    AI_ML = "ai_ml"                          # OpenAI, Anthropic, HuggingFace
    MARKETING = "marketing"                  # Mailchimp, HubSpot, SendGrid
    ECOMMERCE = "ecommerce"                  # Shopify, WooCommerce, Magento
    CUSTOM = "custom"


class IntegrationType(str, Enum):
    """Integration connection type"""
    OAUTH2 = "oauth2"                        # OAuth 2.0 (Google, GitHub, Slack)
    OAUTH1 = "oauth1"                        # OAuth 1.0a (Twitter, Tumblr)
    API_KEY = "api_key"                      # Simple API key (Stripe, OpenAI)
    BASIC_AUTH = "basic_auth"                # Username/password
    BEARER_TOKEN = "bearer_token"            # Bearer token (Notion, Linear)
    JWT = "jwt"                              # JWT token
    CUSTOM = "custom"                        # Custom authentication


class IntegrationStatus(str, Enum):
    """Integration lifecycle status"""
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class WebhookEventType(str, Enum):
    """Webhook event types"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    TRIGGERED = "triggered"
    FAILED = "failed"
    COMPLETED = "completed"
    CUSTOM = "custom"


class TriggerType(str, Enum):
    """Trigger types for workflows"""
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"
    POLLING = "polling"


@dataclass
class AuthConfig:
    """Authentication configuration for integration"""
    type: IntegrationType
    
    # OAuth2
    client_id: str = ""
    client_secret: str = ""
    authorization_url: str = ""
    token_url: str = ""
    scope: List[str] = field(default_factory=list)
    redirect_uri: str = ""
    
    # API Key / Bearer Token
    api_key: str = ""
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer"
    
    # Basic Auth
    username: str = ""
    password: str = ""
    
    # Custom
    custom_headers: Dict[str, str] = field(default_factory=dict)
    custom_params: Dict[str, str] = field(default_factory=dict)
    
    # Token storage (encrypted at rest)
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    
    # PKCE for OAuth2
    pkce_enabled: bool = False
    code_verifier: str = ""
    code_challenge: str = ""
    code_challenge_method: str = "S256"
    
    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                data[key] = value.value
            elif isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, set):
                data[key] = list(value)
            else:
                data[key] = value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthConfig":
        if "type" in data and isinstance(data["type"], str):
            data["type"] = IntegrationType(data["type"])
        if "token_expires_at" in data and data["token_expires_at"]:
            data["token_expires_at"] = datetime.fromisoformat(data["token_expires_at"])
        return cls(**data)


@dataclass
class WebhookConfig:
    """Webhook configuration for receiving events"""
    url: str = ""
    secret: str = ""
    events: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 3,
        "backoff_factor": 2,
        "max_backoff_seconds": 300,
    })
    timeout_seconds: int = 30
    verify_ssl: bool = True
    active: bool = True
    
    # Signature verification
    signature_header: str = "X-Signature"
    signature_algorithm: str = "sha256"
    
    # Filtering
    filters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ConnectorAction:
    """An action that can be performed via the integration"""
    id: str
    name: str
    description: str
    method: str = "POST"  # GET, POST, PUT, PATCH, DELETE
    path: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    response_schema: Optional[Dict[str, Any]] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    rate_limit: Optional[Dict[str, Any]] = None  # requests per minute
    requires_auth: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class ConnectorTrigger:
    """A trigger that can start workflows"""
    id: str
    name: str
    description: str
    type: TriggerType = TriggerType.WEBHOOK
    webhook_config: Optional[WebhookConfig] = None
    schedule: Optional[str] = None  # Cron expression
    event_filter: Dict[str, Any] = field(default_factory=dict)
    payload_schema: Optional[Dict[str, Any]] = None


@dataclass
class IntegrationManifest:
    """Complete integration definition"""
    # Identity
    id: str
    name: str
    display_name: str
    description: str
    version: str
    
    # Classification
    category: IntegrationCategory
    tags: Set[str] = field(default_factory=set)
    
    # Branding
    logo_url: str = ""
    icon: str = ""
    color: str = "#7c5cff"
    
    # Author/Publisher
    author: str = ""
    author_email: str = ""
    organization: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    documentation_url: str = ""
    
    # Authentication
    auth_config: AuthConfig = field(default_factory=AuthConfig)
    supported_auth_types: List[IntegrationType] = field(default_factory=list)
    
    # API Configuration
    base_url: str = ""
    api_version: str = "v1"
    rate_limits: Dict[str, int] = field(default_factory=dict)  # endpoint -> rpm
    
    # Actions & Triggers
    actions: List[ConnectorAction] = field(default_factory=list)
    triggers: List[ConnectorTrigger] = field(default_factory=list)
    
    # Webhooks
    webhook_config: WebhookConfig = field(default_factory=WebhookConfig)
    supports_webhooks: bool = True
    
    # MCP Support
    mcp_enabled: bool = False
    mcp_servers: List[Dict[str, Any]] = field(default_factory=list)
    
    # Quality
    status: IntegrationStatus = IntegrationStatus.DRAFT
    tests: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    min_core_version: str = "0.3.0"
    
    # Marketplace
    is_public: bool = True
    featured: bool = False
    price: float = 0.0
    currency: str = "USD"
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                data[key] = value.value
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, set):
                data[key] = list(value)
            elif hasattr(value, 'to_dict'):
                data[key] = value.to_dict()
            elif isinstance(value, list) and value and hasattr(value[0], 'to_dict'):
                data[key] = [v.to_dict() for v in value]
            else:
                data[key] = value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegrationManifest":
        # Convert enums
        for key in ["category", "status"]:
            if key in data and isinstance(data[key], str):
                enum_class = {"category": IntegrationCategory, "status": IntegrationStatus}[key]
                data[key] = enum_class(data[key])
        
        # Convert nested objects
        if "auth_config" in data and isinstance(data["auth_config"], dict):
            data["auth_config"] = AuthConfig.from_dict(data["auth_config"])
        if "webhook_config" in data and isinstance(data["webhook_config"], dict):
            data["webhook_config"] = WebhookConfig(**data["webhook_config"])
        if "actions" in data:
            data["actions"] = [ConnectorAction(**a) for a in data["actions"]]
        if "triggers" in data:
            data["triggers"] = [ConnectorTrigger(**t) for t in data["triggers"]]
        
        # Convert timestamps
        for key in ["created_at", "updated_at", "published_at"]:
            if key in data and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert tags
        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = set(data["tags"])
        
        return cls(**data)


@dataclass
class IntegrationInstance:
    """Runtime instance of an integration with user-specific config"""
    manifest_id: str
    manifest_version: str
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # User configuration
    name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    auth_data: Dict[str, str] = field(default_factory=dict)  # Encrypted secrets
    
    # Status
    status: IntegrationStatus = IntegrationStatus.DRAFT
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Webhook
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    # Stats
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_called: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                data[key] = value.value
            elif isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, set):
                data[key] = list(value)
            else:
                data[key] = value
        return data


@dataclass
class IntegrationSearchQuery:
    """Search query for integrations"""
    query: str = ""
    category: Optional[IntegrationCategory] = None
    type: Optional[IntegrationType] = None
    tags: Optional[Set[str]] = None
    author: Optional[str] = None
    min_rating: float = 0.0
    max_price: float = float('inf')
    free_only: bool = False
    featured_only: bool = False
    verified_only: bool = False
    sort_by: str = "relevance"  # relevance, rating, downloads, updated, created
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


@dataclass
class IntegrationSearchResult:
    integration: "IntegrationManifest"
    score: float
    matched_fields: List[str]
    highlights: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class WebhookEvent:
    """Incoming webhook event"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    integration_id: str = ""
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    signature: Optional[str] = None
    verified: bool = False
    received_at: datetime = field(default_factory=datetime.utcnow)
    processed: bool = False
    processing_error: Optional[str] = None


@dataclass
class ConnectorTemplate:
    """Pre-built integration template"""
    id: str
    name: str
    description: str
    category: IntegrationCategory
    manifest_template: Dict[str, Any]
    code_template: str
    readme_template: str
    requirements_template: str = ""
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    estimated_time_minutes: int = 30
    tags: List[str] = field(default_factory=list)


# ============ Pre-built Connector Templates ============

CONNECTOR_TEMPLATES = [
    ConnectorTemplate(
        id="slack",
        name="Slack",
        description="Send messages, manage channels, and respond to events in Slack",
        category=IntegrationCategory.COMMUNICATION,
        difficulty="beginner",
        estimated_time_minutes=15,
        tags=["chat", "notifications", "team"],
        manifest_template={
            "id": "slack",
            "name": "slack",
            "display_name": "Slack",
            "description": "Send messages, manage channels, and respond to events in Slack",
            "version": "1.0.0",
            "category": "communication",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "oauth2",
                "authorization_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access",
                "scope": ["channels:read", "chat:write", "groups:read", "im:write"],
            },
            "base_url": "https://slack.com/api",
            "actions": [
                {"id": "send_message", "name": "Send Message", "method": "POST", "path": "/chat.postMessage"},
                {"id": "create_channel", "name": "Create Channel", "method": "POST", "path": "/conversations.create"},
                {"id": "list_channels", "name": "List Channels", "method": "GET", "path": "/conversations.list"},
            ],
        },
        code_template='''
async def main(input_data):
    import httpx
    token = input_data["auth"]["access_token"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": input_data["channel"], "text": input_data["text"]}
        )
        return response.json()
''',
    ),
    ConnectorTemplate(
        id="github",
        name="GitHub",
        description="Manage repositories, issues, pull requests, and workflows",
        category=IntegrationCategory.DEVELOPMENT,
        difficulty="intermediate",
        estimated_time_minutes=20,
        tags=["git", "ci/cd", "repository"],
        manifest_template={
            "id": "github",
            "name": "github",
            "display_name": "GitHub",
            "description": "Manage repositories, issues, pull requests, and workflows",
            "version": "1.0.0",
            "category": "development",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "oauth2",
                "authorization_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "scope": ["repo", "workflow", "admin:repo_hook"],
            },
            "base_url": "https://api.github.com",
            "actions": [
                {"id": "create_issue", "name": "Create Issue", "method": "POST", "path": "/repos/{owner}/{repo}/issues"},
                {"id": "create_pr", "name": "Create Pull Request", "method": "POST", "path": "/repos/{owner}/{repo}/pulls"},
                {"id": "trigger_workflow", "name": "Trigger Workflow", "method": "POST", "path": "/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"},
            ],
        },
        code_template='''
async def main(input_data):
    import httpx
    token = input_data["auth"]["access_token"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{input_data['owner']}/{input_data['repo']}/issues",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
            json={"title": input_data["title"], "body": input_data.get("body", "")}
        )
        return response.json()
''',
    ),
    ConnectorTemplate(
        id="jira",
        name="Jira",
        description="Manage issues, projects, and workflows in Jira",
        category=IntegrationCategory.PROJECT_MANAGEMENT,
        difficulty="intermediate",
        estimated_time_minutes=20,
        tags=["issue-tracking", "agile", "project-management"],
        manifest_template={
            "id": "jira",
            "name": "jira",
            "display_name": "Jira",
            "description": "Manage issues, projects, and workflows in Jira",
            "version": "1.0.0",
            "category": "project_management",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "bearer_token",
                "api_key_header": "Authorization",
                "api_key_prefix": "Bearer",
            },
            "base_url": "https://{domain}.atlassian.net/rest/api/3",
            "actions": [
                {"id": "create_issue", "name": "Create Issue", "method": "POST", "path": "/issue"},
                {"id": "search_issues", "name": "Search Issues", "method": "POST", "path": "/search"},
            ],
        },
        code_template='''
async def main(input_data):
    import httpx
    token = input_data["auth"]["api_key"]
    domain = input_data["config"]["domain"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{domain}.atlassian.net/rest/api/3/issue",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            json=input_data["fields"]
        )
        return response.json()
''',
    ),
    ConnectorTemplate(
        id="stripe",
        name="Stripe",
        description="Process payments, manage customers, and handle subscriptions",
        category=IntegrationCategory.PAYMENT,
        difficulty="intermediate",
        estimated_time_minutes=20,
        tags=["payments", "subscriptions", "ecommerce"],
        manifest_template={
            "id": "stripe",
            "name": "stripe",
            "display_name": "Stripe",
            "description": "Process payments, manage customers, and handle subscriptions",
            "version": "1.0.0",
            "category": "payment",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "api_key",
                "api_key_header": "Authorization",
                "api_key_prefix": "Bearer",
            },
            "base_url": "https://api.stripe.com/v1",
            "actions": [
                {"id": "create_payment", "name": "Create Payment", "method": "POST", "path": "/payment_intents"},
                {"id": "create_customer", "name": "Create Customer", "method": "POST", "path": "/customers"},
                {"id": "create_subscription", "name": "Create Subscription", "method": "POST", "path": "/subscriptions"},
            ],
        },
        code_template='''
async def main(input_data):
    import httpx
    key = input_data["auth"]["api_key"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.stripe.com/v1/payment_intents",
            headers={"Authorization": f"Bearer {key}"},
            data=input_data["params"]
        )
        return response.json()
''',
    ),
    ConnectorTemplate(
        id="sendgrid",
        name="SendGrid",
        description="Send transactional and marketing emails",
        category=IntegrationCategory.COMMUNICATION,
        difficulty="beginner",
        estimated_time_minutes=15,
        tags=["email", "marketing", "notifications"],
        manifest_template={
            "id": "sendgrid",
            "name": "sendgrid",
            "display_name": "SendGrid",
            "description": "Send transactional and marketing emails",
            "version": "1.0.0",
            "category": "communication",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "api_key",
                "api_key_header": "Authorization",
                "api_key_prefix": "Bearer",
            },
            "base_url": "https://api.sendgrid.com/v3",
            "actions": [
                {"id": "send_email", "name": "Send Email", "method": "POST", "path": "/mail/send"},
            ],
        },
        code_template='''
async def main(input_data):
    import httpx
    key = input_data["auth"]["api_key"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": input_data["to"]}], "subject": input_data["subject"]}],
                "from": {"email": input_data["from"]},
                "content": [{"type": "text/plain", "value": input_data["content"]}]
            }
        )
        return response.json()
''',
    ),
    ConnectorTemplate(
        id="aws",
        name="AWS",
        description="Manage AWS resources (EC2, S3, Lambda, DynamoDB, etc.)",
        category=IntegrationCategory.CLOUD,
        difficulty="advanced",
        estimated_time_minutes=30,
        tags=["cloud", "infrastructure", "devops"],
        manifest_template={
            "id": "aws",
            "name": "aws",
            "display_name": "AWS",
            "description": "Manage AWS resources (EC2, S3, Lambda, DynamoDB, etc.)",
            "version": "1.0.0",
            "category": "cloud",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "custom",
            },
            "base_url": "https://{service}.{region}.amazonaws.com",
            "actions": [
                {"id": "s3_upload", "name": "Upload to S3", "method": "PUT", "path": "/{bucket}/{key}"},
                {"id": "lambda_invoke", "name": "Invoke Lambda", "method": "POST", "path": "/2015-03-31/functions/{function_name}/invocations"},
            ],
        },
        code_template='''
async def main(input_data):
    import boto3
    session = boto3.Session(
        aws_access_key_id=input_data["config"]["access_key"],
        aws_secret_access_key=input_data["config"]["secret_key"],
        region_name=input_data["config"]["region"]
    )
    s3 = session.client("s3")
    response = s3.upload_fileobj(input_data["file"], input_data["bucket"], input_data["key"])
    return {"success": True}
''',
    ),
    ConnectorTemplate(
        id="postgresql",
        name="PostgreSQL",
        description="Query and manage PostgreSQL databases",
        category=IntegrationCategory.DATABASE,
        difficulty="intermediate",
        estimated_time_minutes=20,
        tags=["database", "sql", "data"],
        manifest_template={
            "id": "postgresql",
            "name": "postgresql",
            "display_name": "PostgreSQL",
            "description": "Query and manage PostgreSQL databases",
            "version": "1.0.0",
            "category": "database",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "custom",
            },
            "actions": [
                {"id": "query", "name": "Execute Query", "method": "POST", "path": "/query"},
                {"id": "execute", "name": "Execute Statement", "method": "POST", "path": "/execute"},
            ],
        },
        code_template='''
async def main(input_data):
    import asyncpg
    conn = await asyncpg.connect(
        host=input_data["config"]["host"],
        port=input_data["config"]["port"],
        user=input_data["config"]["user"],
        password=input_data["config"]["password"],
        database=input_data["config"]["database"]
    )
    result = await conn.fetch(input_data["query"])
    await conn.close()
    return [dict(row) for row in result]
''',
    ),
    ConnectorTemplate(
        id="openai",
        name="OpenAI",
        description="Generate text, embeddings, and images with OpenAI models",
        category=IntegrationCategory.AI_ML,
        difficulty="beginner",
        estimated_time_minutes=10,
        tags=["llm", "embeddings", "generation"],
        manifest_template={
            "id": "openai",
            "name": "openai",
            "display_name": "OpenAI",
            "description": "Generate text, embeddings, and images with OpenAI models",
            "version": "1.0.0",
            "category": "ai_ml",
            "author": "MAGoCo Team",
            "auth_config": {
                "type": "api_key",
                "api_key_header": "Authorization",
                "api_key_prefix": "Bearer",
            },
            "base_url": "https://api.openai.com/v1",
            "actions": [
                {"id": "chat_completion", "name": "Chat Completion", "method": "POST", "path": "/chat/completions"},
                {"id": "embeddings", "name": "Create Embeddings", "method": "POST", "path": "/embeddings"},
                {"id": "image_generation", "name": "Generate Image", "method": "POST", "path": "/images/generations"},
            ],
        },
        code_template='''
async def main(input_data):
    import httpx
    key = input_data["auth"]["api_key"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": input_data.get("model", "gpt-4"),
                "messages": input_data["messages"],
                "temperature": input_data.get("temperature", 0.7)
            }
        )
        return response.json()
''',
    ),
]