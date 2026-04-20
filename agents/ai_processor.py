from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import sys
import os

# Add parent to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import json
import re

# Load Wood Species Master Database
SPECIES_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "wood_species_master.json")
try:
    with open(SPECIES_DB_PATH, "r", encoding="utf-8") as f:
        WOOD_DB = json.load(f)
except Exception as e:
    print(f"    [!] Warning: Could not load wood species database: {e}")
    WOOD_DB = {}

client = genai.Client(api_key=config.GEMINI_API_KEY)

class EntitiesOutput(BaseModel):
    companies: list[str]

class IntelligenceOutput(BaseModel):
    official_website: str = Field(description="The official website of the company.")
    decision: str = Field(description="Strictly 'Retain' or 'Exclude'.")
    wood_species: str = Field(description="木材类别与树种 (例如: **软木**, 松木, 杉木).")
    wood_category: str = Field(description="核心分类：严格输出 '软木', '硬木' 或 '混合'.")
    employee_count: str = Field(description="人员数量或规模描述 (中文).")
    factory_count: str = Field(description="工厂数量描述 (中文).")
    log_scanner_intel: str = Field(description="3D扫描或优化技术的证据及品牌 (中文).")
    automation_details: str = Field(description="自动化流水线、干燥窑等详情 (中文).")
    rationale: str = Field(description="判定理由 (中文).")
    discovery_source: str = Field(description="域名发现的来源提示 (例如: 'Official Site', 'ZoomInfo', 'Inferred from email').")

class StaffMember(BaseModel):
    name: str = Field(description="人员姓名.")
    title: str = Field(description="人员职务.")
    department: str = Field(description="所属部门 (如: 销售, 生产, 采购, 管理层).")
    email: str = Field(description="联系邮箱 (如果没搜到, 尝试按规律推导或留空).")
    role_description: str = Field(description="职责详细描述 (中文).")
    relevance_analysis: str = Field(description="销售关联度分析：为什么此人对原木扫描仪销售很重要 (中文).")
    source_link: str = Field(description="获取此人情报的原始来源链接.")

class StaffIntelligence(BaseModel):
    members: list[StaffMember]

class DirectExtractedPerson(BaseModel):
    company_name: str = Field(description="公司名称 / The name of the company.")
    name: str = Field(description="高管姓名 / The person's full name.")
    title: str = Field(description="高管职务 / The person's job title or role. Leave empty string if not provided.")
    email: str = Field(description="邮件联系方式 / The person's email address. Leave empty string if not provided.")

class DirectExtractionResult(BaseModel):
    people: list[DirectExtractedPerson]

class EmailDraftInfo(BaseModel):
    salutation: str = Field(description="Strictly output 'Mr.' or 'Ms.' based on the gender implied by the person's first name.")
    last_name: str = Field(description="The pure English surname (last name) of the person, completely stripped of any titles, positions, non-English characters, or parenthetical remarks.")
    location: str = Field(description="If the company has a single operating mill/HQ, return the specific town/region (e.g., 'the Noelville area'). If it is a large multi-site global/national corporation, return the Country or State (e.g., 'Australia' or 'New South Wales').")

def retry_ai_call(func, *args, **kwargs):
    max_retries = 3
    base_delay = 15
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).upper()
            if ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "QUOTA" in err_str) and i < max_retries - 1:
                delay = base_delay * (i + 1)
                print(f"    [!] AI Busy/Limit reached. Exception: {e}")
                print(f"    [!] Retrying in {delay}s... (Attempt {i+1}/{max_retries})")
                import time
                time.sleep(delay)
                continue
            raise e

