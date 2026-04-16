import time
from agents import ai_processor
import config

def process_leads(raw_text: str):
    # Step 0: Extract
    companies = ai_processor.extract_entities(raw_text)
    print(f"\n[Pipeline] Found {len(companies)} companies to process.")
    
    results = []
    
    for current, company in enumerate(companies, 1):
        print(f"\n[{current}/{len(companies)}] Processing: {company}")
        
        # Grounded Analysis
        intel = ai_processor.run_grounded_research(company)
        decision = intel.get("decision", "Exclude")
        
        info = {
            "公司名称": company,
            "网站": intel.get("official_website", "未找到"),
            "木材类别": intel.get("wood_species", "未知"),
            "人员数量": intel.get("employee_count", "未知"),
            "厂数量": intel.get("factory_count", "未知"),
            "业务分类": "重点关注" if decision == "Retain" else "非目标",
            "具体品种": intel.get("wood_species", "未知"), # Keep detailed if needed
            "自动化程度": intel.get("automation_details", "未知"),
            "竞品设备": intel.get("log_scanner_intel", "未知"),
            "理由": intel.get("rationale", "未知"),
            "__tab__": "Target" if decision == "Retain" else "Excluded",
            "__wood_raw__": intel.get("wood_species", "") # Hidden helper for sheet splitting
        }
        
        if decision == "Retain":
            print(f"    [+] Target Verified by AI Search!")
        else:
            print(f"    [-] Excluded by AI Search.")
            
        results.append(info)
            
    return results
