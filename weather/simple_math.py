from mcp.server.fastmcp import FastMCP

# 初始化 MCP Server
mcp = FastMCP("simple_math")

@mcp.tool()
def add(a: float, b: float) -> float:
    """计算 a + b"""
    return a + b

@mcp.tool()
def subtract(a: float, b: float) -> float:
    """计算 a - b"""
    return a - b

@mcp.tool()
def multiply(a: float, b: float) -> float:
    """计算 a * b"""
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> float:
    """计算 a / b"""
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b

if __name__ == "__main__":
    mcp.run(transport="stdio")
