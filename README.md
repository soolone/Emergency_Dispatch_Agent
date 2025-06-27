# 应急物资调度系统

🚒 基于AI的智能应急物资调度与路径规划系统

## 📋 项目简介

本系统是一个基于人工智能的应急物资调度系统，能够根据火灾等应急事件的具体情况，智能分析各仓库的物资配置，计算最优的物资获取路线，并生成详细的作战指挥方案。

## 🏗️ 系统架构

```
Emergency_Agent/
├── app.py                    # Streamlit主应用程序
├── main.py                   # 命令行入口
├── agents/                   # AI代理模块
│   ├── locate_agent.py      # 地理位置代理
│   └── decision_agent.py    # 决策分析代理
├── data/                     # 数据文件
│   ├── resource.json        # 仓库物资数据(JSON格式)
│   └── resource.xlsx        # 仓库物资数据(Excel格式)
├── scripts/                  # 工具脚本
│   └── json_to_xlsx_converter.py  # JSON转Excel转换器
├── utils/                    # 工具函数
│   ├── apis.py              # API接口
│   └── utils.py             # 通用工具函数
└── configs/                  # 配置文件
    └── servers_config.json  # 服务器配置
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 依赖包：streamlit, pandas, openpyxl, asyncio

### 安装依赖

```bash
pip install streamlit pandas openpyxl aiohttp
```

### 使用流程

#### 第一步：准备仓库数据

1. **编辑仓库信息**
   
   参考 `data/resource.json` 文件格式，构建您的仓库信息数据：

   ```json
   {
     "warehouses": [
       {
         "id": "WH001",
         "name": "文化宫仓库",
         "location": {
           "address": "文化宫",
           "longitude": 104.009413,
           "latitude": 30.672258,
           "city": "成都市",
           "district": "青羊区"
         },
         "capacity": {
           "total_area": 5000,
           "available_area": 4200,
           "max_weight": 800
         },
         "resources": {
           "fire_extinguishing": {
             "foam_extinguisher": {
               "quantity": 25,
               "unit": "台",
               "type": "泡沫灭火器",
               "specification": "35L"
             }
           }
         },
         "contact": {
           "manager": "张明",
           "phone": "028-12345001",
           "emergency_phone": "028-12345002"
         }
       }
     ],
     "metadata": {
       "last_updated": "2024-12-19",
       "version": "1.0",
       "description": "应急物资仓库信息数据库"
     }
   }
   ```

#### 第二步：生成Excel文件并计算仓库间距离

使用转换脚本将JSON数据转换为Excel格式，并自动计算仓库间距离：

```bash
# 基本转换（包含距离计算）
python scripts/json_to_xlsx_converter.py

# 指定输入输出文件
python scripts/json_to_xlsx_converter.py -i data/resource.json -o data/resource.xlsx

# 禁用距离计算（仅转换格式）
python scripts/json_to_xlsx_converter.py --no-distances
```

**转换器功能：**
- 📊 将JSON数据转换为多工作表Excel文件
- 📍 自动计算所有仓库间的行驶距离和时间
- 📈 生成物资统计汇总表
- 📋 创建仓库基本信息表

**生成的Excel工作表：**
- `仓库基本信息` - 仓库位置、容量、联系方式
- `物资详细信息` - 各仓库物资清单
- `物资统计汇总` - 按类别统计的物资总量
- `仓库间距离` - 仓库间行驶距离和时间
- `元数据信息` - 数据版本和更新信息

#### 第三步：启动Streamlit应用

运行Web界面进行应急调度模拟：

```bash
streamlit run app.py
```

#### 第四步：进行调度模拟

在Web界面中输入以下信息：

1. **📍 事发地点** - 火灾发生地址或经纬度坐标
2. **🚗 出发地点** - 救援队伍出发地址或经纬度坐标  
3. **👥 作战人员数量** - 参与救援的人员数量
4. **🚒 消防车数量** - 参与救援的消防车数量
5. **🔥 火灾详情描述** - 火灾规模、性质、人员情况等

点击"🔍 开始计算调度方案"按钮，系统将：

- 🧮 计算各仓库到事发地点和出发地点的距离
- 📊 分析各仓库的物资支撑能力
- 🎯 生成智能化的作战指挥方案
- 📋 提供详细的物资获取路线和时间安排

## 🎯 系统功能特性

### 🔍 智能距离计算
- 支持地址和经纬度坐标输入
- 自动进行地址解析和坐标转换
- 实时计算行驶距离和预计时间
- 支持多种距离和时间单位解析

### 📊 物资分析
- 多维度物资配置分析
- 装备支撑能力评估
- 物资充足性检查
- 补充物资需求计算

### 🎯 智能决策
- 基于AI的路径优化
- 多因素综合决策分析
- 风险等级自动评估
- 个性化作战方案生成

### 📋 详细规划
- 人员车辆分批次部署
- 精确的时间节点安排
- 主力救援路线规划
- 物资获取优先级排序

## 📊 数据格式说明

### 仓库数据结构

```json
{
  "warehouses": [
    {
      "id": "仓库唯一标识",
      "name": "仓库名称",
      "location": {
        "address": "详细地址",
        "longitude": "经度",
        "latitude": "纬度",
        "city": "城市",
        "district": "行政区"
      },
      "capacity": {
        "total_area": "总面积(平方米)",
        "available_area": "可用面积(平方米)",
        "max_weight": "最大载重(吨)"
      },
      "resources": {
        "fire_extinguishing": "灭火设备",
        "rescue_equipment": "救援装备",
        "medical_supplies": "医疗用品",
        "communication": "通信设备",
        "evacuation": "疏散设备",
        "heavy_equipment": "重型装备",
        "logistics": "后勤保障",
        "command_center": "指挥中心"
      },
      "contact": {
        "manager": "负责人",
        "phone": "联系电话",
        "emergency_phone": "应急电话"
      }
    }
  ]
}
```

### 物资类别说明

| 类别 | 英文标识 | 包含物资 |
|------|----------|----------|
| 灭火设备 | fire_extinguishing | 泡沫灭火器、干粉灭火器、消防水带等 |
| 救援装备 | rescue_equipment | 呼吸器、防护服、救援绳、破拆工具等 |
| 医疗用品 | medical_supplies | 急救包、烧伤敷料、防烟面罩、氧气瓶等 |
| 通信设备 | communication | 对讲机、扩音器、卫星电话等 |
| 疏散设备 | evacuation | 应急照明灯、逃生滑梯等 |
| 重型装备 | heavy_equipment | 消防车装备、发电机、抽水泵等 |
| 后勤保障 | logistics | 燃油、运输车辆等 |
| 指挥中心 | command_center | 移动指挥单元、无人机等 |

## 🔧 配置说明

### AI模型API配置

系统使用多个AI模型提供智能分析功能，需要配置相应的API密钥。

#### Modelscope API配置

编辑 `utils/apis.py` 文件中的API密钥配置：

```python
class Qwen25VL72BInstruct:
    def __init__(self):
        self.model = "Qwen/Qwen2.5-VL-72B-Instruct"
        self.api_key = "your-modelscope-api"  # 需要替换为您的Modelscope API密钥
        self.api_base = "https://api-inference.modelscope.cn/v1/"