def classify_wood_category(found_species_str: str) -> tuple[str, str]:
    """
    根据本地数据库对搜到的树种字符串进行分类。
    优化了匹配逻辑：优先进行全称/词组匹配，防止 'Red' 误命中。
    """
    if not found_species_str or "未知" in found_species_str or "未查明" in found_species_str:
        return "未知", "未搜寻到具体树种资料。"

    # 清洗和分词逻辑：不再简单按空格拆，而是尝试保留逗号分隔的短语
    found_species_str = found_species_str.lower()
    raw_phrases = re.split(r'[,，、/]+', found_species_str)
    phrases = [p.strip() for p in raw_phrases if p.strip()]
    
    found_soft = []
    found_hard = []
    unmatched_phrases = []

    # 深度匹配逻辑：优先匹配数据库中的完整词组
    for phrase in phrases:
        match_found = False
        
        # 针对每个短语，去数据库里找
        for reg_name, region in WOOD_DB.items():
            # 搜寻每一个分类
            for cat in ["Softwood", "Hardwood"]:
                for db_entry in region.get(cat, []):
                    db_entry_clean = db_entry.lower()
                    # 规则 1：完全包含关系 (例如 'radiata pine' 包含在 'radiata pine logs')
                    # 或 规则 2：正则边界匹配 (确保不是误碰单词中的一部分)
                    if phrase in db_entry_clean or db_entry_clean in phrase:
                        if cat == "Softwood":
                            found_soft.append(phrase)
                        else:
                            found_hard.append(phrase)
                        match_found = True
                        break
                if match_found: break
            if match_found: break
        
        if not match_found:
            # 如果短语没直接中，尝试把短语拆开，但过滤掉无意义的颜色词/方位词
            sub_words = phrase.split()
            ignore_list = ["red", "white", "grey", "gray", "yellow", "blue", "western", "eastern", "southern", "northern", "mountain", "alpine"]
            significant_words = [w for w in sub_words if w not in ignore_list and len(w) > 2]
            
            sub_match = False
            for w in significant_words:
                for reg_name, region in WOOD_DB.items():
                    for cat in ["Softwood", "Hardwood"]:
                        for db_entry in region.get(cat, []):
                            if w in db_entry.lower():
                                if cat == "Softwood":
                                    found_soft.append(w)
                                else:
                                    found_hard.append(w)
                                sub_match = True
                                break
                        if sub_match: break
                    if sub_match: break
                if sub_match: break
            
            if not sub_match:
                unmatched_phrases.append(phrase)

    # 对于没匹配到的品种，启动 AI “实时补课”
    live_discovery_notes = []
    if unmatched_phrases:
        print(f"    [AI-Learning] Database miss for: {unmatched_phrases}. Triggering live lookup...")
        for unknown in unmatched_phrases:
            try:
                # 执行一次微小的联网判定
                completion = client.models.generate_content(
                    model=config.MODEL_NAME,
                    contents=[f"Is '{unknown}' wood classified as a Hardwood or a Softwood? Return strictly 'Hardwood' or 'Softwood'. If unsure, return 'Unknown'."],
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.1
                    )
                )
                answer = completion.text.strip().lower() if completion.text else ""
                if "softwood" in answer:
                    found_soft.append(unknown)
                    live_discovery_notes.append(f"{unknown}(AI查明-软木)")
                    print(f"    [!] AI identified {unknown} as Softwood.")
                elif "hardwood" in answer:
                    found_hard.append(unknown)
                    live_discovery_notes.append(f"{unknown}(AI查明-硬木)")
                    print(f"    [!] AI identified {unknown} as Hardwood.")
                else:
                    print(f"    [?] AI could not classify {unknown}.")
            except Exception as e:
                print(f"    [!] AI lookup failed for {unknown}: {e}")

    # 汇总最终逻辑
    rationale_prefix = ""
    if live_discovery_notes:
        rationale_prefix = f"【动态补课】检测到新树种: {', '.join(live_discovery_notes)} | "

    if not found_soft and not found_hard:
        return "未知", f"{rationale_prefix}搜寻到的树种 ({found_species_str}) 不在数据库且 AI 判定困难。"

    final_soft = list(set(found_soft))
    final_hard = list(set(found_hard))

    if final_soft and final_hard:
        return "混合", f"{rationale_prefix}混合资源：软木({', '.join(final_soft)}) & 硬木({', '.join(final_hard)})。"
    elif final_soft:
        return "软木", f"{rationale_prefix}纯软木：检测到 {', '.join(final_soft)}。"
    else:
        return "硬木", f"{rationale_prefix}纯硬木：检测到 {', '.join(final_hard)}。"

def extract_entities(raw_text: str) -> list[str]:
    print("    [AI] Extracting companies from text...")
    def _call():
        response = client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[raw_text],
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_EXTRACT_ENTITIES,
                response_mime_type="application/json",
                response_schema=EntitiesOutput,
                temperature=0.1
            ),
        )
        return json.loads(response.text).get("companies", [])
    
    try:
        return retry_ai_call(_call)
    except Exception as e:
        print(f"    [!] Final error extracting entities: {e}")
        return []

