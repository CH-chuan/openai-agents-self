import subprocess
import os
from pathlib import Path

def pull_and_build_sif(instance_id="astropy__astropy-12907"):
    """
    Pull Docker image and convert to Apptainer .sif file
    """
    # Define the Docker image name
    instance_id = instance_id.replace("__", "_1776_")
    docker_image = f"swebench/sweb.eval.x86_64.{instance_id}"
    
    # Create images directory if it doesn't exist
    images_dir = Path("swebench_instances/images")
    images_dir.mkdir(exist_ok=True)
    
    # Define output .sif file path
    # Convert image name to valid filename (replace / with _)
    sif_filename = instance_id + ".sif"
    sif_path = images_dir / sif_filename
    
    print(f"Docker image: {docker_image}")
    print(f"Output path: {sif_path}")
    print(f"\nPulling and building container...")
    print("This may take several minutes depending on image size...\n")
    
    try:
        # Use apptainer pull to convert Docker image to .sif
        # Format: docker://image:tag
        result = subprocess.run(
            ['apptainer', 'pull', str(sif_path), f'docker://{docker_image}'],
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"✓ Successfully created {sif_path}")
        print(f"\nFile size: {os.path.getsize(sif_path) / (1024**3):.2f} GB")
        print(f"\nYou can use it with:")
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

if __name__ == "__main__":
    pull_and_build_sif()