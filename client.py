# client.py - MCP 计算器客户端
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def main():
    """MCP 客户端演示"""
    async with sse_client("http://127.0.0.1:8002/sse") as (read, write):
        async with ClientSession(read, write) as mcp_client:
            # 初始化客户端连接
            await mcp_client.initialize()
            
            # 获取可用工具列表
            tools = await mcp_client.list_tools()
            print(f"可用工具: {[tool.name for tool in tools.tools]}")
            print(tools.tools[0])
            
            # 测试加法：5 + 3
            result = await mcp_client.call_tool("5+2")
            print('5+3=', result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())