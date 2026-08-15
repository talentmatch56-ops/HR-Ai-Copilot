import os
import sys
import json
import logging
import asyncio
from typing import List, Dict, Any

# Ensure mcp-server is in path so we can import it
server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp-server"))
if server_dir not in sys.path:
    sys.path.append(server_dir)

logger = logging.getLogger("mcp_client")

class MCPClient:
    def __init__(self):
        self.tools = {}
        self.load_tools()

    def load_tools(self):
        try:
            # Import the FastMCP server instance dynamically
            from server import mcp as mcp_server
            self.mcp_server = mcp_server
            
            # Map tools into a local registry
            # FastMCP list_tools might be async
            try:
                tools = asyncio.run(mcp_server.list_tools())
            except RuntimeError:
                loop = asyncio.get_event_loop()
                tools = loop.run_until_complete(mcp_server.list_tools())
            except TypeError:
                tools = mcp_server.list_tools()

            for tool_obj in tools:
                self.tools[tool_obj.name] = tool_obj
            logger.info(f"Loaded {len(self.tools)} tools from MCP server.")
        except Exception as e:
            logger.error(f"Failed to load MCP server tools: {e}")

    def get_openai_tool_schemas(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI format."""
        schemas = []
        for name, tool in self.tools.items():
            # Generate OpenAI function calling schema
            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description or f"Execute tool {name}",
                    "parameters": getattr(tool, "parameters", {"type": "object", "properties": {}})
                }
            }
            # Remove pydantic internal definitions if any
            if "title" in schema["function"]["parameters"]:
                del schema["function"]["parameters"]["title"]
            schemas.append(schema)
        return schemas

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool through the MCP registry."""
        logger.info(f"Executing MCP tool '{name}' with arguments: {arguments}")
        if name not in self.tools:
            return {"status": "error", "message": f"Tool {name} not found in MCP server."}
        
        try:
            # Use FastMCP's built-in call_tool which handles the execution properly
            result = await self.mcp_server.call_tool(name, arguments)
            
            if hasattr(result, "is_error") and result.is_error:
                error_text = result.content[0].text if result.content else "Unknown Error"
                return {"status": "error", "message": error_text}
                
            if hasattr(result, "content") and result.content:
                res_str = result.content[0].text
            else:
                res_str = str(result)
            
            # Parse response as JSON if possible, otherwise return string
            try:
                return json.loads(res_str)
            except:
                return {"result": res_str}
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {"status": "error", "message": str(e)}

mcp_client = MCPClient()
