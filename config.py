import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCfIXUi5ZHKQcZHhoroz5M102lWXGW-Xag")
MODEL_NAME = "gemini-3.1-flash-lite-preview"

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
