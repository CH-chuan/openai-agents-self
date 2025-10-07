1. install basic vitrual environments and install dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

2. install apptainer image for testing purpose
```bash
python swebench_instances/build_test_instance.py
```

2.1 test if image can be activated
```bash
apptainer shell swebench_instances/images/swebench_sweb.eval.x86_64.astropy_1776_astropy-12907.sif
cd /testbed # this should enter the image root path, which contains a repo with a bug waiting for fixing
```

3. test if agent can use command lines in apptainer and basic tool relations
```bash
pip install pytest-asyncio
cd /home/cche/projects/openai-agents-self
export PYTHONPATH=$PWD:$PYTHONPATH
pytest sweagent/test/test_commands.py
pytest sweagent/test/test_agent.py
```

4. finishing above, we can now test on MCP servers, we choose to use official filesystem mcp server

a. install node.js if you do not have

```bash
# Download and run the setup script for Node.js 20.x (LTS)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Install Node.js (includes npm and npx)
sudo apt-get install -y nodejs

# Verify installation
node --version    # Should show v20.x.x
npm --version     # Should show 10.x.x
npx --version     # Should show 10.x.x
```

and test
```bash
# Create a test directory
cd /tmp
mkdir node-test && cd node-test

# Initialize a package.json
npm init -y

# Install a package
npm install lodash

# Use npx
npx cowsay "Node.js is installed!"
```

b. install filesystem mcp server locally
```bash
cd ~/projects/openai-agents-self

# Create MCP servers directory
mkdir -p mcp-servers/filesystem
cd mcp-servers/filesystem

# Initialize and install the filesystem server
npm init -y
npm install @modelcontextprotocol/server-filesystem

# Verify installation
npx @modelcontextprotocol/server-filesystem --help
```
