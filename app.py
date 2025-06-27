#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应急物资调度系统 - Streamlit Web界面版本
"""

import sys
import os
import asyncio
import streamlit as st
import re
import pandas as pd
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.locate_agent import create_location_agent
from utils.utils import read_warehouse_data_from_xlsx

def is_coordinates(location_str):
    """检测输入是否为经纬度格式"""
    coord_pattern = r'^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$'
    return bool(re.match(coord_pattern, location_str.strip()))

async def get_location_coordinates(agent, location_name):
    """获取地点的经纬度坐标"""
    try:
        query = f"请提供{location_name}的经纬度坐标"
        response = await agent.process_query(query)
        
        coord_pattern = r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)'
        match = re.search(coord_pattern, response)
        
        if match:
            longitude = match.group(1)
            latitude = match.group(2)
            return f"{longitude},{latitude}"
        else:
            return location_name
    except Exception as e:
        st.error(f"获取{location_name}坐标时出错: {e}")
        return location_name

def parse_distance_info(response_text):
    """解析距离信息，提取关键数据"""
    if not response_text:
        return {
            'distance': '无响应',
            'duration': '无响应',
            'success': False,
            'raw_response': '空响应'
        }
    
    # 尝试多种距离格式
    distance_patterns = [
        r'(\d+\.?\d*)公里',
        r'(\d+\.?\d*)\s*km',
        r'(\d+\.?\d*)米',
        r'(\d+\.?\d*)\s*m(?!in)',  # 匹配米但不匹配min
        r'距离[：:]?\s*(\d+\.?\d*)\s*公里',
        r'距离[：:]?\s*(\d+\.?\d*)\s*km',
        r'距离[：:]?\s*(\d+\.?\d*)\s*米',
        r'约\s*(\d+\.?\d*)\s*公里',
        r'约\s*(\d+\.?\d*)\s*米',
        r'大约\s*(\d+\.?\d*)\s*公里',
        r'大约\s*(\d+\.?\d*)\s*米'
    ]
    
    # 尝试多种时间格式，包括小时、分钟和秒
    time_patterns = [
        r'(\d+)分钟',
        r'(\d+)\s*分钟',
        r'(\d+)小时(\d+)分钟',
        r'(\d+)\s*小时\s*(\d+)\s*分钟',
        r'(\d+)秒',
        r'(\d+)\s*秒',
        r'时间[：:]?\s*(\d+)\s*分钟',
        r'时间[：:]?\s*(\d+)\s*秒',
        r'需要[：:]?\s*(\d+)\s*分钟',
        r'需要[：:]?\s*(\d+)\s*秒',
        r'约\s*(\d+)\s*分钟',
        r'约\s*(\d+)\s*秒',
        r'大约\s*(\d+)\s*分钟',
        r'大约\s*(\d+)\s*秒',
        r'耗时[：:]?\s*(\d+)\s*分钟',
        r'耗时[：:]?\s*(\d+)\s*秒',
        r'用时[：:]?\s*(\d+)\s*分钟',
        r'用时[：:]?\s*(\d+)\s*秒'
    ]
    
    distance_match = None
    time_match = None
    parsed_time = None
    
    # 尝试匹配距离
    for pattern in distance_patterns:
        distance_match = re.search(pattern, response_text)
        if distance_match:
            break
    
    # 处理距离单位转换
    parsed_distance = None
    if distance_match:
        distance_value = float(distance_match.group(1))
        # 检查是否为米单位
        if '米' in pattern or 'm(?!in)' in pattern:
            # 将米转换为公里
            distance_value = distance_value / 1000
            parsed_distance = f"{distance_value:.2f}公里"
        else:
            parsed_distance = f"{distance_value}公里"
    
    # 尝试匹配时间
    for pattern in time_patterns:
        time_match = re.search(pattern, response_text)
        if time_match:
            # 处理小时+分钟格式
            if '小时' in pattern and len(time_match.groups()) >= 2:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2))
                total_minutes = hours * 60 + minutes
                parsed_time = f"{total_minutes}分钟"
            # 处理秒转分钟格式
            elif '秒' in pattern:
                seconds = int(time_match.group(1))
                minutes = round(seconds / 60)
                parsed_time = f"{minutes}分钟"
            else:
                parsed_time = f"{time_match.group(1)}分钟"
            break
    
    # 如果没有找到标准格式，尝试查找数字+时间单位的组合
    if not time_match:
        # 查找任何数字后跟时间相关词汇
        fallback_time_pattern = r'(\d+)(?:分钟|小时|秒|min|hour|sec|h|m|s)'
        fallback_match = re.search(fallback_time_pattern, response_text, re.IGNORECASE)
        if fallback_match:
            # 检查是否为秒单位
            if '秒' in fallback_match.group(0) or 'sec' in fallback_match.group(0).lower() or fallback_match.group(0).endswith('s'):
                seconds = int(fallback_match.group(1))
                minutes = round(seconds / 60)
                parsed_time = f"{minutes}分钟"
            else:
                parsed_time = f"{fallback_match.group(1)}分钟"
            time_match = fallback_match
    
    if distance_match and time_match:
        return {
            'distance': parsed_distance,
            'duration': parsed_time or f"{time_match.group(1)}分钟",
            'success': True
        }
    elif distance_match:
        return {
            'distance': parsed_distance,
            'duration': '时间未知',
            'success': True
        }
    else:
        return {
            'distance': '解析失败',
            'duration': '解析失败',
            'success': False,
            'raw_response': response_text,
            'debug_info': f"响应长度: {len(response_text)}, 前200字符: {response_text[:200]}",
            'distance_patterns_tried': len(distance_patterns),
            'time_patterns_tried': len(time_patterns)
        }

async def calculate_single_warehouse_distance(agent, user_location, warehouse, max_retries=3):
    """计算单个仓库的距离，支持重试机制"""
    warehouse_lng = warehouse['location']['longitude']
    warehouse_lat = warehouse['location']['latitude']
    warehouse_location = f"{warehouse_lng},{warehouse_lat}"
    warehouse_address = warehouse['location']['address']
    
    query = f"从{user_location}到{warehouse_location}的车辆行驶距离"
    
    for attempt in range(max_retries):
        try:
            response = await agent.process_query(query)
            parsed_info = parse_distance_info(response)
            
            if parsed_info['success']:
                return {
                    'warehouse_name': warehouse['name'],
                    'warehouse_address': warehouse_address,
                    'warehouse_coordinates': warehouse_location,
                    'origin': user_location,
                    'destination': f"{warehouse_address} ({warehouse_location})",
                    'distance': parsed_info['distance'],
                    'duration': parsed_info['duration'],
                    'success': True,
                    'attempts': attempt + 1
                }
            else:
                if attempt == max_retries - 1:
                    return {
                        'warehouse_name': warehouse['name'],
                        'warehouse_address': warehouse_address,
                        'warehouse_coordinates': warehouse_location,
                        'origin': user_location,
                        'destination': f"{warehouse_address} ({warehouse_location})",
                        'distance': '解析失败',
                        'duration': '解析失败',
                        'success': False,
                        'attempts': attempt + 1,
                        'raw_response': response
                    }
        except Exception as e:
            if attempt == max_retries - 1:
                return {
                    'warehouse_name': warehouse['name'],
                    'warehouse_address': warehouse_address,
                    'warehouse_coordinates': warehouse_location,
                    'origin': user_location,
                    'destination': f"{warehouse_address} ({warehouse_location})",
                    'distance': '计算失败',
                    'duration': '计算失败',
                    'success': False,
                    'attempts': attempt + 1,
                    'error': str(e)
                }
            await asyncio.sleep(1)
    
    return None

async def calculate_distances_to_warehouses(agent, user_location, warehouses):
    """计算用户位置到所有仓库的距离"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text(f"正在计算从 '{user_location}' 到各仓库的距离...")
    
    # 检测用户输入是否为经纬度格式
    if not is_coordinates(user_location):
        status_text.text(f"检测到地点名称，正在获取 '{user_location}' 的经纬度坐标...")
        user_coordinates = await get_location_coordinates(agent, user_location)
        if user_coordinates != user_location:
            status_text.text(f"已获取坐标: {user_coordinates}")
            actual_user_location = user_coordinates
        else:
            status_text.text(f"无法获取坐标，将使用原始地点名称进行计算")
            actual_user_location = user_location
    else:
        status_text.text(f"检测到经纬度格式，直接使用坐标进行计算")
        actual_user_location = user_location
    
    distances = []
    
    for i, warehouse in enumerate(warehouses):
        progress = (i + 1) / len(warehouses)
        progress_bar.progress(progress)
        status_text.text(f"正在计算第 {i+1}/{len(warehouses)} 个仓库: {warehouse['name']}")
        
        result = await calculate_single_warehouse_distance(agent, actual_user_location, warehouse)
        if result:
            result['origin'] = user_location
            distances.append(result)
    
    progress_bar.empty()
    status_text.empty()
    
    return distances

