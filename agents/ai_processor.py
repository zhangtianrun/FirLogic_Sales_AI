from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import sys
import os

# Add parent to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import json

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

class StaffMember(BaseModel):
    name: str = Field(description="人员姓名.")
    title: str = Field(description="人员职务.")
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
    print(f"    [AI-Search] Performing deep research for: {company_name}")
    
    def _search_pass():
        return client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[f"Research {company_name} wood products, sawmills, and factory facilities. We need the official website URL and estimated employee count (look for LinkedIn/business directory info if needed). Also check for log scanning technology or primary processing assets."],
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_DEEP_RESEARCH,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.4
            ),
        )

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
        # Pass 1: Grounded Search
        search_res = retry_ai_call(_search_pass)
        research_text = search_res.text if search_res.text else "No research found."
        
        # Clean text to avoid SDK validation errors for noisy/long input
        # We take the first 15000 characters which is plenty for a summary but safe for the schema
        research_text = research_text[:15000] 
        
        # Pass 2: JSON Formatting
        json_res = retry_ai_call(_format_pass, research_text)
        return json.loads(json_res.text)
    except Exception as e:
        print(f"    [!] Final error in research for {company_name}: {e}")
        return {
            "official_website": "Error",
            "decision": "Review",
            "wood_species": "错误",
            "employee_count": "错误",
            "factory_count": "错误",
            "log_scanner_intel": "错误",
            "automation_details": "错误",
            "rationale": str(e)
        }

def run_staff_test(company_name: str, model_name: str) -> dict:
    print(f"    [AI-Search] Performing Staff Penetration Research for: {company_name} using {model_name}")
    
    def _search_pass():
        return client.models.generate_content(
            model=model_name,
            contents=[f"Exhaustively search for the core management team and managers (Production, Log, Finance) of the company: {company_name}. I need names, titles, and links."],
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_STAFF_RESEARCH,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.4
            ),
        )

    def _format_pass(research_text):
        return client.models.generate_content(
            model=model_name,
            contents=[research_text],
            config=types.GenerateContentConfig(
                system_instruction=config.PROMPT_STAFF_FORMATTER,
                response_mime_type="application/json",
                response_schema=StaffIntelligence,
                temperature=0.1
            ),
        )

    try:
        # Pass 1: Grounded Search
        search_res = retry_ai_call(_search_pass)
        research_text = search_res.text
        
        # Pass 2: JSON Formatting
        json_res = retry_ai_call(_format_pass, research_text)
        return json.loads(json_res.text).get("members", [])
    except Exception as e:
        print(f"    [!] Error in staff research for {company_name} with {model_name}: {e}")
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

def run_email_context_research(name: str, company: str) -> dict:
    print(f"    [AI-Context] Researching demographics and geography for: {name} at {company}...")
    
    # 第一步：搜索并提取原始情报（带联网搜索权限）
    def _search_pass():
        search_prompt = f"""
Research this person: {name} at company: {company}.
I need three pieces of information to write a professional email:
1. Gender of the person (to decide Mr. or Ms.).
2. Their pure English legal Last Name (Surname). Strip away all titles like CEO, Junior, etc.
3. The main operating location of their company or factory. 
   - If they have a specific local mill, give the town/area (e.g., 'the Noelville area').
   - If they are a global corporation, give the country/state (e.g., 'Australia').
Return the findings as raw text.
"""
        return client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[search_prompt],
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2
            ),
        )

    # 第二步：将原始情报整理成标准 JSON 格式（严禁联网，启用 JSON 模式）
    def _format_pass(raw_research_text):
        return client.models.generate_content(
            model=config.MODEL_NAME,
            contents=[raw_research_text],
            config=types.GenerateContentConfig(
                system_instruction="You are a data formatting specialist. Extract the gathered intelligence and output it strictly according to the provided JSON schema.",
                response_mime_type="application/json",
                response_schema=EmailDraftInfo,
                temperature=0.1
            ),
        )

    try:
        # 运行搜索波
        search_res = retry_ai_call(_search_pass)
        raw_text = search_res.text if search_res.text else "No research found."
        
        # 运行格式波
        json_res = retry_ai_call(_format_pass, raw_text)
        return json.loads(json_res.text)
    except Exception as e:
        print(f"    [!] Warning: Error getting context for {name} ({company}): {e}")
        # Default fallback logic
        parts = str(name).replace("——", " ").split()
        fallback_last = parts[-1] if parts else str(name)
        return {"salutation": "Mr.", "last_name": fallback_last, "location": "your region"}

