"""MCP Client for testing stdio communication with BigQuery MCP server."""

import asyncio
import json
import os
import subprocess
import uuid
from typing import Any


class MCPClient:
    """JSON-RPC 2.0 client for communicating with MCP servers via stdio."""

    def __init__(self, server_command: list[str], env: dict[str, str] | None = None):
        """Initialize MCP client with server command.

        Args:
            server_command: Command to start the server (e.g., ["uv", "run", "python", "-m", "src.server"])
            env: Environment variables for the server process
        """
        self.server_command = server_command
        self.env = env
        self.process: subprocess.Popen | None = None
        self.initialized = False
        self.capabilities: dict[str, Any] = {}

    async def start_server(self) -> None:
        """Start the MCP server process."""
        # Inherit current environment and add/override with provided env
        full_env = os.environ.copy() if self.env else os.environ
        if self.env:
            full_env.update(self.env)

        self.process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=full_env,
        )

    async def stop_server(self) -> None:
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(asyncio.create_task(self._wait_for_process()), timeout=5.0)
            except TimeoutError:
                self.process.kill()
                await asyncio.create_task(self._wait_for_process())
            finally:
                self.process = None
                self.initialized = False

    async def _wait_for_process(self) -> None:
        """Wait for process to terminate (async wrapper for wait())."""
        if self.process:
            # Run the blocking wait() in a thread
            await asyncio.to_thread(self.process.wait)

    def _send_request(
        self, method: str, params: dict[str, Any] | None = None, request_id: str | int | None = None
    ) -> None:
        """Send a JSON-RPC request to the server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Server not started")

        if request_id is None:
            request_id = str(uuid.uuid4())

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }

        if params is not None:
            message["params"] = params

        json_message = json.dumps(message) + "\n"
        self.process.stdin.write(json_message)
        self.process.stdin.flush()

    def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Server not started")

        message = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params is not None:
            message["params"] = params

        json_message = json.dumps(message) + "\n"
        self.process.stdin.write(json_message)
        self.process.stdin.flush()

    def _read_response(self, timeout: float = 10.0) -> dict[str, Any]:
        """Read a JSON-RPC response from the server."""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Server not started")

        # Read line from stdout
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Server process ended unexpectedly")

        try:
            return json.loads(line.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from server: {line}") from e

    async def initialize(self) -> dict[str, Any]:
        """Initialize the MCP session."""
        if self.initialized:
            return self.capabilities

        # Send initialization request
        self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {"name": "mcp-test-client", "version": "1.0.0"},
            },
            "init",
        )

        # Read initialization response
        response = self._read_response()

        if "error" in response:
            raise RuntimeError(f"Initialization failed: {response['error']}")

        self.capabilities = response.get("result", {}).get("capabilities", {})

        # Send initialized notification
        self._send_notification("notifications/initialized")

        self.initialized = True
        return self.capabilities

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the server."""
        if not self.initialized:
            await self.initialize()

        self._send_request("tools/list", {}, "list_tools")
        response = self._read_response()

        if "error" in response:
            raise RuntimeError(f"Failed to list tools: {response['error']}")

        return response.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a specific tool with arguments."""
        if not self.initialized:
            await self.initialize()

        request_id = f"call_{name}_{uuid.uuid4()}"
        self._send_request("tools/call", {"name": name, "arguments": arguments}, request_id)

        response = self._read_response()

        if "error" in response:
            raise RuntimeError(f"Tool call failed: {response['error']}")

        return response.get("result", {})

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources from the server."""
        if not self.initialized:
            await self.initialize()

        self._send_request("resources/list", {}, "list_resources")
        response = self._read_response()

        if "error" in response:
            raise RuntimeError(f"Failed to list resources: {response['error']}")

        return response.get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a specific resource by URI."""
        if not self.initialized:
            await self.initialize()

        self._send_request("resources/read", {"uri": uri}, f"read_resource_{uuid.uuid4()}")

        response = self._read_response()

        if "error" in response:
            raise RuntimeError(f"Failed to read resource: {response['error']}")

        return response.get("result", {})

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_server()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_server()
