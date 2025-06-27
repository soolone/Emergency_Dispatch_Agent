import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.apis import Qwen3_235B_A22B

@dataclass
class WarehouseInfo:
    """仓库信息数据类"""
    name: str
    address: str
    coordinates: Tuple[float, float]
    equipment: Dict
    distance_to_incident: Optional[float] = None
    distance_to_departure: Optional[float] = None
    travel_time_to_incident: Optional[int] = None
    travel_time_to_departure: Optional[int] = None

@dataclass
class BattlePlan:
    """作战计划数据类"""
    plan_id: str
    priority: int
    description: str
    assigned_personnel: int
    assigned_vehicles: int
    assigned_warehouses: List[str]
    equipment_allocation: Dict
    estimated_time: int
    special_instructions: str

class DecisionAgent:
    """基于Qwen3-235B-A22B的作战决策智能代理"""
    
    def __init__(self):
        # 初始化Qwen模型（开启思考模式）
        qwen_config = Qwen3_235B_A22B()
        self.llm = ChatOpenAI(
            openai_api_base=qwen_config.api_base,
            openai_api_key=qwen_config.api_key,
            model_name=qwen_config.model,
            temperature=0.2,  # 稍高的温度以增加创造性
            max_tokens=8000,  # 更大的token限制用于详细规划
            streaming=True,
            extra_body={
                "enable_thinking": True,  # 开启思考模式
            }
        )
        
        # 消息历史
        self.messages = []
        
        # 初始化系统提示
        self._initialize_system_prompt()
    
    def _initialize_system_prompt(self):
        """初始化系统提示"""
        system_prompt = """
你是一个专业的消防应急作战决策专家，具备丰富的火灾扑救和应急救援经验。你的任务是基于提供的信息制定科学、高效的作战规划。

核心职责：
1. 分析火灾情况和现场条件
2. 评估可用资源（人员、车辆、装备）
3. 制定分层次的作战计划
4. 优化资源配置和调度
5. 提供详细的指挥作战方案

决策原则：
- 人员安全第一
- 快速响应，科学部署
- 资源优化配置
- 分级分类处置
- 动态调整策略

输出要求：
1. 提供结构化的作战规划
2. 包含详细的人员和装备分配
3. 明确各阶段作战目标和策略
4. 给出时间节点和执行顺序
5. 提供应急预案和风险控制措施

请始终保持专业、准确、高效的决策风格。
"""
        self.messages.append(SystemMessage(content=system_prompt))
    
    async def analyze_situation(self, 
                              incident_location: str,
                              departure_location: str, 
                              personnel_count: int,
                              vehicle_count: int,
                              fire_description: str,
                              warehouse_distances: Dict,
                              warehouse_info: str,
                              inter_warehouse_distances: str) -> str:
        """分析情况并制定作战规划"""
        
        # 构建分析提示
        analysis_prompt = f"""
请基于以下信息制定详细的消防作战规划：

【基本信息】
- 事发地点：{incident_location}
- 出发地点：{departure_location}
- 可用作战人员：{personnel_count}人
- 可用消防车辆：{vehicle_count}辆

【火灾详情】
{fire_description}

【仓库距离信息】
事发地点到各仓库距离：
{self._format_distances(warehouse_distances.get('incident', {}))}

出发地点到各仓库距离：
{self._format_distances(warehouse_distances.get('departure', {}))}

【仓库物资信息】
{warehouse_info}

【仓库间距离】
{inter_warehouse_distances}

请制定包含以下内容的作战规划：
1. 情况分析和风险评估
2. 作战目标和优先级
3. 人员和车辆分配方案
4. 装备调配计划
5. 分阶段作战部署
6. 时间节点和执行顺序
7. 应急预案和安全措施
8. 指挥协调机制

请以结构化、专业的格式输出完整的作战规划。
"""
        
        # 调用LLM进行分析
        self.messages.append(HumanMessage(content=analysis_prompt))
        response = await self.llm.ainvoke(self.messages)
        
        # 保存响应到消息历史
        self.messages.append(response)
        
        return response.content
    
    def _format_distances(self, distances: Dict) -> str:
        """格式化距离信息"""
        if not distances:
            return "暂无距离信息"
        
        formatted = []
        for warehouse, info in distances.items():
            if isinstance(info, dict):
                distance = info.get('distance', '未知')
                time = info.get('time', '未知')
                formatted.append(f"- {warehouse}：{distance}公里，预计{time}分钟")
            else:
                formatted.append(f"- {warehouse}：{info}")
        
        return "\n".join(formatted)
    
    async def generate_battle_plans(self, 
                                   situation_analysis: str,
                                   max_plans: int = 3) -> List[BattlePlan]:
        """基于情况分析生成多个作战方案"""
        
        plans_prompt = f"""
基于以下情况分析，请生成{max_plans}个不同的作战方案，每个方案应有不同的重点和策略：

{situation_analysis}

请为每个方案提供：
1. 方案编号和名称
2. 优先级（1-5，1为最高）
3. 详细描述
4. 人员分配
5. 车辆分配
6. 仓库选择
7. 装备配置
8. 预计执行时间
9. 特殊注意事项

请以JSON格式输出方案列表。
"""
        
        self.messages.append(HumanMessage(content=plans_prompt))
        response = await self.llm.ainvoke(self.messages)
        self.messages.append(response)
        
        # 这里可以添加JSON解析逻辑来创建BattlePlan对象
        # 目前返回文本格式
        return response.content
    
    async def optimize_resource_allocation(self, 
                                         battle_plans: str,
                                         constraints: Dict) -> str:
        """优化资源配置"""
        
        optimization_prompt = f"""
请对以下作战方案进行资源配置优化：

【作战方案】
{battle_plans}

【约束条件】
{json.dumps(constraints, ensure_ascii=False, indent=2)}

优化目标：
1. 最大化救援效率
2. 最小化响应时间
3. 确保人员安全
4. 合理分配资源

请提供优化后的资源配置建议，包括：
- 人员重新分配
- 装备调整建议
- 时间优化方案
- 风险控制措施
"""
        
        self.messages.append(HumanMessage(content=optimization_prompt))
        response = await self.llm.ainvoke(self.messages)
        self.messages.append(response)
        
        return response.content
    
    async def format_command_output(self, 
                                   analysis: str, 
                                   plans: str, 
                                   optimization: str) -> str:
        """格式化最终的指挥作战结果"""
        
        format_prompt = f"""
请将以下分析结果整合为一份完整的指挥作战方案，要求格式规范、条理清晰、便于执行：

【情况分析】
{analysis}

【作战方案】
{plans}

【资源优化】
{optimization}

请按以下格式输出最终的指挥作战方案：

# 消防应急作战指挥方案

## 一、情况概述
[简要描述火灾情况和现场条件]

## 二、作战目标
[明确作战目标和优先级]

## 三、力量部署
### 3.1 人员分配
[详细的人员分工和职责]

### 3.2 车辆配置
[消防车辆的部署和使用]

### 3.3 装备调配
[各类装备的分配和运输]

## 四、作战部署
### 4.1 第一阶段（紧急响应）
[初期作战部署和行动]

### 4.2 第二阶段（全面展开）
[主要作战行动]

### 4.3 第三阶段（巩固清理）
[后续处置和清理]

## 五、时间节点
[关键时间节点和里程碑]

## 六、指挥协调
[指挥体系和协调机制]

## 七、安全措施
[安全防护和应急预案]

## 八、注意事项
[特殊情况和风险提醒]

请确保方案具有可操作性和实用性。
"""
        
        self.messages.append(HumanMessage(content=format_prompt))
        response = await self.llm.ainvoke(self.messages)
        self.messages.append(response)
        
        return response.content
    
    async def make_decision(self, 
                           incident_location: str,
                           departure_location: str,
                           personnel_count: int,
                           vehicle_count: int,
                           fire_description: str,
                           warehouse_distances: Dict,
                           warehouse_info: str,
                           inter_warehouse_distances: str) -> str:
        """简化的决策方法，专注于物资获取和路径规划"""
        
        try:
            print("[决策代理] 正在生成物资获取和路径规划方案...")
            
            # 构建简化的决策提示
            decision_prompt = f"""
请根据以下信息，制定详细的消防作战指挥方案：

## 火灾情况
- 事发地点：{incident_location}
- 火灾详情：{fire_description}

## 可用资源
- 出发地点：{departure_location}
- 人员数量：{personnel_count}人
- 车辆数量：{vehicle_count}辆

## 仓库信息
{warehouse_info}

## 距离信息
### 事发地点到各仓库距离：
{self._format_distances(warehouse_distances.get('incident', {}))}

### 出发地点到各仓库距离：
{self._format_distances(warehouse_distances.get('departure', {}))}

### 仓库间距离：
{inter_warehouse_distances}

请按以下格式提供详细的作战指挥方案：

**重要提醒：请严格按照上述提供的距离信息来计算时间，不要随意估算！**

## 一、人员车辆分配与物资获取
### 第一批次：
- **人员配置**：X人驾驶X辆车
- **目标仓库**：从{departure_location}前往XX仓库
- **获取装备**：呼吸器X套、防护服X套、其他装备X件
- **预计时间**：根据上述"出发地点到各仓库距离"信息，到达XX仓库需要X分钟，装载物资需要X分钟

### 第二批次（如需分兵作战）：
- **人员配置**：X人驾驶X辆车
- **目标仓库**：从{departure_location}前往XX仓库
- **获取装备**：具体装备清单和数量
- **预计时间**：根据上述"出发地点到各仓库距离"信息，到达XX仓库需要X分钟，装载物资需要X分钟

## 二、救援路线与时间安排
### 主力救援：
- **路线**：从XX仓库前往{incident_location}
- **预计时间**：根据上述"事发地点到各仓库距离"信息，从XX仓库到达现场需要X分钟
- **总用时**：出发到仓库(X分钟) + 装载物资(X分钟) + 仓库到现场(X分钟) = 总计X分钟

### 物资补充（如需要）：
- **补充路线**：从XX仓库前往XX仓库获取XX物资
- **预计时间**：根据仓库间距离信息计算具体时间

## 三、资源需求评估
### 仓库现有物资充足性：
- 已满足需求：XX装备X套
- 可能不足：XX装备可能需要X套

### 总部资源呼叫：
- **紧急需求**：除仓库现有物资外，还需要XX装备X套
- **呼叫理由**：基于火灾规模和人员需求的评估
- **建议调配**：从总部或其他支队调配XX资源

## 四、作战时间节点
- T+0分钟：队伍出发
- T+X分钟：到达仓库开始装载（严格按照"出发地点到各仓库距离"的时间）
- T+X分钟：完成装载前往现场
- T+X分钟：到达现场开始救援（严格按照"事发地点到各仓库距离"的时间）

**请务必使用上述提供的准确距离和时间信息，不要自行估算或使用不合理的时间（如0分钟、1分钟等）。**
"""
            
            # 调用LLM生成方案
            self.messages.append(HumanMessage(content=decision_prompt))
            response = await self.llm.ainvoke(self.messages)
            self.messages.append(response)
            
            return response.content
            
        except Exception as e:
            error_msg = f"决策过程中发生错误: {str(e)}"
            print(error_msg)
            return error_msg
    
    def reset_conversation(self):
        """重置对话历史"""
        self.messages = [self.messages[0]]  # 保留系统提示
        print("[决策代理] 对话历史已重置")

