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


