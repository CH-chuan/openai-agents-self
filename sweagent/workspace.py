"""Workspace management for isolated instance execution.

This module provides workspace lifecycle management for SWE-agent instances.
Each instance gets an isolated workspace where both MCP and Apptainer container
access the same physical files via bind mounts.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from sweagent.sweagent_logging import logger, write_json_log


class WorkspaceError(RuntimeError):
    """Raised when workspace operations fail."""


@dataclass
class WorkspaceInfo:
    """Information about a created workspace."""

    workspace_dir: Path
    testbed_dir: Path
    outputs_dir: Path
    instance_id: str
    model_name: str
    timestamp: str
    sif_path: Path


class WorkspaceManager:
    """Manages workspace lifecycle for instance isolation.
    
    Architecture:
        HOST filesystem:
          workspaces/
            └── {timestamp}_{model}_{instance}/
                ├── testbed/        # Copied from .sif, bind-mounted to container
                ├── outputs/        # Agent outputs, logs
                └── metadata.json   # Run metadata
        
        CONTAINER filesystem:
          /testbed/    ← Bind mounted to HOST workspace/testbed/
          /outputs/    ← Bind mounted to HOST workspace/outputs/
        
        MCP server:
          Allowed directory: workspace/testbed/  (same as container)
    """

    def __init__(self, base_dir: Path = Path("workspaces")):
        """Initialize workspace manager.
        
        Args:
            base_dir: Base directory for all workspaces (default: "workspaces")
        """
        self.base_dir = base_dir

    def create_workspace(
        self,
        instance_id: str,
        model_name: str,
        sif_path: Path,
        *,
        timestamp: Optional[str] = None,
    ) -> WorkspaceInfo:
        """Create and initialize a new workspace for an instance.
        
        This method:
        1. Creates workspace directory structure
        2. Copies /testbed from .sif to workspace/testbed
        3. Saves metadata
        
        Args:
            instance_id: Instance identifier (e.g., "astropy__astropy-12907")
            model_name: Model name (e.g., "gpt-4", "openai/gpt-oss-20b")
            sif_path: Path to the .sif container image
            timestamp: Optional custom timestamp (default: current time)
            
        Returns:
            WorkspaceInfo with paths to created workspace
            
        Raises:
            WorkspaceError: If workspace creation or initialization fails
        """
        # Generate workspace ID
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sanitize names for filesystem
        safe_instance = instance_id.replace("__", "_").replace("/", "_")
        safe_model = model_name.replace("/", "_").replace(":", "_")
        workspace_id = f"{timestamp}_{safe_model}_{safe_instance}"
        
        workspace_dir = self.base_dir / workspace_id
        testbed_dir = workspace_dir / "testbed"
        outputs_dir = workspace_dir / "outputs"
        
        logger.info(
            "Creating workspace",
            extra={
                "workspace_id": workspace_id,
                "instance_id": instance_id,
                "model": model_name,
            }
        )
        
        try:
            # Create directory structure
            testbed_dir.mkdir(parents=True, exist_ok=True)
            outputs_dir.mkdir(parents=True, exist_ok=True)
            
            # Bootstrap testbed from container
            self._copy_testbed_from_sif(sif_path, testbed_dir)
            
            # Save metadata with relative path from project root
            try:
                # Try to make path relative to current working directory (project root)
                relative_sif_path = sif_path.absolute().relative_to(Path.cwd())
                sif_path_str = str(relative_sif_path)
            except ValueError:
                # If sif_path is outside project root, keep absolute path
                sif_path_str = str(sif_path.absolute())
            
            metadata = {
                "instance_id": instance_id,
                "model_name": model_name,
                "timestamp": timestamp,
                "workspace_id": workspace_id,
                "sif_path": sif_path_str,
                "created_at": datetime.now().isoformat(),
            }
            
            metadata_path = workspace_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))
            
            # Log workspace creation
            write_json_log(
                Path("logs/sweagent_workspace.jsonl"),
                {
                    "event": "workspace_created",
                    "workspace_id": workspace_id,
                    "workspace_dir": str(workspace_dir.absolute()),
                    "instance_id": instance_id,
                    "model": model_name,
                }
            )
            
            logger.info(
                "Workspace created successfully",
                extra={
                    "workspace_dir": str(workspace_dir.absolute()),
                    "testbed_dir": str(testbed_dir.absolute()),
                }
            )
            
            return WorkspaceInfo(
                workspace_dir=workspace_dir,
                testbed_dir=testbed_dir,
                outputs_dir=outputs_dir,
                instance_id=instance_id,
                model_name=model_name,
                timestamp=timestamp,
                sif_path=sif_path,
            )
            
        except Exception as e:
            logger.error(
                "Failed to create workspace",
                extra={
                    "workspace_id": workspace_id,
                    "error": str(e),
                }
            )
            # Clean up partial workspace on failure
            if workspace_dir.exists():
                try:
                    shutil.rmtree(workspace_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up workspace: {cleanup_error}")
            
            raise WorkspaceError(
                f"Failed to create workspace for {instance_id}: {e}"
            ) from e

    def _copy_testbed_from_sif(self, sif_path: Path, testbed_dir: Path) -> None:
        """Copy /testbed directory from .sif container to workspace.
        
        Args:
            sif_path: Path to .sif container image
            testbed_dir: Destination directory for testbed contents
            
        Raises:
            WorkspaceError: If copy operation fails
        """
        if not sif_path.exists():
            raise WorkspaceError(f"Container image not found: {sif_path}")
        
        logger.info(
            "Copying testbed from container",
            extra={
                "sif_path": str(sif_path),
                "dest": str(testbed_dir),
            }
        )
        
        try:
            # Use apptainer exec to copy files from container to host
            # The -c flag copies recursively, preserving permissions
            result = subprocess.run(
                [
                    "apptainer",
                    "exec",
                    str(sif_path),
                    "sh",
                    "-c",
                    f"cp -r /testbed/. {testbed_dir}/",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for large repos
            )
            
            if result.returncode != 0:
                raise WorkspaceError(
                    f"Copy failed with exit code {result.returncode}: {result.stderr}"
                )
            
            logger.info("Testbed copied successfully")
            
        except subprocess.TimeoutExpired as e:
            raise WorkspaceError(
                "Timeout while copying testbed from container"
            ) from e
        except subprocess.CalledProcessError as e:
            raise WorkspaceError(
                f"Failed to copy testbed: {e.stderr}"
            ) from e
        except Exception as e:
            raise WorkspaceError(
                f"Unexpected error copying testbed: {e}"
            ) from e

    def cleanup_workspace(self, workspace_dir: Path, *, force: bool = False) -> None:
        """Remove a workspace directory.
        
        Args:
            workspace_dir: Path to workspace directory to remove
            force: If True, ignore errors during removal
            
        Raises:
            WorkspaceError: If removal fails and force=False
        """
        if not workspace_dir.exists():
            logger.warning(f"Workspace does not exist: {workspace_dir}")
            return
        
        logger.info("Cleaning up workspace", extra={"workspace_dir": str(workspace_dir)})
        
        try:
            shutil.rmtree(workspace_dir)
            
            write_json_log(
                Path("logs/sweagent_workspace.jsonl"),
                {
                    "event": "workspace_removed",
                    "workspace_dir": str(workspace_dir),
                }
            )
            
            logger.info("Workspace removed successfully")
            
        except Exception as e:
            logger.error(f"Failed to remove workspace: {e}")
            if not force:
                raise WorkspaceError(
                    f"Failed to remove workspace {workspace_dir}: {e}"
                ) from e

    def list_workspaces(self) -> list[Path]:
        """List all workspace directories.
        
        Returns:
            List of workspace directory paths
        """
        if not self.base_dir.exists():
            return []
        
        return [
            d for d in self.base_dir.iterdir()
            if d.is_dir() and (d / "metadata.json").exists()
        ]

    def get_workspace_metadata(self, workspace_dir: Path) -> dict:
        """Read metadata from a workspace.
        
        Args:
            workspace_dir: Path to workspace directory
            
        Returns:
            Metadata dictionary
            
        Raises:
            WorkspaceError: If metadata cannot be read
        """
        metadata_path = workspace_dir / "metadata.json"
        
        if not metadata_path.exists():
            raise WorkspaceError(f"No metadata found in {workspace_dir}")
        
        try:
            return json.loads(metadata_path.read_text())
        except Exception as e:
            raise WorkspaceError(
                f"Failed to read metadata from {workspace_dir}: {e}"
            ) from e

    def cleanup_old_workspaces(
        self,
        max_age_hours: int = 24,
        *,
        dry_run: bool = False,
    ) -> list[Path]:
        """Remove workspaces older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours (default: 24)
            dry_run: If True, only report what would be deleted
            
        Returns:
            List of workspaces that were (or would be) removed
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed = []
        
        for workspace_dir in self.list_workspaces():
            try:
                metadata = self.get_workspace_metadata(workspace_dir)
                created_at = datetime.fromisoformat(metadata.get("created_at", ""))
                
                if created_at < cutoff_time:
                    if dry_run:
                        logger.info(
                            f"Would remove old workspace: {workspace_dir}"
                        )
                    else:
                        self.cleanup_workspace(workspace_dir, force=True)
                    
                    removed.append(workspace_dir)
                    
            except Exception as e:
                logger.warning(
                    f"Error processing workspace {workspace_dir}: {e}"
                )
        
        return removed

