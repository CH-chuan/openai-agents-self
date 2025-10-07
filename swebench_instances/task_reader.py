"""Task reader for SWE-bench dataset.

Loads tasks from the SWE-bench_Verified dataset and formats them for agent execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datasets import load_dataset


@dataclass
class SWEBenchTask:
    """Represents a single SWE-bench task."""
    
    instance_id: str
    """Formatted instance identifier (e.g., repo_owner__repo_name-PR-number)."""
    
    repo: str
    """Repository owner/name identifier from GitHub."""
    
    base_commit: str
    """Commit hash before the solution PR is applied."""
    
    problem_statement: str
    """The issue title and body that needs to be resolved."""
    
    patch: str
    """The gold patch that resolved the issue (for evaluation)."""
    
    test_patch: str
    """Test file patch contributed by the solution PR."""
    
    hints_text: str | None = None
    """Comments made on the issue prior to solution PR creation."""
    
    version: str | None = None
    """Installation version for running evaluation."""
    
    environment_setup_commit: str | None = None
    """Commit hash for environment setup and installation."""
    
    fail_to_pass: list[str] | None = None
    """Tests that should pass after the fix."""
    
    pass_to_pass: list[str] | None = None
    """Tests that should pass before and after the fix."""
    
    created_at: str | None = None
    """Creation date of the pull request."""
    
    def to_agent_task(self) -> str:
        """Convert to agent task prompt."""
        return f"""# Task: {self.instance_id}

## Repository
{self.repo}

## Problem Statement
{self.problem_statement}

## Instructions
You are working in a repository at commit {self.base_commit[:8]}. 
Your task is to resolve the issue described above by making the necessary code changes.

The repository is located at /testbed. Use the shell commands to:
1. Explore the codebase and understand the issue
2. Locate the relevant files
3. Make the necessary changes to fix the issue
4. Verify your changes work correctly

When you're done, your changes will be automatically evaluated against the test suite.
"""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "instance_id": self.instance_id,
            "repo": self.repo,
            "base_commit": self.base_commit,
            "problem_statement": self.problem_statement,
            "patch": self.patch,
            "test_patch": self.test_patch,
            "hints_text": self.hints_text,
            "version": self.version,
            "environment_setup_commit": self.environment_setup_commit,
            "fail_to_pass": self.fail_to_pass,
            "pass_to_pass": self.pass_to_pass,
            "created_at": self.created_at,
        }


class SWEBenchTaskReader:
    """Loads and manages SWE-bench tasks."""
    
    def __init__(self, dataset_name: str = "princeton-nlp/SWE-bench_Verified"):
        """Initialize the task reader.
        
        Args:
            dataset_name: Name of the Hugging Face dataset to load
        """
        self.dataset_name = dataset_name
        self.dataset = None
    
    def load_dataset(self, split: str = "test"):
        """Load the SWE-bench dataset from Hugging Face.
        
        Args:
            split: Dataset split to load (default: "test")
        """
        print(f"Loading {self.dataset_name} dataset (split: {split})...")
        self.dataset = load_dataset(self.dataset_name, split=split)
        print(f"✓ Loaded {len(self.dataset)} tasks")
    
    def get_task(self, index: int = 0) -> SWEBenchTask:
        """Get a specific task by index.
        
        Args:
            index: Index of the task to retrieve
            
        Returns:
            SWEBenchTask object
        """
        if self.dataset is None:
            self.load_dataset()
        
        if index < 0 or index >= len(self.dataset):
            raise IndexError(f"Task index {index} out of range (0-{len(self.dataset)-1})")
        
        return self._parse_task(self.dataset[index])
    
    def get_task_by_id(self, instance_id: str) -> SWEBenchTask | None:
        """Get a task by its instance ID.
        
        Args:
            instance_id: The instance_id to search for
            
        Returns:
            SWEBenchTask object or None if not found
        """
        if self.dataset is None:
            self.load_dataset()
        
        for item in self.dataset:
            if item["instance_id"] == instance_id:
                return self._parse_task(item)
        
        return None
    
    def get_tasks_by_repo(self, repo: str) -> list[SWEBenchTask]:
        """Get all tasks for a specific repository.
        
        Args:
            repo: Repository name (e.g., "django/django")
            
        Returns:
            List of SWEBenchTask objects
        """
        if self.dataset is None:
            self.load_dataset()
        
        return [
            self._parse_task(item)
            for item in self.dataset
            if item["repo"] == repo
        ]
    
    def list_repositories(self) -> list[tuple[str, int]]:
        """List all repositories and their task counts.
        
        Returns:
            List of (repo_name, count) tuples
        """
        if self.dataset is None:
            self.load_dataset()
        
        from collections import Counter
        repos = Counter(item["repo"] for item in self.dataset)
        return sorted(repos.items(), key=lambda x: x[1], reverse=True)
    
    def _parse_task(self, item: dict[str, Any]) -> SWEBenchTask:
        """Parse a dataset item into a SWEBenchTask.
        
        Args:
            item: Raw dataset item
            
        Returns:
            SWEBenchTask object
        """
        # Parse JSON fields if they're strings
        fail_to_pass = item.get("FAIL_TO_PASS")
        if isinstance(fail_to_pass, str):
            fail_to_pass = json.loads(fail_to_pass)
        
        pass_to_pass = item.get("PASS_TO_PASS")
        if isinstance(pass_to_pass, str):
            pass_to_pass = json.loads(pass_to_pass)
        
        return SWEBenchTask(
            instance_id=item["instance_id"],
            repo=item["repo"],
            base_commit=item["base_commit"],
            problem_statement=item["problem_statement"],
            patch=item["patch"],
            test_patch=item["test_patch"],
            hints_text=item.get("hints_text"),
            version=item.get("version"),
            environment_setup_commit=item.get("environment_setup_commit"),
            fail_to_pass=fail_to_pass,
            pass_to_pass=pass_to_pass,
            created_at=item.get("created_at"),
        )
    
    def save_task(self, task: SWEBenchTask, output_path: Path):
        """Save a task to a JSON file.
        
        Args:
            task: Task to save
            output_path: Path to output JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"✓ Saved task to {output_path}")


def main():
    """Example usage of the task reader."""
    reader = SWEBenchTaskReader()
    
    # Load dataset
    reader.load_dataset()
    
    # List repositories
    print("\nRepositories in dataset:")
    for repo, count in reader.list_repositories():
        print(f"  {repo}: {count} tasks")
    
    # Get first task
    print("\n" + "="*70)
    print("Example Task (index 0):")
    print("="*70)
    task = reader.get_task(0)
    print(f"Instance ID: {task.instance_id}")
    print(f"Repository: {task.repo}")
    print(f"Base commit: {task.base_commit[:8]}")
    print(f"\nProblem Statement:\n{task.problem_statement[:200]}...")
    
    # Show agent prompt
    print("\n" + "="*70)
    print("Agent Task Prompt:")
    print("="*70)
    print(task.to_agent_task()[:500] + "...")


if __name__ == "__main__":
    main()