# 便捷函数
async def create_decision_agent() -> DecisionAgent:
    """创建决策代理"""
    return DecisionAgent()

async def quick_decision(incident_location: str,
                        departure_location: str,
                        personnel_count: int,
                        vehicle_count: int,
                        fire_description: str,
                        warehouse_distances: Dict,
                        warehouse_info: str,
                        inter_warehouse_distances: str) -> str:
    """快速决策函数"""
    agent = await create_decision_agent()
    result = await agent.make_decision(
        incident_location, departure_location, personnel_count,
        vehicle_count, fire_description, warehouse_distances,
        warehouse_info, inter_warehouse_distances
    )
    return result

# 测试函数
async def test_decision_agent():
    """测试决策代理"""
    agent = await create_decision_agent()
    
    # 测试数据
    test_data = {
        "incident_location": "成都市锦江区春熙路",
        "departure_location": "成都市消防救援支队",
        "personnel_count": 20,
        "vehicle_count": 4,
        "fire_description": "商业综合体三楼发生火灾，火势较大，有人员被困",
        "warehouse_distances": {
            "incident": {"仓库A": {"distance": 5.2, "time": 15}, "仓库B": {"distance": 8.1, "time": 22}},
            "departure": {"仓库A": {"distance": 3.8, "time": 12}, "仓库B": {"distance": 6.5, "time": 18}}
        },
        "warehouse_info": "仓库A：呼吸器20套，防护服30套；仓库B：呼吸器15套，防护服25套",
        "inter_warehouse_distances": "仓库A-仓库B：12.3公里，预计35分钟"
    }
    
    print("开始测试决策代理...")
    result = await agent.make_decision(**test_data)
    print("\n=== 决策结果 ===")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_decision_agent())