def analyze_fire_impact(fire_details, personnel_count, fire_truck_count):
    """分析火灾详情对作战计划的影响"""
    impact_analysis = {
        'risk_level': '中等',
        'recommended_equipment': [],
        'personnel_adjustment': personnel_count,
        'fire_truck_adjustment': fire_truck_count,
        'special_considerations': []
    }
    
    fire_details_lower = fire_details.lower()
    
    # 分析火灾规模
    if any(keyword in fire_details_lower for keyword in ['大火', '重大', '严重', '高层']):
        impact_analysis['risk_level'] = '高危'
        impact_analysis['personnel_adjustment'] = max(personnel_count, 30)
        impact_analysis['fire_truck_adjustment'] = max(fire_truck_count, 5)
        impact_analysis['recommended_equipment'].extend(['重型消防车', '云梯车', '大功率水泵'])
        impact_analysis['special_considerations'].append('需要增派人员和重型设备')
    elif any(keyword in fire_details_lower for keyword in ['小火', '初期', '轻微']):
        impact_analysis['risk_level'] = '低危'
        impact_analysis['personnel_adjustment'] = min(personnel_count, 15)
        impact_analysis['fire_truck_adjustment'] = min(fire_truck_count, 2)
    
    # 分析人口密度
    if any(keyword in fire_details_lower for keyword in ['人口密集', '医院', '学校', '商场']):
        impact_analysis['special_considerations'].append('人员疏散优先，需要救护车待命')
        impact_analysis['recommended_equipment'].extend(['救护车', '疏散设备'])
    
    # 分析火灾性质
    if any(keyword in fire_details_lower for keyword in ['化学', '危险品', '油类']):
        impact_analysis['risk_level'] = '高危'
        impact_analysis['recommended_equipment'].extend(['化学防护服', '泡沫灭火剂'])
        impact_analysis['special_considerations'].append('需要化学防护措施')
    
    return impact_analysis

