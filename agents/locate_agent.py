import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import re
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.apis import Qwen3_235B_A22B

def format_tools_for_llm(tool) -> str:
    """对tool进行格式化"""
    args_desc = []
    if "properties" in tool.inputSchema:
        for param_name, param_info in tool.inputSchema["properties"].items():
            arg_desc = (
                f"- {param_name}: {param_info.get('description', 'No description')}"
            )
            if param_name in tool.inputSchema.get("required", []):
                arg_desc += " (required)"
            args_desc.append(arg_desc)
    return f"Tool: {tool.name}\nDescription: {tool.description}\nArguments:\n{chr(10).join(args_desc)}"

class LocationAgent:
    """基于Qwen3-235B-A22B的地图定位智能代理"""
    
    def __init__(self, server_config_path="configs/servers_config.json"):
        # 加载服务器配置
        with open(server_config_path) as f:
            self.server_config = json.load(f)
        
        # MCP连接相关
        self._exit_stack: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None
        self.tools = {}
        
        # 初始化Qwen模型
        qwen_config = Qwen3_235B_A22B()
        self.llm = ChatOpenAI(
            openai_api_base=qwen_config.api_base,
            openai_api_key=qwen_config.api_key,
            model_name=qwen_config.model,
            temperature=0.1,
            max_tokens=4000,
            streaming=False,
            extra_body={
                    "enable_thinking": False,  # 禁用思考模式
            }
        )
        
        # 消息历史
        self.messages = []
    
    async def connect_to_amap_server(self):
        """连接到高德地图MCP服务器"""
        url = self.server_config["mcpServers"]["amap-amap-sse"]["url"]
        print(f"尝试连接到: {url}")
        
        self._exit_stack = AsyncExitStack()
        sse_cm = sse_client(url)
        streams = await self._exit_stack.enter_async_context(sse_cm)
        print("SSE 流已获取。")
        
        session_cm = ClientSession(streams[0], streams[1])
        self.session = await self._exit_stack.enter_async_context(session_cm)
        print("ClientSession 已创建。")
        
        await self.session.initialize()
        print("Session 已初始化。")
        
        # 获取可用工具
        response = await self.session.list_tools()
        self.tools = {tool.name: tool for tool in response.tools}
        print(f"成功获取 {len(self.tools)} 个工具:")
        for name, tool in self.tools.items():
            print(f"  - {name}: {tool.description[:50]}...")
        print("连接成功并准备就绪。")
        
        # 设置系统提示
        tools_description = "\n".join([format_tools_for_llm(tool) for tool in response.tools])
        system_prompt = (
            "You are a helpful assistant specialized in Chengdu, China with access to these tools:\n\n"
            f"{tools_description}\n"
            "Choose the appropriate tool based on the user's question. "
            "If no tool is needed, reply directly.\n\n"
            "IMPORTANT LOCATION CONTEXT:\n"
            "- You are specifically designed to help with locations in Chengdu, Sichuan Province, China\n"
            "- When users mention place names without specifying the city, assume they are referring to locations in Chengdu\n"
            "- For ambiguous place names that exist in multiple cities, prioritize Chengdu locations\n"
            "- Always provide responses in Chinese unless specifically requested otherwise\n\n"
            "CRITICAL TOOL USAGE STRATEGY:\n"
            "For route planning queries (A到B怎么走, A到B出行), you MUST follow this EXACT sequence:\n"
            "1. First call: maps_geo with origin location name\n"
            "2. Second call: maps_geo with destination location name\n"
            "3. Third call: maps_direction_transit_integrated with the coordinates from steps 1&2\n"
            "\n"
            "EXAMPLE for '文化宫到省骨科医院':\n"
            "Step 1: {\"tool\": \"maps_geo\", \"arguments\": {\"address\": \"文化宫\"}}\n"
            "Step 2: {\"tool\": \"maps_geo\", \"arguments\": {\"address\": \"省骨科医院\"}}\n"
            "Step 3: {\"tool\": \"maps_direction_transit_integrated\", \"arguments\": {\"origin\": \"lat1,lng1\", \"destination\": \"lat2,lng2\"}}\n"
            "\n"
            "NEVER skip the coordinate lookup steps. ALWAYS get coordinates for BOTH locations first.\n\n"
            "IMPORTANT: When you need to use a tool, you must ONLY respond with "
            "the exact JSON object format below, nothing else:\n"
            "{\n"
            '    "tool": "tool-name",\n'
            '    "arguments": {\n'
            '        "argument-name": "value"\n'
            "    }\n"
            "}\n\n"
            '"```json" is not allowed\n'
            "After receiving a tool's response:\n"
            "1. Transform the raw data into a natural, conversational response\n"
            "2. Keep responses concise but informative\n"
            "3. Focus on the most relevant information\n"
            "4. Use appropriate context from the user's question\n"
            "5. Avoid simply repeating the raw data\n"
            "6. When providing location information, prioritize Chengdu-based results\n\n"
            "Please use only the tools that are explicitly defined above."
        )
        self.messages.append(SystemMessage(content=system_prompt))
    
    async def disconnect(self):
        """断开MCP连接"""
        if self._exit_stack:
            await self._exit_stack.aclose()
            print("MCP连接已断开")
    
    async def call_llm(self, prompt, role="user"):
        """调用LLM"""
        if role == "user":
            self.messages.append(HumanMessage(content=prompt))
        else:
            self.messages.append(SystemMessage(content=prompt))
        
        response = await self.llm.ainvoke(self.messages)
        llm_response = response.content
        return llm_response
    
    async def call_tool(self, llm_response: str):
        """调用工具"""
        try:
            # 移除可能的 ```json 标记
            pattern = r"```json\n(.*?)\n?```"
            match = re.search(pattern, llm_response, re.DOTALL)
            if match:
                llm_response = match.group(1)
            
            # 解析工具调用
            tool_call = json.loads(llm_response)
            if "tool" in tool_call and "arguments" in tool_call:
                response = await self.session.list_tools()
                tools = response.tools
                if any(tool.name == tool_call["tool"] for tool in tools):
                    try:
                        print(f"[提示]：正在调用工具 {tool_call['tool']}")
                        result = await self.session.call_tool(
                            tool_call["tool"], tool_call["arguments"]
                        )
                        # 处理进度信息
                        if isinstance(result, dict) and "progress" in result:
                            progress = result["progress"]
                            total = result["total"]
                            percentage = (progress / total) * 100
                            print(f"Progress: {progress}/{total} ({percentage:.1f}%)")
                        return f"Tool execution result: {result}"
                    except Exception as e:
                        error_msg = f"Error executing tool: {str(e)}"
                        print(error_msg)
                        return error_msg
                return f"No server found with tool: {tool_call['tool']}"
            return llm_response
        except json.JSONDecodeError:
            return llm_response
    
    async def process_query(self, user_query: str) -> str:
        """处理用户查询的主要方法"""
        try:
            # 调用LLM分析查询
            response = await self.call_llm(user_query)
            self.messages.append(HumanMessage(content=response))
            
            # 尝试调用工具
            result = await self.call_tool(response)
            
            # 如果工具调用返回了不同的结果，继续对话
            while result != response:
                response = await self.call_llm(result, "system")
                self.messages.append(HumanMessage(content=response))
                result = await self.call_tool(response)
            
            return response
            
        except Exception as e:
            error_msg = f"处理查询时发生错误: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def interactive_mode(self):
        """交互模式"""
        print("地图定位代理启动")
        print("输入 /bye 退出")
        
        while True:
            try:
                user_input = input(">>> ").strip()
                
                if "/bye" in user_input.lower():
                    print("再见！")
                    break
                
                if not user_input:
                    print("请输入有效的查询")
                    continue
                
                response = await self.process_query(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n程序被用户中断")
                break
            except Exception as e:
                print(f"处理查询时出错: {e}")
                continue

# 便捷函数
async def create_location_agent(server_config_path="configs/servers_config.json") -> LocationAgent:
    """创建并初始化地图定位代理"""
    agent = LocationAgent(server_config_path)
    await agent.connect_to_amap_server()
    return agent

async def quick_query(query: str, server_config_path="configs/servers_config.json") -> str:
    """快速查询函数"""
    agent = await create_location_agent(server_config_path)
    try:
        result = await agent.process_query(query)
        return result
    finally:
        await agent.disconnect()

# 测试函数
async def test_location_agent():
    """测试地图定位代理"""
    agent = await create_location_agent()
    
    try:
        # 测试查询
        test_queries = [
            "北京天安门在哪里",
            "从北京到上海怎么走",
            "北京到上海多远",
            "搜索附近的餐厅"
        ]
        
        for query in test_queries:
            print(f"\n测试查询: {query}")
            print("-" * 40)
            response = await agent.process_query(query)
            print(f"回复: {response}")
            
    finally:
        await agent.disconnect()

if __name__ == "__main__":
    asyncio.run(test_location_agent())