#!/usr/bin/env python
"""Main entry point for running SWE-agent with a task."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path ONLY for swebench_instances
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.append(str(_parent_dir))

from dotenv import load_dotenv

from sweagent import SWEAgentRunner
from swebench_instances.task_reader import SWEBenchTaskReader


async def main():
    parser = argparse.ArgumentParser(description="Run SWE-agent on a task")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Path to configuration YAML file (default: config.yaml)",
    )
    
    # Task source: either direct task or SWE-bench
    task_group = parser.add_mutually_exclusive_group(required=True)
    task_group.add_argument(
        "--task",
        type=str,
        help="Task description for the agent to solve",
    )
    task_group.add_argument(
        "--swe-bench-task",
        type=str,
        metavar="INSTANCE_ID",
        help="Load task from SWE-bench by instance ID (e.g., astropy__astropy-12907)",
    )
    task_group.add_argument(
        "--swe-bench-index",
        type=int,
        metavar="INDEX",
        help="Load task from SWE-bench by index (0-499)",
    )
    
    args = parser.parse_args()
    
    # Load environment variables from .env
    load_dotenv()
    
    # Determine task input
    if args.task:
        task_input = args.task
        task_id = "custom"
    elif args.swe_bench_task:
        # Load by instance ID
        print("Loading SWE-bench task by ID...")
        reader = SWEBenchTaskReader()
        swe_task = reader.get_task_by_id(args.swe_bench_task)
        if swe_task is None:
            print(f"✗ Task {args.swe_bench_task} not found in dataset")
            return
        task_input = swe_task.to_agent_task()
        task_id = swe_task.instance_id
    else:
        # Load by index
        print(f"Loading SWE-bench task at index {args.swe_bench_index}...")
        reader = SWEBenchTaskReader()
        swe_task = reader.get_task(args.swe_bench_index)
        task_input = swe_task.to_agent_task()
        task_id = swe_task.instance_id
    
    print("="*70)
    print("SWE-Agent Task Runner")
    print("="*70)
    print(f"Config: {args.config}")
    print(f"Task ID: {task_id}")
    print(f"Task Preview: {task_input[:150]}{'...' if len(task_input) > 150 else ''}")
    print("="*70)
    print()
    
    # Create and run the agent
    runner = SWEAgentRunner(config_path=args.config)
    
    try:
        await runner.run(task_input)
        print("\n" + "="*70)
        print("✓ Task execution complete")
        print("="*70)
    except Exception as e:
        print("\n" + "="*70)
        print(f"✗ Error during execution: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

