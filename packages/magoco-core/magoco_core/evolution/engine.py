"""Self-Evolution Engine — agent improves itself over time.

Core components:
1. Reflection: Post-task analysis of success/failure
2. Pattern Mining: Extract recurring patterns from history
3. Prompt Optimization: Rewrite system prompts based on learnings
4. Skill Generation: Convert successful patterns into reusable skills
5. Knowledge Distillation: Compress history into distilled knowledge
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

from magoco_core.memory.three_layer import ThreeLayerMemory


@dataclass
class ReflectionResult:
    """Result of a reflection cycle."""
    task_goal: str
    success: bool
    key_insights: List[str]
    mistakes: List[str]
    improved_prompt: Optional[str] = None
    new_skill_candidates: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass 
class SkillBlueprint:
    """A new skill generated from successful pattern."""
    name: str
    description: str
    code: str  # Python code implementing the skill
    parameters: Dict[str, Any]
    trigger_pattern: str  # When to use this skill
    success_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SelfEvolutionEngine:
    """Engine that drives agent self-improvement."""

    def __init__(self, memory: ThreeLayerMemory, storage_path: str = "./evolution_data"):
        self.memory = memory
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.reflection_log: List[ReflectionResult] = []
        self.generated_skills: Dict[str, SkillBlueprint] = {}
        self.prompt_versions: Dict[str, str] = {}  # agent_role -> current prompt

    async def reflect_on_task(
        self, 
        agent_role: str,
        task_goal: str, 
        result: Any,
        trace: List[Dict[str, Any]]
    ) -> ReflectionResult:
        """Analyze a completed task and extract learnings."""
        
        # Determine success
        success = getattr(result, 'success', True) if hasattr(result, 'success') else True
        
        # Extract insights from trace
        key_insights = []
        mistakes = []
        
        for step in trace:
            if not step.get('success', True):
                mistakes.append(f"Step {step.get('step', '?')}: {step.get('observation', 'Failed')}")
            else:
                key_insights.append(f"Step {step.get('step', '?')}: {step.get('thought', '')[:100]}")
        
        # Build improved prompt if mistakes found
        improved_prompt = None
        if mistakes:
            current_prompt = self.prompt_versions.get(agent_role, "")
            improved_prompt = await self._optimize_prompt(agent_role, current_prompt, mistakes, key_insights)
            self.prompt_versions[agent_role] = improved_prompt
        
        # Generate skill candidates from successful patterns
        skill_candidates = []
        if success and len(key_insights) > 2:
            skill_candidates = await self._extract_skill_candidates(task_goal, trace)
        
        reflection = ReflectionResult(
            task_goal=task_goal,
            success=success,
            key_insights=key_insights,
            mistakes=mistakes,
            improved_prompt=improved_prompt,
            new_skill_candidates=skill_candidates,
        )
        
        self.reflection_log.append(reflection)
        
        # Store in memory
        await self.memory.add_turn(
            "system",
            f"REFLECTION[{agent_role}]: Goal='{task_goal}' Success={success} Insights={len(key_insights)} Mistakes={len(mistakes)}"
        )
        
        return reflection

    async def _optimize_prompt(self, role: str, current_prompt: str, mistakes: List[str], insights: List[str]) -> str:
        """Generate improved system prompt based on reflections."""
        
        optimization_instructions = f"""
Original Prompt:
{current_prompt}

Mistakes to avoid:
{chr(10).join(f"- {m}" for m in mistakes)}

Successful patterns:
{chr(10).join(f"- {i}" for i in insights)}

