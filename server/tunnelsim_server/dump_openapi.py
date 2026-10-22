"""Print the API schema; the web app generates its TypeScript types from it."""

import json

from tunnelsim_server.app import app

print(json.dumps(app.openapi(), indent=2))
