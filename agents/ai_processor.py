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
                print(f"    [!] AI Busy/Limit reached. Retrying in {delay}s... (Attempt {i+1}/{max_retries})")
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
        research_text = search_res.text
        
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
