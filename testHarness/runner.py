"""
Eval runner: orchestrates the LLM <-> tool call loop.

Feeds a task description to the LLM, executes tool calls against
SolidWorks via the InstrumentedServer, records everything, and
returns a complete EvalSession for grading.
"""

import time
import json
import subprocess
import logging
from testHarness.models import EvalSession, TaskSpec
from testHarness.middleware import InstrumentedServer
from testHarness.llm.base import LLMProvider
from testHarness.llm.tool_formatter import mcp_tools_to_openai_functions

logger = logging.getLogger(__name__)

MAX_TURNS = 50  # safety limit to prevent infinite loops

SYSTEM_PROMPT = """You are a CAD engineer using SolidWorks through MCP tools.
You will be given a task to create 3D geometry. Use the available tools to complete the task.

Important workflow rules:
- Always start with solidworks_new_part to create a fresh document
- Create a sketch on a plane before drawing sketch entities
- Exit sketch before creating features (extrusions exit sketch automatically)
- Use solidworks_get_edges / solidworks_get_faces to find coordinates for selection-based operations (fillet, chamfer, shell, etc.)
- All dimensions are in millimeters
- For cut-extrusions through the entire body, use endCondition "THROUGH_ALL"

When you have completed the task, respond with the text "TASK_COMPLETE" and nothing else.
If you cannot complete the task, respond with "TASK_FAILED: <reason>".
"""


def _get_git_info() -> tuple[str, str]:
    """Get current git commit hash and branch name."""
    commit = ""
    branch = ""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        pass
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        pass
    return commit, branch


class EvalRunner:
    """Orchestrates a single eval: LLM <-> tools <-> SolidWorks."""

    def __init__(self, provider: LLMProvider, server: InstrumentedServer):
        self.provider = provider
        self.server = server

    def run(self, spec: TaskSpec) -> EvalSession:
        """Run a single eval task and return the session record.

        Args:
            spec: Task specification defining what the LLM should build

        Returns:
            EvalSession with all tool calls, messages, and completion status
        """
        # Capture git info
        git_commit, git_branch = _get_git_info()

        session = EvalSession(
            task_id=spec.task_id,
            task_description=spec.description,
            model_name=self.provider.model_name(),
            git_commit=git_commit,
            git_branch=git_branch,
        )
        self.server.bind_session(session)

        # Prepare tools in OpenAI format
        mcp_tools = self.server.get_tool_definitions()
        openai_tools = mcp_tools_to_openai_functions(mcp_tools)

        # Build initial messages
        system_content = SYSTEM_PROMPT
        if spec.system_prompt_addendum:
            system_content += "\n\n" + spec.system_prompt_addendum

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": spec.description},
        ]

        # Reset SolidWorks state
        self.server.close_all_docs()
        self.server.reset_state()

        deadline = time.time() + spec.timeout_seconds
        turn = 0
        nudge_count = 0  # track how many times we've nudged the LLM

        try:
            while turn < MAX_TURNS and time.time() < deadline:
                turn += 1
                logger.info(f"[{spec.task_id}] Turn {turn}/{MAX_TURNS}")

                # Call LLM
                try:
                    response = self.provider.chat_completion(
                        messages=messages,
                        tools=openai_tools,
                        temperature=0.0,
                    )
                except Exception as e:
                    logger.error(f"[{spec.task_id}] LLM API error: {e}")
                    session.error = f"LLM API error: {e}"
                    break

                choice = response["choices"][0]
                message = choice["message"]
                finish_reason = choice.get("finish_reason", "stop")

                # Store assistant message in conversation
                messages.append(message)

                # Check for completion signal (text response, no tool calls)
                tool_calls = message.get("tool_calls")
                content = message.get("content", "") or ""

                if not tool_calls:
                    if "TASK_COMPLETE" in content:
                        session.completed = True
                        logger.info(f"[{spec.task_id}] Task completed by LLM")
                        break
                    elif "TASK_FAILED" in content:
                        session.completed = False
                        session.error = content
                        logger.info(f"[{spec.task_id}] Task failed by LLM: {content}")
                        break
                    else:
                        # LLM stopped without completing or making tool calls
                        nudge_count += 1
                        if nudge_count >= 3:
                            # Too many nudges, consider it done
                            logger.warning(f"[{spec.task_id}] LLM unresponsive after {nudge_count} nudges")
                            break
                        messages.append({
                            "role": "user",
                            "content": (
                                "Have you completed the task? If so, reply TASK_COMPLETE. "
                                "If not, continue working on the task."
                            ),
                        })
                        continue

                # Execute tool calls
                for tc in tool_calls:
                    func = tc["function"]
                    tool_name = func["name"]

                    try:
                        arguments = json.loads(func["arguments"])
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}

                    logger.info(f"  Tool: {tool_name}({json.dumps(arguments, default=str)[:200]})")

                    result = self.server.route_tool(tool_name, arguments)

                    logger.info(f"  Result: {result[:200]}")

                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                # Reset nudge counter since LLM made tool calls
                nudge_count = 0

            # Check timeout
            if time.time() >= deadline:
                session.timed_out = True
                logger.warning(f"[{spec.task_id}] Timed out after {spec.timeout_seconds}s")

            # Capture final state
            try:
                state_result = self.server.route_tool("solidworks_get_state", {})
                session.final_state = json.loads(state_result)
            except Exception as e:
                logger.warning(f"[{spec.task_id}] Failed to capture final state: {e}")

        except Exception as e:
            session.error = str(e)
            logger.error(f"[{spec.task_id}] Runner error: {e}", exc_info=True)

        session.end_time = time.time()
        session.llm_messages = messages

        return session