def run_grounded_research(company_name: str) -> dict:
    import time
    print(f"    [AI-Hunter] Launching Global Domain & Intelligence Hunt for: {company_name}")
    
    # 阶段 1：全球化搜索指令 (侦探增强版)
    hunting_prompt = f"""
Identify the authoritative official web domain and core facts for: {company_name}.
STRATEGY:
1. FIND DOMAIN: The company name may differ from its web domain (e.g. "Probyn Log" -> "probyngroup.ca"). 
   Look for parent groups, branch affiliations, or subsidiary redirects.
   PRIORITIZE: Official .com/.ca sites, Naturally Wood, LinkedIn, ZoomInfo snippets.
2. EXTRACT SPECIES: List specific trees (Pine, Spruce, Fir, SPF, etc.).
3. DETECT ASSETS: Confirm if they have a sawmill, kiln, or manufacturing facility.
4. LOCATION: Confirm their primary operating region (e.g. BC, Alberta, Washington).

FORMAT YOUR BRAIN:
Start with a short "Logic: <your reasoning>" followed by the findings.
"""
    
    def _search_pass():
        res = client.models.generate_content(
            model=config.MODEL_NAME, # 升级后的 2.5 Flash
            contents=[hunting_prompt],
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_DEEP_RESEARCH,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2
            ),
        )
        # 实时打印 AI 的搜网思维链
        if res.text:
            logic_header = res.text.split('\n\n')[0] if '\n\n' in res.text else res.text[:200]
            if "Logic:" in logic_header:
                print(f"    [Scout Reasoning]: {logic_header.split('Logic:')[1].split('\n')[0].strip()}")
        return res

    def _format_pass(research_text):
        return client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[research_text],
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_JSON_FORMATTER,
                response_mime_type="application/json",
                response_schema=IntelligenceOutput,
                temperature=0.1
            ),
        )

    try:
        # Pass 1: Grounded Hunting
        search_res = retry_ai_call(_search_pass)
        research_text = search_res.text if search_res.text else "No research found."
        
        # Pass 2: JSON Formatting (Initial extraction)
        json_res = retry_ai_call(_format_pass, research_text[:15000])
        final_data = json.loads(json_res.text)

        # Pass 3: Python-based Species Classification Override
        # 这个步骤强制使用本地数据库判定分类，解决 AI 不稳定的问题
        species_str = final_data.get("wood_species", "")
        category, rationale = classify_wood_category(species_str)
        
        final_data["wood_category"] = category
        final_data["rationale"] = f"{rationale} | 原始判断: {final_data.get('rationale', '')}"
        
        return final_data
    except Exception as e:
        print(f"    [!] Final error in research for {company_name}: {e}")
        return {
            "official_website": "Error",
            "decision": "Review",
            "wood_species": "错误",
            "wood_category": "未知",
            "employee_count": "错误",
            "factory_count": "错误",
            "log_scanner_intel": "错误",
            "automation_details": "错误",
            "rationale": str(e),
            "discovery_source": "None"
        }


def run_staff_test(company_name: str, model_name: str) -> list[dict]:
    print(f"    [AI-Sniper 2.0] Direct All-Source Recon for: {company_name}...")
    
    # 综合布尔指令：全层级覆盖 + 强制锁定 ZoomInfo
    combined_query = (
        f'"{company_name}" (site:zoominfo.com OR "Owner" OR "CEO" OR "President" OR "Founder" OR "Mill Manager" OR "Plant Manager" OR "Procurement")'
    )
    
    def _execute_recon(query):
        prompt = f"""
You are a High-Precision Executive Sniper. EXHAUSTIVELY find personnel for: {company_name}.
Current Strategy: {query}

CRITICAL RULES:
1. MANDATORY CHECK: If a ZoomInfo link (zoominfo.com) appears in search results, you MUST analyze its personnel list first. It is the primary evidentiary source.
2. LEADERS FIRST: Prioritize identifying the Owner, CEO, or President by name.
3. PERSONAL ONLY: Extract Name, Title, and Department.
4. MAJOR WARNING: DO NOT LOOK FOR EMAILS. DO NOT extract or infer any email addresses.
5. CONTEXTUAL EXTRACTION: Parse snippets for "Name, Role at {company_name}" patterns.
"""
        return retry_ai_call(client.models.generate_content,
            model=model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_STAFF_RESEARCH,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3
            ),
        )

    def _format_pass(research_text):
        return client.models.generate_content(
            model=model_name,
            contents=[research_text],
            config=types.GenerateContentConfig(
                system_instruction="Analyze the research text and return a structured JSON list of personnel. ONLY include Name, Title, and Department.",
                response_mime_type="application/json",
                response_schema=StaffIntelligence,
                temperature=0.1
            ),
        )

    try:
        # 单波次强力搜寻
        res = _execute_recon(combined_query)
        research_text = res.text if res.text else "No staff found."
        
        # 格式化输出 (加固 JSON 解析，增加缓冲区防止长名单截断)
        print(f"    [AI-Sniper] Crystallizing personnel data...")
        # 增加到 35,000 字符缓冲区，处理 Gorman Brothers 级别的大名单
        json_res = retry_ai_call(_format_pass, research_text[:35000])
        members = json.loads(json_res.text).get("members", [])
        
        # 简单姓名去重
        unique_members = []
        seen_names = set()
        for m in members:
            name_clean = m.get("name", "").strip().lower()
            if name_clean and name_clean not in seen_names:
                unique_members.append(m)
                seen_names.add(name_clean)
        
        print(f"    [AI-Sniper] Success: Captured {len(unique_members)} professionals.")
        return unique_members

    except Exception as e:
        print(f"    [!] Sniper 2.0 Failure for {company_name}: {e}")
        return []

