import sys
import os

# Add agents directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.ai_processor import run_staff_test

# Models for the test
MODEL_FLASH = "gemini-3.1-flash-lite-preview"
MODEL_PRO = "gemini-3.1-pro-preview"

# Test Companies
COMPANIES = ["Timberlink Australia", "Hyne Timber"]

def run_comparison():
    print("="*60)
    print("🚀 FIR LOGIC: PRO VS FLASH MODEL COMPARISON TEST")
    print("目标：深挖人际情报 & 销售角色判定")
    print("="*60)
    
    for company in COMPANIES:
        print(f"\n🏢 目标公司: {company}")
        print("-" * 30)
        
        # 1. Run Flash Test
        print(f"\n[测试 1] 正在运行 实习生模式 (Flash-Lite)...")
        results_flash = run_staff_test(company, MODEL_FLASH)
        
        # 2. Run Pro Test
        print(f"\n[测试 2] 正在运行 专家模式 (Pro)...")
        results_pro = run_staff_test(company, MODEL_PRO)
        
        # Summary
        print(f"\n📊 {company} 对比结果摘要:")
        print(f"   - Flash-Lite 找到成员数: {len(results_flash)}")
        print(f"   - Pro 找到成员数: {len(results_pro)}")
        
        print("\n---【Flash-Lite 模式详情】---")
        if not results_flash:
            print("    [!] 未找到有效成员。")
        for m in results_flash[:3]: # Show top 3
            print(f"    👤 {m['name']} ({m['title']})")
            print(f"    💡 销售判定: {m['relevance_analysis'][:80]}...")
            
        print("\n---【Pro 模式详情】---")
        if not results_pro:
            print("    [!] 未找到有效成员。")
        for m in results_pro[:3]: # Show top 3
            print(f"    👤 {m['name']} ({m['title']})")
            print(f"    💡 销售判定: {m['relevance_analysis'][:80]}...")
        
        print("\n" + "="*30)

if __name__ == "__main__":
    run_comparison()
