import os
import subprocess
import sys

port = os.getenv('PORT', '8000')
subprocess.run([
    sys.executable, '-m', 'uvicorn',
    'app:app',
    '--host', '0.0.0.0',
    '--port', str(port)
])
