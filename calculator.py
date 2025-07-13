# server.py
from fastmcp import FastMCP
import math
import random
import datetime

# Create an MCP server
mcp = FastMCP("Calculator")

# Add an addition tool
@mcp.tool()
def calculator(python_expression: str) -> dict:
    """用于数学计算，始终使用此工具来计算Python表达式的结果。您可以直接使用'math'或'random'模块，无需import。"""
    result = eval(python_expression, {"math": math, "random": random, "datetime": datetime})
    print(f"Calculating formula: {python_expression}, result: {result}")
    return {"success": True, "result": result}

# Start the server
if __name__ == "__main__":
    print("Starting calculator server...")
    mcp.run(transport='sse', host="127.0.0.1", port=8002)
