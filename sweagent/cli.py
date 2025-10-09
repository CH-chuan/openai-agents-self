#!/usr/bin/env python
"""Main entry point for running SWE-agent with a task."""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path ONLY for swebench_instances
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.append(str(_parent_dir))

import yaml
from dotenv import load_dotenv

from sweagent import SWEAgentRunner
from swebench_instances.build_swebench_instances import SWEBenchInstances, SWEBenchInstance, pull_and_build_sif


def parse_agent_config(config_path: Path) -> Dict[str, Any]:
    """Parse agent configuration YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Agent config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Expand environment variables in the config
    config_str = yaml.dump(config)
    config_str = os.path.expandvars(config_str)
    config = yaml.safe_load(config_str)
    
    return config


def parse_task_config(config_path: Path) -> Dict[str, Any]:
    """Parse task configuration YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Task config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


async def main():
    parser = argparse.ArgumentParser(description="Run SWE-agent on a task")
    
    # Configuration files
    parser.add_argument(
        "--agent-config",
        type=Path,
        default=Path(__file__).parent / "agent_config.yaml",
        help="Path to agent configuration YAML file (default: agent_config.yaml)",
    )
    parser.add_argument(
        "--task-config",
        type=Path,
        default=Path(__file__).parent.parent / "swebench_instances" / "task_config.yaml",
        help="Path to task configuration YAML file (default: swebench_instances/task_config.yaml)",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("sweagent_output"),
        help="Path to output directory for results (default: sweagent_output)",
    )
    
    args = parser.parse_args()
    
    # Load environment variables from .env
    load_dotenv()
    
    # Parse configuration files
    try:
        # Handle legacy config argument
        agent_config_path = args.agent_config
        
        print("Parsing configuration files...")
        agent_config = parse_agent_config(agent_config_path)
        task_config = parse_task_config(args.task_config)
        
        print("✓ Configuration files parsed successfully")
        print(f"Agent config: {agent_config_path}")
        print(f"Task config: {args.task_config}")
        
        # Display parsed parameters
        print("\n" + "="*70)
        print("PARSED CONFIGURATION PARAMETERS")
        print("="*70)
        
        print("\nAGENT CONFIGURATION:")
        print("-" * 30)
        for key, value in agent_config.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for subkey, subvalue in value.items():
                    print(f"  {subkey}: {subvalue}")
            else:
                print(f"{key}: {value}")
        
        print("\nTASK CONFIGURATION:")
        print("-" * 30)
        for key, value in task_config.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for subkey, subvalue in value.items():
                    print(f"  {subkey}: {subvalue}")
            else:
                print(f"{key}: {value}")
        
        print("="*70)
        
    except Exception as e:
        print(f"✗ Error parsing configuration files: {e}")
        import traceback
        traceback.print_exc()
        return
    
    if task_config['instances']['type'] == 'swe_bench':
        # Load SWE-bench instances from config
        swe_bench = SWEBenchInstances.from_config_file(str(args.task_config))
        instances = swe_bench.get_instances()
        
        print(f"\nFound {len(instances)} SWE-bench instances:")
        for instance in instances:
            print(f"  - {instance.instance_id} ({instance.repo})")
            print(f"    Problem: {instance.problem_statement[:100]}...")
        
        # Create output directory
        output_path = args.output_path
        output_path.mkdir(exist_ok=True)
        print(f"✓ Output directory: {output_path}")
        
        # Process each instance
        successful_runs = 0
        failed_runs = 0
        
        for i, instance in enumerate(instances, 1):
            print(f"\n[{i}/{len(instances)}] Processing instance: {instance.instance_id}")
            try:
                await run_single_instance(instance, agent_config, output_path)
                successful_runs += 1
            except Exception as e:
                print(f"✗ Failed to process {instance.instance_id}: {e}")
                failed_runs += 1
        
        # Print summary
        print("\n" + "="*70)
        print("EXECUTION SUMMARY")
        print("="*70)
        print(f"Total instances: {len(instances)}")
        print(f"Successful runs: {successful_runs}")
        print(f"Failed runs: {failed_runs}")
        print(f"Success rate: {(successful_runs/len(instances)*100):.1f}%")
        print("="*70)



async def run_single_instance(instance: SWEBenchInstance, agent_config: Dict[str, Any], output_path: Path):
    """
    Run SWE-agent on a single instance.
    
    Args:
        instance: SWEBenchInstance object with all instance data
        agent_config: Agent configuration dictionary
        output_path: Path to output directory
    """
    try:
        print(f"Starting SWE-agent for instance: {instance.instance_id}")
        print(f"Problem statement: {instance.problem_statement[:200]}...")
        print(f"Repository: {instance.repo}")
        print(f"Base commit: {instance.base_commit}")
        
        # Build container if needed
        sif_path = pull_and_build_sif(instance.instance_id)
        if not sif_path:
            print(f"✗ Failed to build container for {instance.instance_id}")
            return
        
        print(f"✓ Container ready: {sif_path}")
        
        # Create instance-specific output directory
        instance_dir = output_path / instance.instance_id.replace('__', '_')
        instance_dir.mkdir(exist_ok=True)
        
        # Save agent config for this instance (original config, no modifications)
        agent_config_path = instance_dir / "agent_config.yaml"
        with open(agent_config_path, 'w') as f:
            yaml.dump(agent_config, f, default_flow_style=False)
        
        print(f"✓ Saved configs to: {instance_dir}")
        
        # Initialize and run SWE-agent with explicit sif_path
        # No need to modify config - pass sif_path directly!
        runner = SWEAgentRunner(
            config_path=agent_config_path,
            instance_id=instance.instance_id,
            model_name=agent_config['agent']['model']['name'],
            sif_path=Path(sif_path),  # ← Pass explicitly
        )
        
        print(f"✓ SWE-agent initialized")
        print(f"Running SWE-agent with problem statement...")
        print(f"Instance: {instance.instance_id}")
        print(f"Model: {agent_config['agent']['model']['name']}")
        print(f"Container: {sif_path}")
        
        # Run the agent with the problem statement
        await runner.run(instance.problem_statement)
        
        print(f"✓ SWE-agent completed successfully")
        
        # Report workspace location if workspace was created
        workspace_pattern = f"*{instance.instance_id.replace('__', '_')}*"
        print(f"\n💾 Workspace: workspaces/{workspace_pattern}")
        print(f"✓ Completed processing {instance.instance_id}")
        
        # TODO: Save trajectory.jsonl with agent chat log, tool execution, and environment feedback
        # This would be saved to instance_dir / "trajectory.jsonl"
        
    except Exception as e:
        print(f"✗ Error processing {instance.instance_id}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

