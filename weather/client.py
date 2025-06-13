import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack
import httpx
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        transport = httpx.AsyncHTTPTransport(proxy=None)  # 明确禁用代理
        self.client = httpx.AsyncClient(transport=transport)
        self.deepseek_api_url = "https://api.deepseek.com/v1"  # Update with actual DeepSeek API URL
        self.deepseek_api_key = "sk-f0904a96b7654c8d811ec4ffefc88bd1"  # Set from environment variables

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def deepseek_chat(self, messages: list, tools: list = None) -> dict:
        """Call DeepSeek Chat API"""
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 1000,
        }
        
        if tools:
            # 按照 DeepSeek API 要求的格式转换工具定义
            formatted_tools = [{
                "type": "function",  # 必须包含的字段
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {})
                }
            } for tool in tools]
            
            payload["tools"] = formatted_tools
        
        try:
            response = await self.client.post(
                f"{self.deepseek_api_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"DeepSeek API error: {e.response.text}")
            raise

    async def process_query(self, query: str) -> str:
        """Process a query using DeepSeek and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{ 
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial DeepSeek API call
        deepseek_response = await self.deepseek_chat(
            messages=messages,
            tools=available_tools if available_tools else None
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        for choice in deepseek_response.get('choices', []):
            message = choice.get('message', {})
            if 'content' in message:
                final_text.append(message['content'])
            
            # Handle tool calls if present
            if 'tool_calls' in message:
                for tool_call in message['tool_calls']:
                    tool_name = tool_call['function']['name']
                    tool_args = json.loads(tool_call['function']['arguments'])
                    
                    # Execute tool call
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_results.append({"call": tool_name, "result": result})
                    final_text.append(f"[Called tool {tool_name} with args {tool_args}]")

                    # Continue conversation with tool results
                    messages.append({
                        "role": "assistant",
                        "content": message.get('content', '')
                    })
                    messages.append({
                        "role": "user", 
                        "content": str(result.content)
                    })

                    # Get next response from DeepSeek
                    deepseek_response = await self.deepseek_chat(
                        messages=messages,
                        tools=available_tools if available_tools else None
                    )

                    if deepseek_response.get('choices'):
                        final_text.append(deepseek_response['choices'][0]['message']['content'])

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
        await self.client.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())