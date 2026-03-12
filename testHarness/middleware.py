"""
Instrumented MCP server wrapper for recording tool calls.

Wraps SolidWorksMCPServer and intercepts every _route_tool() call
to record timing, inputs, outputs, and success/failure in an EvalSession.
"""

import sys
import os
import time
import json
import logging

# Add project root to path so we can import server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testHarness.models import ToolCall, EvalSession
from typing import Optional

logger = logging.getLogger(__name__)


class InstrumentedServer:
    """Wraps SolidWorksMCPServer, intercepting _route_tool to log all calls."""

    def __init__(self):
        from server import SolidWorksMCPServer
        self.server = SolidWorksMCPServer()
        self.session: Optional[EvalSession] = None
        self._call_counter = 0

    def bind_session(self, session: EvalSession):
        """Bind an EvalSession to start recording tool calls."""
        self.session = session
        self._call_counter = 0

    def route_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool call, recording it in the bound session."""
        start = time.time()
        success = True
        error = None
        output = ""

        # Ensure connection before routing
        if not self.server.connection.app:
            if not self.server.connection.connect():
                output = "\u274c Failed to connect to SolidWorks"
                call = ToolCall(
                    tool_name=name,
                    inputs=arguments,
                    output=output,
                    timestamp=start,
                    duration_ms=(time.time() - start) * 1000,
                    success=False,
                    error="Failed to connect to SolidWorks",
                    call_index=self._call_counter,
                )
                self._call_counter += 1
                if self.session:
                    self.session.tool_calls.append(call)
                return output

        try:
            output = self.server._route_tool(name, arguments)
            # Determine success from output format
            success = self._check_success(output)
            if not success:
                error = self._extract_error(output)
        except Exception as e:
            success = False
            error = str(e)
            output = f"\u274c Error: {e}"

        duration_ms = (time.time() - start) * 1000

        call = ToolCall(
            tool_name=name,
            inputs=arguments,
            output=output,
            timestamp=start,
            duration_ms=duration_ms,
            success=success,
            error=error,
            call_index=self._call_counter,
        )
        self._call_counter += 1

        if self.session:
            self.session.tool_calls.append(call)

        return output

    def get_tool_definitions(self) -> list:
        """Return all MCP tool definitions from the underlying server."""
        tools = []
        for module in self.server._modules:
            tools.extend(module.get_tool_definitions())
        return tools

    def close_all_docs(self):
        """Close all open SolidWorks documents without saving."""
        sw = self.server.connection.app
        if sw:
            try:
                sw.CloseAllDocuments(True)
            except Exception:
                while True:
                    doc = sw.ActiveDoc
                    if not doc:
                        break
                    try:
                        sw.QuitDoc(doc.GetTitle())
                    except Exception:
                        break

    def reset_state(self):
        """Reset the state tracker for a fresh run."""
        self.server.tracker.reset()

    @staticmethod
    def _check_success(output: str) -> bool:
        """Determine if a tool call succeeded from its output."""
        if not output:
            return False

        # Try JSON format first: {"result": "\u2713 ...", ...}
        if output.startswith("{"):
            try:
                parsed = json.loads(output)
                result_str = parsed.get("result", "")
                return result_str.startswith("\u2713")
            except (json.JSONDecodeError, AttributeError):
                pass

        # Plain string: starts with checkmark
        return output.startswith("\u2713")

    @staticmethod
    def _extract_error(output: str) -> Optional[str]:
        """Extract error message from a failed tool output."""
        if not output:
            return "Empty output"

        if output.startswith("{"):
            try:
                parsed = json.loads(output)
                result_str = parsed.get("result", "")
                if result_str.startswith("\u274c"):
                    return result_str
            except (json.JSONDecodeError, AttributeError):
                pass

        if output.startswith("\u274c"):
            return output

        return None
