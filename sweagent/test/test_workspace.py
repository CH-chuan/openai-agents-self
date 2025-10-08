"""Tests for workspace management functionality."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sweagent.workspace import WorkspaceManager, WorkspaceError, WorkspaceInfo


@pytest.fixture
def temp_workspace_dir(tmp_path):
    """Provide a temporary workspace directory."""
    workspace_base = tmp_path / "test_workspaces"
    workspace_base.mkdir()
    yield workspace_base
    # Cleanup after test
    if workspace_base.exists():
        shutil.rmtree(workspace_base)


@pytest.fixture
def workspace_manager(temp_workspace_dir):
    """Provide a WorkspaceManager instance."""
    return WorkspaceManager(base_dir=temp_workspace_dir)


def test_workspace_manager_init(temp_workspace_dir):
    """Test WorkspaceManager initialization."""
    manager = WorkspaceManager(base_dir=temp_workspace_dir)
    assert manager.base_dir == temp_workspace_dir


def test_create_workspace_structure(workspace_manager, temp_workspace_dir, tmp_path):
    """Test workspace directory structure creation."""
    # Create a minimal .sif mock
    sif_path = tmp_path / "test.sif"
    sif_path.write_text("mock sif file")
    
    # Mock the _copy_testbed_from_sif method to avoid actual apptainer calls
    with patch.object(
        WorkspaceManager,
        "_copy_testbed_from_sif",
        return_value=None,
    ):
        workspace_info = workspace_manager.create_workspace(
            instance_id="test__instance-123",
            model_name="gpt-4",
            sif_path=sif_path,
            timestamp="20250108_120000",
        )
    
    # Check workspace_info
    assert isinstance(workspace_info, WorkspaceInfo)
    assert workspace_info.instance_id == "test__instance-123"
    assert workspace_info.model_name == "gpt-4"
    assert workspace_info.timestamp == "20250108_120000"
    
    # Check directory structure
    assert workspace_info.workspace_dir.exists()
    assert workspace_info.testbed_dir.exists()
    assert workspace_info.outputs_dir.exists()
    assert (workspace_info.workspace_dir / "metadata.json").exists()
    
    # Check metadata content
    import json
    metadata = json.loads((workspace_info.workspace_dir / "metadata.json").read_text())
    assert metadata["instance_id"] == "test__instance-123"
    assert metadata["model_name"] == "gpt-4"
    assert metadata["timestamp"] == "20250108_120000"


def test_workspace_id_sanitization(workspace_manager, tmp_path):
    """Test that workspace IDs are properly sanitized for filesystem."""
    sif_path = tmp_path / "test.sif"
    sif_path.write_text("mock")
    
    with patch.object(WorkspaceManager, "_copy_testbed_from_sif", return_value=None):
        workspace_info = workspace_manager.create_workspace(
            instance_id="repo__issue-123",
            model_name="openai/gpt-4:latest",
            sif_path=sif_path,
            timestamp="20250108_120000",
        )
    
    # Check that special characters are replaced
    workspace_name = workspace_info.workspace_dir.name
    assert "__" not in workspace_name  # __ should be replaced with _
    assert "/" not in workspace_name   # / should be replaced
    assert ":" not in workspace_name   # : should be replaced


def test_cleanup_workspace(workspace_manager, tmp_path):
    """Test workspace cleanup."""
    sif_path = tmp_path / "test.sif"
    sif_path.write_text("mock")
    
    with patch.object(WorkspaceManager, "_copy_testbed_from_sif", return_value=None):
        workspace_info = workspace_manager.create_workspace(
            instance_id="test__cleanup",
            model_name="gpt-4",
            sif_path=sif_path,
        )
    
    assert workspace_info.workspace_dir.exists()
    
    # Clean up workspace
    workspace_manager.cleanup_workspace(workspace_info.workspace_dir)
    
    assert not workspace_info.workspace_dir.exists()


def test_list_workspaces(workspace_manager, tmp_path):
    """Test listing workspaces."""
    sif_path = tmp_path / "test.sif"
    sif_path.write_text("mock")
    
    # Initially empty
    assert len(workspace_manager.list_workspaces()) == 0
    
    # Create two workspaces
    with patch.object(WorkspaceManager, "_copy_testbed_from_sif", return_value=None):
        workspace_manager.create_workspace(
            instance_id="instance1",
            model_name="gpt-4",
            sif_path=sif_path,
            timestamp="20250108_120000",
        )
        workspace_manager.create_workspace(
            instance_id="instance2",
            model_name="gpt-4",
            sif_path=sif_path,
            timestamp="20250108_120001",
        )
    
    workspaces = workspace_manager.list_workspaces()
    assert len(workspaces) == 2


def test_get_workspace_metadata(workspace_manager, tmp_path):
    """Test reading workspace metadata."""
    sif_path = tmp_path / "test.sif"
    sif_path.write_text("mock")
    
    with patch.object(WorkspaceManager, "_copy_testbed_from_sif", return_value=None):
        workspace_info = workspace_manager.create_workspace(
            instance_id="test__metadata",
            model_name="gpt-4",
            sif_path=sif_path,
        )
    
    metadata = workspace_manager.get_workspace_metadata(workspace_info.workspace_dir)
    
    assert metadata["instance_id"] == "test__metadata"
    assert metadata["model_name"] == "gpt-4"
    assert "created_at" in metadata


def test_copy_testbed_error_handling(workspace_manager, tmp_path):
    """Test error handling when .sif file doesn't exist."""
    nonexistent_sif = tmp_path / "nonexistent.sif"
    
    with pytest.raises(WorkspaceError, match="Container image not found"):
        workspace_manager.create_workspace(
            instance_id="test__error",
            model_name="gpt-4",
            sif_path=nonexistent_sif,
        )


def test_workspace_bind_mount_paths(workspace_manager, tmp_path):
    """Test that workspace provides correct bind mount paths."""
    sif_path = tmp_path / "test.sif"
    sif_path.write_text("mock")
    
    with patch.object(WorkspaceManager, "_copy_testbed_from_sif", return_value=None):
        workspace_info = workspace_manager.create_workspace(
            instance_id="test__bindmount",
            model_name="gpt-4",
            sif_path=sif_path,
        )
    
    # Check that paths are absolute and exist
    assert workspace_info.testbed_dir.is_absolute()
    assert workspace_info.outputs_dir.is_absolute()
    assert workspace_info.testbed_dir.exists()
    assert workspace_info.outputs_dir.exists()
    
    # These should be suitable for bind mounts
    testbed_mount = f"{workspace_info.testbed_dir.absolute()}:/testbed"
    outputs_mount = f"{workspace_info.outputs_dir.absolute()}:/outputs"
    
    assert ":" in testbed_mount
    assert ":" in outputs_mount