def main():
    """Streamlit主界面"""
    st.set_page_config(
        page_title="应急物资调度系统",
        page_icon="🚒",
        layout="wide"
    )
    
    st.title("🚒 应急物资调度系统")
    st.markdown("---")
    
    # 侧边栏输入区域
    with st.sidebar:
        st.header("📋 应急事件信息")
        
        # 事发地点
        incident_location = st.text_input(
            "🏥 事发地点",
            value="省骨科医院武侯院区",
            help="请输入地址或经纬度坐标"
        )
        
        # 出发地点
        departure_location = st.text_input(
            "🚗 出发地点",
            value="成都消防",
            help="请输入地址或经纬度坐标"
        )
        
        # 作战人员数量
        personnel_count = st.number_input(
            "👥 作战人员数量",
            min_value=1,
            max_value=200,
            value=25,
            step=1
        )
        
        # 消防车数量
        fire_truck_count = st.number_input(
            "🚒 消防车数量",
            min_value=1,
            max_value=4,
            value=3,
            step=1,
            help="请输入参与救援的消防车数量"
        )
        
        # 火灾详情描述
        fire_details = st.text_area(
            "🔥 火灾详情描述",
            value="省骨科医院武侯院区住院部3楼发生电气火灾，火势中等规模，涉及病房区域。医院内有约200名患者和医护人员需要疏散，其中包括行动不便的住院患者。火灾性质为A类固体材料燃烧，但存在医疗设备和药品，需要特别注意安全。周边为居民密集区，需要防止火势蔓延。",
            height=150,
            help="请描述火灾的规模、性质、人员情况等关键信息"
        )
        
        # 计算按钮
        calculate_button = st.button(
            "🔍 开始计算调度方案",
            type="primary",
            use_container_width=True
        )
    
    # 主内容区域
    if calculate_button:
        if not incident_location or not departure_location:
            st.error("请填写完整的事发地点和出发地点信息")
            return
        
        # 显示输入信息摘要
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**事发地点:** {incident_location}")
            st.info(f"**出发地点:** {departure_location}")
        with col2:
            st.info(f"**作战人员:** {personnel_count}人")
            st.info(f"**消防车数量:** {fire_truck_count}辆")
        
        # 火灾影响分析
        impact_analysis = analyze_fire_impact(fire_details, personnel_count, fire_truck_count)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            risk_color = {'低危': 'green', '中等': 'orange', '高危': 'red'}[impact_analysis['risk_level']]
            st.markdown(f"**风险等级:** :{risk_color}[{impact_analysis['risk_level']}]")
        with col2:
            st.markdown(f"**作战人员:** {impact_analysis['personnel_adjustment']}人")
        with col3:
            st.markdown(f"**作战消防车:** {impact_analysis['fire_truck_adjustment']}辆")
        with col4:
            if impact_analysis['recommended_equipment']:
                st.markdown(f"**推荐装备:** {', '.join(impact_analysis['recommended_equipment'][:2])}...")
        
        if impact_analysis['special_considerations']:
            st.warning("⚠️ 特殊注意事项: " + "; ".join(impact_analysis['special_considerations']))
        
        with st.expander("📝 查看完整火灾详情"):
            st.text(fire_details)
        
        st.markdown("---")
        
        # 加载仓库信息
        try:
            xlsx_path = os.path.join(os.path.dirname(__file__), 'data', 'resource.xlsx')
            warehouse_data = read_warehouse_data_from_xlsx(xlsx_path)
            warehouses = warehouse_data['warehouses']
            
            # 获取格式化的仓库信息文本，用于LLM输入
            from utils.utils import format_warehouse_data_for_llm
            warehouse_text, distance_text = format_warehouse_data_for_llm(warehouse_data)
            
            st.success(f"✅ 已加载 {len(warehouses)} 个仓库信息")
        except Exception as e:
            st.error(f"❌ 加载仓库信息失败: {e}")
            return
        
        # 异步计算距离
        async def run_calculation():
            try:
                agent = await create_location_agent()
                
                # 使用可展开的区域显示距离计算结果
                with st.expander("📍 距离计算结果", expanded=False):
                    # 创建两列布局
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 🏥 事发地点 → 仓库")
                        incident_distances = await calculate_distances_to_warehouses(agent, incident_location, warehouses)
                        
                        # 显示事发地点距离结果
                        for dist in incident_distances:
                            if dist['success']:
                                st.success(f"✅ {dist['warehouse_name']}: {dist['distance']}, {dist['duration']}")
                            else:
                                st.error(f"❌ {dist['warehouse_name']}: {dist['distance']}")
                                if 'raw_response' in dist:
                                    with st.expander(f"查看详细信息 - {dist['warehouse_name']}"):
                                        st.text("原始响应:")
                                        st.code(dist['raw_response'])
                                        if 'debug_info' in dist:
                                             st.text("调试信息:")
                                             st.info(dist['debug_info'])
                                             if 'distance_patterns_tried' in dist:
                                                 st.text(f"尝试的距离模式数: {dist['distance_patterns_tried']}")
                                             if 'time_patterns_tried' in dist:
                                                 st.text(f"尝试的时间模式数: {dist['time_patterns_tried']}")
                    
                    with col2:
                        st.markdown("### 🚗 出发地点 → 仓库")
                        departure_distances = await calculate_distances_to_warehouses(agent, departure_location, warehouses)
                        
                        # 显示出发地点距离结果
                        for dist in departure_distances:
                            if dist['success']:
                                st.success(f"✅ {dist['warehouse_name']}: {dist['distance']}, {dist['duration']}")
                            else:
                                st.error(f"❌ {dist['warehouse_name']}: {dist['distance']}")
                                if 'raw_response' in dist:
                                    with st.expander(f"查看详细信息 - {dist['warehouse_name']}"):
                                        st.text("原始响应:")
                                        st.code(dist['raw_response'])
                                        if 'debug_info' in dist:
                                            st.text("调试信息:")
                                            st.info(dist['debug_info'])
                                            if 'distance_patterns_tried' in dist:
                                                st.text(f"尝试的距离模式数: {dist['distance_patterns_tried']}")
                                            if 'time_patterns_tried' in dist:
                                                st.text(f"尝试的时间模式数: {dist['time_patterns_tried']}")
                
                await agent.disconnect()
                return incident_distances, departure_distances
                
            except Exception as e:
                st.error(f"计算过程中出错: {e}")
                return None, None
        
        # 运行异步计算
        with st.spinner("正在计算距离信息..."):
            incident_distances, departure_distances = asyncio.run(run_calculation())
        
        if incident_distances and departure_distances:
            # 显示详细结果
            with st.expander("📊 综合调度分析", expanded=False):
                
                for i, (inc_dist, dep_dist) in enumerate(zip(incident_distances, departure_distances)):
                    warehouse = warehouses[i]
                    
                    # 计算装备支撑能力
                    equipment_capacity = 0
                    equipment_details = []
                    
                    # 处理resources列表格式（从Excel加载的数据）
                    for resource in warehouse.get('resources', []):
                        item_name = resource.get('name', '')
                        quantity = resource.get('quantity', 0)
                        
                        if any(keyword in item_name for keyword in ['呼吸器', '防护服', '面罩']):
                            equipment_capacity += quantity
                            equipment_details.append(f"{item_name}:{quantity}套")
                    
                    # 判断装备支撑能力
                    if equipment_capacity >= personnel_count:
                        equipment_status = "✅ 充足"
                        equipment_color = "green"
                    elif equipment_capacity >= personnel_count * 0.7:
                        equipment_status = "⚠️ 基本满足"
                        equipment_color = "orange"
                    else:
                        equipment_status = "❌ 不足"
                        equipment_color = "red"
                    
                    # 创建仓库信息卡片
                    with st.expander(f"🏢 仓库 {i+1}: {inc_dist['warehouse_name']}", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("**📍 基本信息**")
                            st.text(f"地址: {inc_dist['warehouse_address']}")
                            st.text(f"坐标: {inc_dist['warehouse_coordinates']}")
                        
                        with col2:
                            st.markdown("**🏥 事发地点距离**")
                            if inc_dist['success']:
                                st.metric("距离", inc_dist['distance'])
                                st.metric("时间", inc_dist['duration'])
                            else:
                                st.error(f"计算失败: {inc_dist['distance']}")
                        
                        with col3:
                            st.markdown("**🚗 出发地点距离**")
                            if dep_dist['success']:
                                st.metric("距离", dep_dist['distance'])
                                st.metric("时间", dep_dist['duration'])
                            else:
                                st.error(f"计算失败: {dep_dist['distance']}")
                        
                        if equipment_details:
                            st.markdown("**🛡️ 防护装备详情**")
                            st.text(", ".join(equipment_details))
            
                    # 统计信息
                    st.markdown("---")
                    st.subheader("📈 统计分析")
                    
                    col1, col2, col3, col4 = st.columns(4)
                
                    # 距离计算统计
                    successful_incident = sum(1 for d in incident_distances if d['success'])
                    successful_departure = sum(1 for d in departure_distances if d['success'])
                    
                    with col1:
                        st.metric("事发地点查询成功", f"{successful_incident}/{len(incident_distances)}")
                    with col2:
                        st.metric("出发地点查询成功", f"{successful_departure}/{len(departure_distances)}")
                
                    # 装备支撑统计
                    adequate_warehouses = 0
                    basic_warehouses = 0
                    insufficient_warehouses = 0
                    
                    for warehouse in warehouses:
                        equipment_capacity = 0
                        # 处理resources列表格式（从Excel加载的数据）
                        for resource in warehouse.get('resources', []):
                            item_name = resource.get('name', '')
                            quantity = resource.get('quantity', 0)
                            if any(keyword in item_name for keyword in ['呼吸器', '防护服', '面罩']):
                                equipment_capacity += quantity
                        
                        if equipment_capacity >= personnel_count:
                            adequate_warehouses += 1
                        elif equipment_capacity >= personnel_count * 0.7:
                            basic_warehouses += 1
                        else:
                            insufficient_warehouses += 1
                    
                    with col3:
                        st.metric("装备充足仓库", f"{adequate_warehouses}/{len(warehouses)}")
                    with col4:
                        st.metric("装备不足仓库", f"{insufficient_warehouses}/{len(warehouses)}")
                
                    # 推荐仓库
                    if successful_incident > 0 or successful_departure > 0:
                        st.subheader("🎯 推荐仓库")
                        
                        col1, col2 = st.columns(2)
                        
                        if successful_incident > 0:
                            nearest_incident = min([d for d in incident_distances if d['success']], 
                                                 key=lambda x: float(x['distance'].replace('公里', '').replace('km', '')))
                            with col1:
                                st.success(f"**距离事发地点最近:** {nearest_incident['warehouse_name']}")
                                st.text(f"距离: {nearest_incident['distance']} | 时间: {nearest_incident['duration']}")
                        
                        if successful_departure > 0:
                            nearest_departure = min([d for d in departure_distances if d['success']], 
                                                  key=lambda x: float(x['distance'].replace('公里', '').replace('km', '')))
                            with col2:
                                st.success(f"**距离出发地点最近:** {nearest_departure['warehouse_name']}")
                                st.text(f"距离: {nearest_departure['distance']} | 时间: {nearest_departure['duration']}")            
            
            # 作战指挥部署
            st.markdown("---")
            st.subheader("🎯 作战指挥部署")
            
            # 调用决策代理进行作战规划
            async def run_decision_analysis():
                try:
                    from agents.decision_agent import DecisionAgent
                    
                    # 创建决策代理
                    decision_agent = DecisionAgent()
                    
                    # 准备距离数据
                    warehouse_distances = {
                        'incident': {d['warehouse_name']: {'distance': d['distance'], 'time': d['duration']} 
                                   for d in incident_distances if d['success']},
                        'departure': {d['warehouse_name']: {'distance': d['distance'], 'time': d['duration']} 
                                    for d in departure_distances if d['success']}
                    }
                    
                    # 调用决策代理的主要决策方法
                    battle_plan = await decision_agent.make_decision(
                        incident_location=incident_location,
                        departure_location=departure_location,
                        personnel_count=personnel_count,
                        vehicle_count=fire_truck_count,
                        fire_description=fire_details,
                        warehouse_distances=warehouse_distances,
                        warehouse_info=warehouse_text,
                        inter_warehouse_distances=distance_text
                    )
                    
                    return battle_plan
                    
                except Exception as e:
                    st.error(f"作战规划生成失败: {e}")
                    return None
            
            # 运行决策分析
            with st.spinner("正在生成物资获取和路径规划方案..."):
                battle_plan = asyncio.run(run_decision_analysis())
            
            if battle_plan:
                # 显示物资获取和路径规划方案
                with st.expander("🚛 物资获取和路径规划方案", expanded=True):
                    # 使用左右两列布局显示方案
                    col1, col2 = st.columns(2)
                    
                    # 将battle_plan按段落分割
                    plan_sections = battle_plan.split('\n\n')
                    mid_point = len(plan_sections) // 2
                    
                    with col1:
                        # 显示前半部分内容
                        left_content = '\n\n'.join(plan_sections[:mid_point])
                        st.markdown(left_content)
                    
                    with col2:
                        # 显示后半部分内容
                        right_content = '\n\n'.join(plan_sections[mid_point:])
                        st.markdown(right_content)
                
                # 添加下载按钮
                st.download_button(
                    label="📄 下载规划方案",
                    data=battle_plan,
                    file_name=f"物资获取路径规划_{incident_location}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
    
    else:
        # 默认显示系统介绍
        st.markdown("""
        ## 🎯 系统功能
        
        本系统为应急物资调度提供智能化支持，主要功能包括：
        
        - 📍 **双地点距离计算**: 同时计算事发地点和出发地点到各仓库的距离
        - 🛡️ **装备支撑分析**: 根据作战人员数量分析各仓库的装备支撑能力
        - 🔥 **火灾影响评估**: 基于火灾详情智能分析对作战计划的影响
        - 📊 **综合决策支持**: 提供距离、装备、风险等多维度分析结果
        
        ## 📝 使用说明
        
        1. 在左侧面板填写应急事件信息
        2. 点击"开始计算调度方案"按钮
        3. 系统将自动计算并显示分析结果
        4. 查看推荐仓库和统计信息
        
        ## ⚠️ 注意事项
        
        - 地点可以输入地址或经纬度坐标
        - 系统会自动进行地址解析和坐标转换
        - 火灾详情描述会影响风险评估和装备推荐
        """)

if __name__ == "__main__":
    main()