"""API route collection.

This module intentionally avoids importing submodules at package import time so
that tests can import specific route modules (e.g. `backend.api.routes.context`)
without pulling in other routes that may depend on DB connections.
"""

__all__ = [
	"slow_queries",
	"analyze",
	"stats",
	"ai_analysis",
	"context",
	"ideas",
]

