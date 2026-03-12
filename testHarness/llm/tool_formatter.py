"""
Converts MCP Tool definitions to OpenAI function-calling format.

MCP Tool has: name, description, inputSchema (JSON Schema dict)
OpenAI expects: {"type": "function", "function": {"name", "description", "parameters"}}

This is a thin mapping because MCP's inputSchema is already a JSON Schema
object with type, properties, and required -- exactly what OpenAI expects.
"""


def mcp_tools_to_openai_functions(mcp_tools: list) -> list[dict]:
    """Convert MCP Tool definitions to OpenAI function-calling format.

    Args:
        mcp_tools: List of MCP Tool objects (from module.get_tool_definitions())

    Returns:
        List of dicts in OpenAI tool format.
    """
    functions = []
    for tool in mcp_tools:
        func_def = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}},
            },
        }
        functions.append(func_def)
    return functions