class Qwen3_235B_A22B:
    def __init__(self):
        self.model = "Qwen/Qwen3-235B-A22B"
        self.api_key = "your-modelscope-api"  # 需要替换为您的Modelscope API密钥
        self.api_base = "https://api-inference.modelscope.cn/v1/"
```

**获取Modelscope API密钥：**

1. 访问 [Modelscope官网](https://www.modelscope.cn/)
2. 注册并登录您的账户
3. 进入个人中心 → API管理
4. 创建新的API密钥或查看现有密钥
5. 将获取的API密钥替换 `utils/apis.py` 文件中的 `"your-modelscope-api"`

**注意事项：**
- 请妥善保管您的API密钥，不要将其提交到公共代码仓库
- 建议使用环境变量来存储API密钥以提高安全性
- 确保您的Modelscope账户有足够的API调用额度

### 服务器配置

编辑 `configs/servers_config.json` 文件配置API服务器：

```json
{
  "api_servers": [
    {
      "name": "主服务器",
      "base_url": "https://api.example.com",
      "api_key": "your_api_key",
      "timeout": 30
    }
  ]
}
```

### Streamlit配置

创建 `.streamlit/config.toml` 文件：

```toml
[server]
port = 8501
fileWatcherType = "none"

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

## 🚨 使用示例

### 示例场景：医院火灾应急响应

**输入信息：**
- 事发地点：省骨科医院武侯院区
- 出发地点：中国电信四川公司总部
- 作战人员：20人
- 消防车：3辆
- 火灾详情：住院部3楼电气火灾，中等规模，需疏散200名患者和医护人员

**系统输出：**
- 📍 计算到各仓库的精确距离和时间
- 🎯 推荐最优仓库组合
- 📋 详细的物资获取清单
- ⏰ 完整的作战时间安排
- 🚛 具体的行驶路线规划

## 🛠️ 开发说明

### 核心模块

- **locate_agent.py** - 地理位置查询和距离计算
- **decision_agent.py** - 智能决策分析和方案生成
- **utils.py** - 数据处理和格式化工具
- **apis.py** - 外部API接口封装

### 扩展开发

1. **添加新的物资类别**
   - 在JSON数据中添加新的resources分类
   - 更新utils.py中的格式化函数

2. **集成新的地图API**
   - 修改locate_agent.py中的API调用逻辑
   - 更新距离解析函数

3. **优化决策算法**
   - 修改decision_agent.py中的决策提示词
   - 添加新的分析维度

## 📝 注意事项

1. **API配置** - 确保地图API密钥正确配置
2. **数据格式** - 严格按照JSON格式要求编辑仓库数据
3. **坐标系统** - 使用WGS84坐标系统
4. **网络连接** - 距离计算需要稳定的网络连接
5. **性能优化** - 大量仓库时建议分批计算距离

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进系统功能。

## 📄 许可证

本项目采用MIT许可证。

---

🚒 **应急物资调度系统** - 让应急响应更智能、更高效！