import os
import re
import random
import subprocess
import yaml
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from datasets import load_dataset


class SWEBenchInstance:
    """Represents a single SWE-bench instance with all its data."""
    
    def __init__(
        self,
        instance_id: str,
        problem_statement: str,
        base_commit: str,
        patch: str = "",
        test_patch: str = "",
        repo: str = "",
        created_at: str = "",
        hints_text: str = "",
        hints_code: str = "",
        environment_setup_commit: str = "",
        test_file_path: str = "",
        test_cases: str = "",
        test_line_numbers: str = "",
        test_type: str = "",
        test_directives: str = "",
        test_timeout: int = 0,
        installation_script: str = "",
        pre_install_script: str = "",
        post_install_script: str = "",
        test_script: str = "",
        image_name: str = "",
    ):
        self.instance_id = instance_id
        self.problem_statement = problem_statement
        self.base_commit = base_commit
        self.patch = patch
        self.test_patch = test_patch
        self.repo = repo
        self.created_at = created_at
        self.hints_text = hints_text
        self.hints_code = hints_code
        self.environment_setup_commit = environment_setup_commit
        self.test_file_path = test_file_path
        self.test_cases = test_cases
        self.test_line_numbers = test_line_numbers
        self.test_type = test_type
        self.test_directives = test_directives
        self.test_timeout = test_timeout
        self.installation_script = installation_script
        self.pre_install_script = pre_install_script
        self.post_install_script = post_install_script
        self.test_script = test_script
        self.image_name = image_name or self._generate_image_name()
    
    def _generate_image_name(self) -> str:
        """Generate Docker image name from instance ID."""
        docker_compatible_id = self.instance_id.replace("__", "_1776_")
        return f"swebench/sweb.eval.x86_64.{docker_compatible_id}:latest"
    
    @classmethod
    def from_dataset_item(cls, item: Dict[str, Any]) -> "SWEBenchInstance":
        """Create SWEBenchInstance from HuggingFace dataset item."""
        return cls(
            instance_id=item["instance_id"],
            problem_statement=item["problem_statement"],
            base_commit=item["base_commit"],
            patch=item.get("patch", ""),
            test_patch=item.get("test_patch", ""),
            repo=item.get("repo", ""),
            created_at=item.get("created_at", ""),
            hints_text=item.get("hints_text", ""),
            hints_code=item.get("hints_code", ""),
            environment_setup_commit=item.get("environment_setup_commit", ""),
            test_file_path=item.get("test_file_path", ""),
            test_cases=item.get("test_cases", ""),
            test_line_numbers=item.get("test_line_numbers", ""),
            test_type=item.get("test_type", ""),
            test_directives=item.get("test_directives", ""),
            test_timeout=item.get("test_timeout", 0),
            installation_script=item.get("installation_script", ""),
            pre_install_script=item.get("pre_install_script", ""),
            post_install_script=item.get("post_install_script", ""),
            test_script=item.get("test_script", ""),
            image_name=item.get("image_name", ""),
        )
    
    def __str__(self) -> str:
        return f"SWEBenchInstance(id={self.instance_id}, repo={self.repo})"
    
    def __repr__(self) -> str:
        return self.__str__()


class SWEBenchInstances:
    """Simple class to load and manage SWE-bench instances."""

    def __init__(
        self,
        subset: Literal["lite", "verified", "full"] = "lite",
        split: Literal["dev", "test"] = "dev",
        filter_pattern: str = ".*",
        slice_spec: str = "",
        shuffle: bool = False
    ):
        self.subset = subset
        self.split = split
        self.filter_pattern = filter_pattern
        self.slice_spec = slice_spec
        self.shuffle = shuffle

    def _get_dataset_name(self) -> str:
        """Get the HuggingFace dataset name based on subset."""
        dataset_map = {
            "full": "princeton-nlp/SWE-Bench",
            "verified": "princeton-nlp/SWE-Bench_Verified", 
            "lite": "princeton-nlp/SWE-Bench_Lite"
        }
        if self.subset not in dataset_map:
            raise ValueError(f"Unsupported subset: {self.subset}")
        return dataset_map[self.subset]

    def get_instances(self) -> List[SWEBenchInstance]:
        """Load SWE-bench instances from dataset."""
        dataset = load_dataset(self._get_dataset_name(), split=self.split)
        
        # Convert dataset items to SWEBenchInstance objects
        instances = [SWEBenchInstance.from_dataset_item(item) for item in dataset]
        
        # Apply filtering
        if self.filter_pattern != ".*":
            instances = [inst for inst in instances if re.match(self.filter_pattern, inst.instance_id)]
        
        # Apply shuffling
        if self.shuffle:
            random.seed(42)
            random.shuffle(instances)
        
        # Apply slicing
        if self.slice_spec:
            instances = instances[self._parse_slice(self.slice_spec)]
        
        return instances
    
    def get_instance_ids(self) -> List[str]:
        """Load instance IDs from SWE-bench dataset (convenience method)."""
        instances = self.get_instances()
        return [inst.instance_id for inst in instances]

    def _parse_slice(self, slice_spec: str) -> slice:
        """Parse slice specification string into slice object."""
        if not slice_spec:
            return slice(None)
        
        parts = slice_spec.split(":")
        values = [None if p == "" else int(p) for p in parts]
        
        if len(parts) == 1:
            return slice(values[0])
        elif len(parts) == 2:
            return slice(values[0], values[1])
        elif len(parts) == 3:
            return slice(values[0], values[1], values[2])
        else:
            raise ValueError(f"Invalid slice specification: {slice_spec}")

    @classmethod
    def from_config_file(cls, config_path: str = "swebench_instances/task_config.yaml") -> "SWEBenchInstances":
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        instances_config = config["instances"]
        return cls(
            subset=instances_config["subset"],
            split=instances_config["split"],
            filter_pattern=instances_config["filter"],
            slice_spec=instances_config["slice"],
            shuffle=instances_config["shuffle"]
        )



