"""Work the queue: uv run -m agent, or uv run -m agent CLM-1001 CLM-1003"""

import sys

from agent.main import work_queue

work_queue(sys.argv[1:])
