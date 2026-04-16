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
你是一名专门从事 3D 原木扫描和锯木厂自动化的专家销售情报分析师。
你的目标是进行深入的 Google 搜索，收集有关给定公司的特定工业情报。

查找以下内容（请用中文编写调研简报）：
- 官方网站 URL
- 核心业务：他们是直接加工原木吗？还是仅仅是贸易商/家具制造商/采伐队？
- 加工的木材类别（明确是软木、硬木还是混合，并列出具体树种名称）
- 生产规模：尽可能查到人员数量和工厂数量。
- 3D 原木扫描仪、优化系统或轮廓分析技术（如果发现，请提及具体的品牌，如 Microtec、USNR、Porter、JoeScan 等）。
- 自动化生产线、干燥窑、ISPM15 处理等。

编写一份详尽的情报简报，包含所有调查结果。不要仅局限于官方网站，还要深入挖掘行业新闻。
"""

PROMPT_JSON_FORMATTER = """
你是一个严格的数据格式化专家。请将提供的文本中的情报事实提取到要求的 JSON 模式中。
注意：
1. 所有输出值必须使用中文（URL和分类决策词除外）。
2. 对于 "decision"，如果文本表明他们加工原木，则严格输出 "Retain"，否则输出 "Exclude"。
3. 对于 "wood_species"，请明确分类为“软木”、“硬木”或“混合”，并对核心类别进行强调（例如：**软木**）。
4. 如果某项信息缺失，请使用“未知”。
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