def pull_and_build_sif(instance_id: str, output_dir: str = "swebench_instances/images") -> Optional[str]:
    """
    Pull Docker image and convert to Apptainer .sif file.
    
    Args:
        instance_id: SWE-bench instance ID (e.g., "astropy__astropy-12907")
        output_dir: Directory to save the .sif file
        
    Returns:
        Path to the created .sif file, or None if failed
    """
    # Convert instance ID to Docker-compatible format
    docker_instance_id = instance_id.replace("__", "_1776_")
    docker_image = f"swebench/sweb.eval.x86_64.{docker_instance_id}"
    
    # Setup output directory and file path
    images_dir = Path(output_dir)
    images_dir.mkdir(exist_ok=True)
    sif_path = images_dir / f"{docker_instance_id}.sif"

    # skip if the sif file already exists
    if sif_path.exists():
        print(f"SIF file already exists: {sif_path}")
        return str(sif_path)
    
    print(f"Docker image: {docker_image}")
    print(f"Output path: {sif_path}")
    print(f"Pulling and building container...")
    print("This may take several minutes depending on image size...\n")
    
    try:
        # Use apptainer pull to convert Docker image to .sif
        result = subprocess.run(
            ['apptainer', 'pull', str(sif_path), f'docker://{docker_image}'],
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"✓ Successfully created {sif_path}")
        print(f"File size: {os.path.getsize(sif_path) / (1024**3):.2f} GB")
        print(f"\nUsage:")
        print(f"  apptainer shell {sif_path}")
        print(f"  apptainer exec {sif_path} <command>")
        
        return str(sif_path)
        
    except subprocess.CalledProcessError as e:
        print(f"Error building container:")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return None
        
    except FileNotFoundError:
        print("Error: Apptainer is not installed or not in PATH")
        print("Install with: sudo apt-get install apptainer")
        return None


def build_containers_from_config(config_path: str = "swebench_instances/task_config.yaml") -> List[str]:
    """
    Build containers for all instances specified in the config file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        List of successfully created .sif file paths
    """
    swe_bench = SWEBenchInstances.from_config_file(config_path)
    instances = swe_bench.get_instances()
    
    print(f"Building containers for {len(instances)} instances...")
    successful_builds = []
    
    for i, instance in enumerate(instances, 1):
        print(f"\n[{i}/{len(instances)}] Processing {instance.instance_id}")
        sif_path = pull_and_build_sif(instance.instance_id)
        if sif_path:
            successful_builds.append(sif_path)
    
    print(f"\n✓ Successfully built {len(successful_builds)}/{len(instances)} containers")
    return successful_builds


if __name__ == "__main__":
    # Example usage
    print("SWE-bench Instance Manager")
    print("=" * 30)
    
    # Load instances from config
    swe_bench = SWEBenchInstances.from_config_file()
    instances = swe_bench.get_instances()
    
    print(f"Found {len(instances)} instances:")
    for instance in instances:
        print(f"  - {instance.instance_id} ({instance.repo})")
        print(f"    Problem: {instance.problem_statement[:100]}...")
        print(f"    Image: {instance.image_name}")
        print()
    
    # Build containers for all instances
    if instances:
        print(f"Building containers...")
        successful_builds = build_containers_from_config()
        print(f"Successfully built {len(successful_builds)} containers")