Generate an improved system prompt for a {role} agent that:
1. Avoids the mistakes above
2. Reinforces the successful patterns
3. Adds specific guidance for edge cases
4. Remains concise and actionable
"""
        # In production, this would call an LLM. For now, return enhanced version.
        improved = current_prompt or f"You are a {role} agent."
        improved += f"\n\n[SELF-OPTIMIZED {datetime.utcnow().isoformat()}]\n"
        improved += "Key improvements:\n"
        for m in mistakes[:3]:
            improved += f"- Avoid: {m}\n"
        for i in insights[:3]:
            improved += f"- Reinforce: {i}\n"
        return improved

    async def _extract_skill_candidates(self, task_goal: str, trace: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract reusable skill patterns from successful execution trace."""
        candidates = []
        
        # Simple pattern: sequence of tool calls that succeeded
        tool_sequence = []
        for step in trace:
            if step.get('action') and step.get('success'):
                tool_sequence.append({
                    'tool': step['action'],
                    'input': step.get('action_input', {}),
                    'output_summary': step.get('observation', '')[:200],
                })
        
        if len(tool_sequence) >= 3:
            candidates.append({
                'name': f"skill_{task_goal[:20].replace(' ', '_')}",
                'description': f"Automated sequence for: {task_goal}",
                'steps': tool_sequence,
                'trigger': task_goal,
            })
        
        return candidates

    async def promote_skill(self, candidate: Dict[str, Any]) -> SkillBlueprint:
        """Promote a skill candidate to a registered skill."""
        skill = SkillBlueprint(
            name=candidate['name'],
            description=candidate['description'],
            code=self._generate_skill_code(candidate),
            parameters={},
            trigger_pattern=candidate.get('trigger', ''),
        )
        
        self.generated_skills[skill.name] = skill
        
        # Save to disk
        skill_file = self.storage_path / f"{skill.name}.json"
        skill_file.write_text(json.dumps(asdict(skill), indent=2))
        
        # Add to working memory
        await self.memory.add_turn(
            "system",
            f"NEW SKILL GENERATED: {skill.name} - {skill.description}"
        )
        
        return skill

    def _generate_skill_code(self, candidate: Dict[str, Any]) -> str:
        """Generate Python code for the skill."""
        steps = candidate.get('steps', [])
        code = f'''"""
Auto-generated skill: {candidate['name']}
Description: {candidate['description']}
Trigger: {candidate.get('trigger', 'manual')}
"""

async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the learned skill sequence."""
    results = []
'''
        for i, step in enumerate(steps):
            tool = step.get('tool', '')
            inp = step.get('input', {})
            code += f"    # Step {i+1}: {tool}\n"
            code += f"    result = await tool_registry.get('{tool}').execute({inp})\n"
            code += "    results.append(result.content)\n\n"
        
        code += "    return {'status': 'completed', 'results': results}\n"
        return code

    async def distill_knowledge(self) -> Dict[str, Any]:
        """Distill reflection log into compact knowledge for long-term memory."""
        total_tasks = len(self.reflection_log)
        successful = sum(1 for r in self.reflection_log if r.success)
        
        # Extract common mistake patterns
        all_mistakes = []
        for r in self.reflection_log:
            all_mistakes.extend(r.mistakes)
        
        # Simple frequency analysis
        mistake_freq = {}
        for m in all_mistakes:
            key = m.split(':')[0] if ':' in m else m[:50]
            mistake_freq[key] = mistake_freq.get(key, 0) + 1
        
        top_mistakes = sorted(mistake_freq.items(), key=lambda x: -x[1])[:5]
        
        distilled = {
            'total_tasks': total_tasks,
            'success_rate': successful / max(total_tasks, 1),
            'top_mistake_patterns': top_mistakes,
            'generated_skills_count': len(self.generated_skills),
            'prompt_versions': {k: len(v) for k, v in self.prompt_versions.items()},
            'distilled_at': datetime.utcnow().isoformat(),
        }
        
        # Store in long-term memory
        await self.memory.add_turn(
            "system",
            f"KNOWLEDGE DISTILLED: SuccessRate={distilled['success_rate']:.2f} Skills={distilled['generated_skills_count']}"
        )
        
        return distilled

    def get_evolution_report(self) -> Dict[str, Any]:
        """Get comprehensive evolution status."""
        return {
            'reflections_count': len(self.reflection_log),
            'skills_generated': len(self.generated_skills),
            'prompt_optimizations': len(self.prompt_versions),
            'latest_reflection': asdict(self.reflection_log[-1]) if self.reflection_log else None,
            'distilled_knowledge': None,  # Would call distill_knowledge() to update
        }


# Global instance (initialized by main app)
evolution_engine: SelfEvolutionEngine | None = None

def init_evolution_engine(memory: ThreeLayerMemory) -> SelfEvolutionEngine:
    global evolution_engine
    evolution_engine = SelfEvolutionEngine(memory)
    return evolution_engine