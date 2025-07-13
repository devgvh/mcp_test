import json
import logging
from openai import OpenAI
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import asyncio

# 配置字典
CONFIG = {
    "model": "qwen-plus-latest",
    "api_key": "sk-20f7584670174ecdb0a2e555b9c----", #这里要替换你自己的api_key，可以在阿里云申请
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
    "mcp_url": "http://127.0.0.1:8001/sse"
}

class LLMClient:
    """LLM客户端，负责与大语言模型API通信"""
    def __init__(self, model_name: str, url: str, api_key: str) -> None:
        self.model_name: str = model_name
        self.url: str = url
        self.client = OpenAI(api_key=api_key, base_url=url)

    def get_response(self, messages: list[dict[str, str]]) -> str:
        """发送消息给LLM并获取响应"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content


class ChatSession:
    """聊天会话，处理用户输入和LLM响应，并与MCP工具交互"""
    def __init__(self, llm_client: LLMClient, mcp_client: ClientSession, ) -> None:
        self.mcp_client: ClientSession = mcp_client
        self.llm_client: LLMClient = llm_client

    async def process_llm_response(self, llm_response: str) -> str:
        """处理LLM响应，解析工具调用并执行"""
        try:
            # 尝试移除可能的markdown格式
            if llm_response.startswith('```json'):
                llm_response = llm_response.strip('```json').strip('```').strip()
            tool_call = json.loads(llm_response)
            if "tool" in tool_call and "arguments" in tool_call:
                # 检查工具是否可用
                tools = await self.mcp_client.list_tools()
                if any(tool.name == tool_call["tool"] for tool in tools.tools):
                    try:
                        # 执行工具调用
                        result = await self.mcp_client.call_tool(
                            tool_call["tool"], tool_call["arguments"]
                        )

                        return f"Tool execution result: {result}"
                    except Exception as e:
                        error_msg = f"Error executing tool: {str(e)}"
                        logging.error(error_msg)
                        return error_msg
                return f"No server found with tool: {tool_call['tool']}"
            return llm_response
        except json.JSONDecodeError:
            # 如果不是JSON格式，直接返回原始响应
            return llm_response

    async def start(self, system_message) -> None:
        """启动聊天会话的主循环"""
        messages = [{"role": "system", "content": system_message}]
        while True:
            try:
                # 获取用户输入
                user_input = input("用户: ").strip().lower()
                if user_input in ["quit", "exit", "退出"]:
                    print('AI助手退出')
                    break
                messages.append({"role": "user", "content": user_input})

                # 获取LLM的初始响应
                llm_response = self.llm_client.get_response(messages)
                print("助手: ", llm_response)

                # 处理可能的工具调用
                result = await self.process_llm_response(llm_response)

                # 如果处理结果与原始响应不同，说明执行了工具调用，需要进一步处理
                while result != llm_response:
                    messages.append({"role": "assistant", "content": llm_response})
                    messages.append({"role": "system", "content": result})

                    # 将工具执行结果发送回LLM获取新响应
                    llm_response = self.llm_client.get_response(messages)
                    result = await self.process_llm_response(llm_response)
                    print("助手: ", llm_response)

                messages.append({"role": "assistant", "content": llm_response})

            except KeyboardInterrupt:
                print('AI助手退出')
                break


async def main():
    async with sse_client(CONFIG["mcp_url"]) as (read, write):
        async with ClientSession(read, write) as mcp_client:
            await mcp_client.initialize()
            # 初始化LLM客户端，使用通义千问模型
            llm_client = LLMClient(model_name=CONFIG["model"], api_key=CONFIG["api_key"],
                                   url=CONFIG["base_url"])

            # 获取可用工具列表并格式化为系统提示的一部分
            tools = await mcp_client.list_tools()
            dict_list = [tool.__dict__ for tool in tools.tools]
            tools_description = json.dumps(dict_list, ensure_ascii=False)

            # 系统提示，指导LLM如何使用工具和返回响应
            system_message = f'''
                    你是一个智能助手，严格遵循以下协议返回响应：
    
                    可用工具：{tools_description}
    
                    响应规则：
                    1、当需要计算时，返回严格符合以下格式的纯净JSON：
                    {{"tool": "tool-name", "arguments": {{"argument-name": "value"}}}}
                    2、禁止包含以下内容：
                     - Markdown标记（如```json）
                     - 自然语言解释（如"结果："）
                     - import内容
                     - 格式化数值（必须保持原始精度）
                     - 单位符号（如元、kg）
    
                    校验流程：
                    ✓ 参数数量与工具定义一致
                    ✓ 数值类型为number
                    ✓ JSON格式有效性检查
    
                    3、在收到工具的响应后：
                     - 将原始数据转化为自然、对话式的回应
                     - 保持回复简洁但信息丰富
                     - 聚焦于最相关的信息
                     - 使用用户问题中的适当上下文
                     - 避免简单重复使用原始数据
                    '''
            # 启动聊天会话
            chat_session = ChatSession(llm_client=llm_client, mcp_client=mcp_client)
            await chat_session.start(system_message=system_message)

if __name__ == "__main__":
    asyncio.run(main())