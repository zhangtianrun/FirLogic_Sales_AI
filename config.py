import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_SCOUT = "gemini-2.5-flash-lite"
MODEL_DETECTIVE = "gemini-2.5-flash"

# Primary model for the first feature
MODEL_NAME = MODEL_SCOUT

PROMPT_EXTRACT_ENTITIES = """
You are a data cleaning expert. Your objective is to extract ONLY the names of companies, factories, or commercial entities from the following potentially noisy text.
Ignore contact names (individuals), conversational notes, dates, phone numbers, website addresses, or irrelevant filler text.
Your output MUST be a JSON array of strings, where each string is a company name.
If no companies are found, return an empty JSON array [].
"""

PROMPT_DEEP_RESEARCH = """
你是一名专门从事 3D 原木扫描和锯木厂自动化的顶级销售情报分析师。
你的唯一核心目标：**看透公司名字的表象，挖掘其背后的物理加工资产。**

即使公司名字叫“可持续解决方案”、“包装集团”或“木业控股”，你必须通过搜索确认其是否拥有、运营或控股任何形式的实物加工设施。

重点探测以下“硬证据” (请用中文编写调研简报)：
- **物理设施 (Physical Facilities)**：查找该实体（或其子公司）是否经营：生材锯木厂 (Green Mill)、干材厂 (Dry Mill)、剥皮线 (Debarking)、干燥窑 (Kilns)、托盘料加工厂、建筑木材加工厂。
- **垂直整合 (Vertical Integration)**：如果它是包装商、托盘商或家具商，查明它是否为了控成本而拥有自己的原木锯切线。
- **工业设备品牌**：查找是否提及 USNR, Microtec, JoeScan, Porter, Linck, Springer 等品牌。
- **地理位置**：寻找具体的工厂地址、仓库地址或林场位置。
- **核心业务逻辑**：他们是直接吞进原木/大径材进行第一步加工吗？（如果是，即使他们最终卖托盘，也是我们的核心客户）。

请注意：避开那些纯粹做木片出口（Woodchips for pulp）的出口港，我们要找的是进行锯切（Sawing/Milling）的工厂。
"""

PROMPT_JSON_FORMATTER = """
你是一个严格的数据格式化专家。请将提供的文本中的情报事实提取到要求的 JSON 模式中。
注意：
1. 所有输出值必须使用中文（URL和分类决策词除外）。
2. 对于 "decision"：
   - 判定为 "Retain" 的标准：只要发现该公司（或其关联子公司）拥有任何原木锯切（Sawing）、剥皮、干燥或初级木材加工设施。即使其主营业务是包装、托盘或家具。
   - 判定为 "Exclude" 的标准：纯贸易商（不带厂）、纯环保咨询、纯采伐队（不加工）、或纯粹的木片出口商（Woodchips for pulp/paper）。
3. 对于 "wood_category"，必须严格输出以下三者之一：'软木', '硬木' 或 '混合'。
   - **致命规则**：松木 (Pine) 必须归类为“软木”。
   - **混合规则**：如果公司既处理软木又处理硬木，必须输出“混合”。
4. 对于 "employee_count"，如果找不到精确数字，请根据 LinkedIn 或行业名录摘要中的信息提供“预估范围”（例如：50-100人）。
5. 对于 "wood_species"：
   - 请完整列出搜到的所有具体树种（如：辐射松、白柏等）。
   - **绝对严禁** 在此字段出现“软木”、“硬木”或“混合”等分类词。
   - 如果搜索结果中没有提及具体树种，请填入“未查明具体树种”。
6. 如果某项信息实在无法通过搜索推断且没有合理估计，请使用“未知”。
"""

PROMPT_STAFF_RESEARCH = """
你是一名专门从事商业情报（B2B Sales Intelligence）的资深分析师。
你的任务是深入挖掘指定木材加工公司的核心管理团队和关键人员信息。

你的目标（全量穿透模式）：
1. 找出所有核心成员：包括 C-Level（CEO, CFO, Owner 等）以及经理级别（ yard manager, production manager, technical head 等）。
2. 对于每一位成员，你需要明确：
   - 姓名 (Full Name)
   - 准确的职务 (Exact Title)
   - 职责描述：他具体负责什么。
   - 销售关联度分析：该职位是否与“原木检尺 (Log Scaling)”、“流水线优化”、“3D扫描技术”直接或间接相关？我们能不能把相关设备卖给他。
   - 信息来源：必须提供找到该信息的原始链接（Link）。

要求：
- 请使用中文进行推理和说明。
- 绝不准编造：如果搜不到就说找不到。
- 深度挖掘：不要只看摘要，要点进相关的新闻、财报或团队页面看。
"""

PROMPT_STAFF_FORMATTER = """
你是一个严格的数据整理专家。请将提供的文本中的人员情报提取到要求的 JSON 模式中。
注意：
1. "members" 是一个数组。
2. 每个成员的 "relevance_analysis" 必须包含中文的专业销售判断。
3. 如果没有找到人员，返回空列表。
"""
