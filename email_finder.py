import os
import argparse
import pandas as pd
import requests
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()
CLEAROUT_API_KEY = os.getenv("CLEAROUT_API_KEY")

def get_args():
    parser = argparse.ArgumentParser(description="FirLogic Email Finder (Step 3)")
    parser.add_argument('--input', type=str, default="FirLogic_Sales_Intel_Report_Step2.xlsx", help="Step 2 的输入文件路径")
    parser.add_argument('--output', type=str, default="~/Downloads/FirLogic_Sales_Intel_Report_Step3.xlsx", help="生成 Step 3 的输出文件路径")
    return parser.parse_args()

def clean_domain(url):
    """提取干净的域名"""
    if pd.isna(url) or not str(url).strip():
        return None
    url = str(url).strip().lower()
    if url == 'unknown':
        return None
    for prefix in ["https://", "http://", "www."]:
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.split('/')[0].strip()

def find_email_api(name, domain):
    if not CLEAROUT_API_KEY or CLEAROUT_API_KEY == "your_clearout_api_key_here":
        return "请在.env填写CLEAROUT_API_KEY"

    url = "https://api.clearout.io/v2/email_finder/instant"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CLEAROUT_API_KEY}"
    }
    payload = {
        "name": name,
        "domain": domain,
        "timeout": 30000,
        "queue": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=35)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data", {}).get("emails"):
                first_match = data["data"]["emails"][0]
                # API returns a dict, e.g. {'email_address': 'scottlewis@claymark.com', ...}
                if isinstance(first_match, dict) and "email_address" in first_match:
                    return first_match["email_address"]
                return str(first_match)
            else:
                return "未查到公开邮箱"
        elif response.status_code == 402:
            return "API额度不足"
        elif response.status_code == 401:
            return "API Key 无效"
        elif response.status_code == 429:
            return "API请求过于频繁"
        else:
            return f"API查询失败 ({response.status_code})"
    except Exception as e:
        return f"查询异常: {str(e)}"

def format_excel(file_path):
    """把生成的格子调大一点"""
    import openpyxl
    wb = openpyxl.load_workbook(file_path)
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # 设置列宽
        ws.column_dimensions['A'].width = 30  # 公司名称
        ws.column_dimensions['B'].width = 25  # 高管姓名
        ws.column_dimensions['C'].width = 35  # 高管职务
        ws.column_dimensions['D'].width = 40  # 邮件联系方式
        
    wb.save(file_path)

def main():
    args = get_args()
    input_file = os.path.expanduser(args.input)
    output_file = os.path.expanduser(args.output)

    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}。请检查路径。")
        return
        
    try:
        df = pd.read_excel(input_file, sheet_name="重点关注_软木及混合")
        if '公司名称' in df.columns:
            df['公司名称'] = df['公司名称'].ffill()
        if '网站' in df.columns:
            df['网站'] = df['网站'].ffill()
    except Exception as e:
        print(f"读取Excel失败: {e}")
        return

    results = []
    missing_info = []

    import time
    print("[*] 开始执行 Clearout API 极速邮箱查询 (启动 14 RPM 极速限流保护)...")

    request_count = 0
    batch_start_time = 0.0

    for idx, row in df.iterrows():
        company = str(row.get('公司名称', '')).strip()
        name = str(row.get('高管姓名', '')).strip()
        title = str(row.get('高管职务', '')).strip()
        website = str(row.get('网站', '')).strip()
        
        domain = clean_domain(website)
        
        base_info = {
            '公司名称': company,
            '高管姓名': name,
            '高管职务': title,
            '邮件联系方式': ""
        }

        is_valid = True
        if not domain:
            is_valid = False
        elif not name or name.lower() == 'unknown' or len(name.split()) < 2:
            is_valid = False

        if not is_valid:
            print(f"[-] 跳过: {name} @ {company} (信息不完整)")
            base_info['邮件联系方式'] = '缺乏域名或全名'
            missing_info.append(base_info)
            continue

        # == 批次限流计时的起点 ==
        if request_count == 0:
            batch_start_time = time.time()

        print(f"[>] 第 {request_count+1}/14 次请求 - 查找: {name} @ {domain} ... ", end="", flush=True)
        email = find_email_api(name, domain)
        print(f"[{email}]")
        
        base_info['邮件联系方式'] = email
        results.append(base_info)
        
        # == 限流检测与阻断逻辑 ==
        request_count += 1
        if request_count == 14:
            elapsed = time.time() - batch_start_time
            if elapsed < 60.0:
                # 满 14 次且耗时不足一分钟，等到一分钟并额外缓冲 2 秒
                sleep_time = 60.0 - elapsed + 2.0
                print(f"\n[!] 触发限流保护: 已用尽 14 次并发额度 (耗时 {elapsed:.1f}s)。")
                print(f"[!] 强制冷却洗牌... 等待 {sleep_time:.1f} 秒后重置计时池。")
                time.sleep(sleep_time)
                print("[*] 冷却完毕，重新进入下一个 14 RPM 周期。\n")
            # 无论是否罚站，满 14 次后计时器与计数器清零
            request_count = 0

    if not results and not missing_info:
        print("\n[-] 警告：名单完全为空，未生成任何表格。")
        return

    print(f"[*] 写入 {output_file} ... ", end="", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        if results:
            pd.DataFrame(results).to_excel(writer, sheet_name='查询结果', index=False)
        if missing_info:
            pd.DataFrame(missing_info).to_excel(writer, sheet_name='找不到(缺失信息)', index=False)
    print("完成")

    print("[*] 正在精美重排(拉宽单元格)... ", end="", flush=True)
    try:
        format_excel(output_file)
        print("完成")
    except Exception as e:
        print(f"失败 ({e})")

    print(f"\n[OK] 第三功能执行完成！请前往 {output_file} 查收。")

if __name__ == "__main__":
    main()