def run_direct_extraction(raw_text: str) -> list[dict]:
    print("    [AI] Bypassing pipeline: Automatically extracting contacts directly from unstructured text...")
    
    system_prompt = """
You are an expert Data Extraction AI. The user will provide unstructured text containing companies, names, titles, and email addresses.
Your task is to parse out every individual person mentioned, keeping track of which company they belong to (companies are usually used as section headers before a list of people).

Extract exactly these 4 fields for every person:
1. company_name (公司名称)
2. name (高管姓名)
3. title (高管职务)
4. email (邮件联系方式)

If a title or email is missing, leave the field empty.
"""
    
    def _extract_pass():
        return client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[raw_text],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=DirectExtractionResult,
                temperature=0.1
            ),
        )

    try:
        json_res = retry_ai_call(_extract_pass)
        people_list = json.loads(json_res.text).get("people", [])
        return people_list
    except Exception as e:
        print(f"    [!] Final error extracting unstructured data: {e}")
        return []

def run_company_location_research(company: str, domain: str = "") -> str:
    print(f"    [AI-Locate] Identifying regional footprint for: {company}...")
    
    # 采用“宁模糊不写错”的决策逻辑
    locate_prompt = f"""
Identify the primary operating location or factory headquarters for the timber company: {company}.
Use the official domain as an anchor if provided: {domain}.

CRITICAL POLICY:
- If there is only 1 primary site, output the specific town/area (e.g., 'the Mt Gambier area').
- If there are multiple sites or inconsistency, output the State/Region (e.g., 'the Queensland area').
- If only the country is certain, output the Country (e.g., 'Australia').
- DO NOT guess or hallucinate specific towns if search results are unclear.
- Use 'your region' if no location can be found.

Return ONLY the final location string (e.g. 'the Burnaby area' or 'Australia').
"""
    
    def _search_pass():
        return client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[locate_prompt],
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2
            ),
        )

    try:
        res = retry_ai_call(_search_pass)
        return res.text.strip() if res.text else "your region"
    except Exception as e:
        print(f"    [!] Warning: Error locating {company}: {e}")
        return "your region"

def run_identity_analysis(name: str) -> dict:
    # 纯文本处理，不强制联网，保护隐私且极速
    print(f"    [AI-Identity] Extracting salutation and surname for: {name}")
    
    prompt = f"""
From this input string: '{name}'
1. Determine if the person is likely Mr. or Ms. (Default to Mr. if unclear).
2. Extract ONLY the English Surname (Last Name). Strip all titles (CEO, Junior, etc.).
Return JSON with 'salutation' and 'last_name'.
"""
    def _call():
        response = client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EmailDraftInfo, # Reuse the existing schema for just two fields is fine
                temperature=0.1
            ),
        )
        return json.loads(response.text)

    try:
        return retry_ai_call(_call)
    except Exception:
        fallback_last = name.split()[-1] if name.split() else name
        return {"salutation": "Mr.", "last_name": str(fallback_last), "location": ""}

# Keep the legacy function for backward compatibility but internal refactor
def run_email_context_research(name: str, company: str) -> dict:
    # This is now just a wrapper that handles everything for Step 4
    loc = run_company_location_research(company)
    ident = run_identity_analysis(name)
    ident['location'] = loc
    return ident

