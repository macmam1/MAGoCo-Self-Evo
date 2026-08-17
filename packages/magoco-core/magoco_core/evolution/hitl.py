"""Approval and Planning states for the Workflow Engine.

Allows the engine to pause execution and wait for human intervention.
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"

@dataclass
class ApprovalRequest:
    """A request for human approval before executing a sensitive action."""
    request_id: str
    node_id: str
    agent_name: str
    action_description: str
    proposed_input: Dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    user_comment: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

class HumanInTheLoopManager:
    """Manages pending approvals and planning phase for workflows."""
    
    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.active_plans: Dict[str, Dict[str, Any]] = {}

    async def create_approval(self, request: ApprovalRequest):
        self.pending_approvals[request.request_id] = request
        return request.request_id

    async def resolve_approval(self, request_id: str, status: ApprovalStatus, comment: str = None):
        if request_id not in self.pending_approvals:
            raise ValueError("Approval request not found")
            
        req = self.pending_approvals[request_id]
        req.status = status
        req.user_comment = comment
        req.resolved_at = datetime.utcnow()
        return req

    async def submit_plan(self, workflow_id: str, plan: Dict[str, Any]):
        self.active_plans[workflow_id] = plan
        return True

    async def approve_plan(self, workflow_id: str):
        if workflow_id not in self.active_plans:
            raise ValueError("No pending plan for this workflow")
        return True

# Global instance
hitl_manager = HumanInTheLoopManager()

def init_hitl_manager() -> HumanInTheLoopManager:
    """Initialize and return the HITL manager (for lifespan)."""
    return hitl_manager