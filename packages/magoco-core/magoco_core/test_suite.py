"""Test the Multi-Agent Orchestrator and Self-Evolution Engine."""

import asyncio
from magoco_core.agents.orchestrator import MultiAgentOrchestrator
from magoco_core.memory.three_layer import ThreeLayerMemory
from magoco_core.evolution.engine import SelfEvolutionEngine

async def run_full_suite():
    # 1. Multi-Agent Test
    print('--- Running Multi-Agent Test ---')
    orchestrator = MultiAgentOrchestrator()
    orchestrator.add_default_team()
    result = await orchestrator.run_pipeline('Write a Python function to add two numbers')
    print(f"Multi-Agent Pipeline Finished. Final output: {result.get('final', '')[:50]}...")

    # 2. Self-Evolution Test
    print('\n--- Running Self-Evolution Test ---')
    memory = ThreeLayerMemory()
    engine = SelfEvolutionEngine(memory)
    trace = [{'step': 1, 'thought': 'I will write the function.', 'action': 'python_exec', 'success': True, 'observation': 'Def add(a,b): return a+b'}]
    reflection = await engine.reflect_on_task('coder', 'Write addition function', None, trace)
    print(f'Reflection Success: {reflection.success}')
    print(f'New prompt created: {reflection.improved_prompt is not None}')
    
    print('\n✅ Full Suite Passed!')

if __name__ == "__main__":
    asyncio.run(run_full_suite())
