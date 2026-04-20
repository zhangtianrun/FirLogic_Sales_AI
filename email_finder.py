import os
import argparse
import time
import random
import re
import pandas as pd
import config
from DrissionPage import ChromiumPage, ChromiumOptions

def get_args():
    parser = argparse.ArgumentParser(description="FirLogic Email Finder - DrissionPage Geek Mode")
    parser.add_argument('--input', type=str, default="FirLogic_Sales_Intel_Report_Step2.xlsx", help="Step 2 的输入文件路径")
    parser.add_argument('--output', type=str, default="~/Downloads/FirLogic_Sales_Intel_Report_Step3.xlsx", help="生成 Step 3 的输出文件路径")
    return parser.parse_args()

def search_for_domain(company_name, client):
    """如果Excel里没有网站，主动去搜一下官网域名 (全透明调试版)"""
    import config
    print(f"\n      [🔎] 侦探模式：正在为 {company_name} 进行全网溯源...")
    try:
        from google.genai import types
        # 故意放开限制，让 AI 先解释，再给结果
        prompt = f"""
TASK: Identify the authoritative official web domain for: {company_name}.
CONSIDERATIONS: 
- Parent/Subsidiary relationships (e.g. Probyn Log -> probyngroup.ca).
- Industry directories like Naturally Wood, ZoomInfo, or LinkedIn.
- Official PDF reports or news mentions if the site is hard to find.

FORMAT:
Reasoning: <Your short detective logic here>
Domain: <The final domain.com only>

If no domain is found, output "unknown".
"""
        res = client.models.generate_content(
            model=config.MODEL_DETECTIVE, 
            contents=[prompt],
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1
            )
        )
        
        full_text = res.text.strip()
        # 调试日志：打印 AI 的思考过程
        print(f"      [AI 思维链]:\n      {full_text.split('Domain:')[0].strip()}")
        
        if "Domain:" in full_text:
            domain = full_text.split("Domain:")[1].strip().lower()
        else:
            domain = full_text.lower()

        # 过滤冗余字符
        domain = domain.split("\n")[0].strip()
        for prefix in ["https://", "http://", "www."]:
            if domain.startswith(prefix):
                 domain = domain[len(prefix):]
        domain = domain.split('/')[0].strip()
        
        if domain == "unknown" or len(domain) < 3:
            return None
            
        print(f"      [✓] 锁定域名: {domain}")
        return domain
    except Exception as e:
        print(f"      [!] 搜网过程出错: {e}")
        return None

def clean_domain(url):
    """提取干净的域名"""
    if not url or pd.isna(url) or not str(url).strip() or str(url).lower() == 'nan':
        return None
    url = str(url).strip().lower()
    if url == 'unknown':
        return None
    for prefix in ["https://", "http://", "www."]:
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.split('/')[0].strip()

def format_excel(file_path):
    """把生成的格子调大一点"""
    import openpyxl
    wb = openpyxl.load_workbook(file_path)
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
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
        # 读取时强制要求处理合并单元格的问题
        df = pd.read_excel(input_file, sheet_name="重点关注_软木及混合")
        
        # 核心修复：确保每一行都有公司和网站的上下文
        if '公司名称' in df.columns:
            df['公司名称'] = df['公司名称'].ffill()
        if '网站' in df.columns:
            df['网站'] = df['网站'].ffill()
            
        # 预清洗：删除没有任何人员姓名的行
        df = df[df['高管姓名'].notna() & (df['高管姓名'].str.strip() != "")]
        
    except Exception as e:
        print(f"读取Excel失败: {e}")
        return

    results = []
    missing_info = []

    print("\n---------------------------------------------------------")
    print("[*] 启动极客实习生模式 (DrissionPage 前端伪装自动爬虫)")
    print("---------------------------------------------------------")
    print("[*] 正在拉起本地 Chrome 浏览器...")
    try:
        co = ChromiumOptions()
        # 严禁挂起后台隐藏的窗口
        co.set_argument('--disable-backgrounding-occluded-windows')
        # 严禁限制后台标签页的定时器（保持全速运行）
        co.set_argument('--disable-background-timer-throttling')
        # 严禁将后台渲染器降级
        co.set_argument('--disable-renderer-backgrounding')
        
        page = ChromiumPage(co)
    except Exception as e:
        print(f"\n\033[91m[!] 启动浏览器失败！可能没有找到 Chrome 浏览器。报错: {e}\033[0m")
        return

    # 初始化 Gemini 客户端用于潜在的域名搜索
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    print("[*] 导航至 Mailmeteor 首页...")
    page.get('https://mailmeteor.com/tools/email-finder')
    time.sleep(3) 
    
    for idx, row in df.iterrows():
        company = str(row.get('公司名称', '')).strip()
        name = str(row.get('高管姓名', '')).strip()
        title = str(row.get('高管职务', '')).strip()
        website = str(row.get('网站', '')).strip()
        
        domain = clean_domain(website)
        
        # 核心逻辑：如果域名为空，实时联网搜寻
        if not domain:
            domain = search_for_domain(company, client)
            
        base_info = {
            '公司名称': company,
            '高管姓名': name,
            '高管职务': title,
            '邮件联系方式': ""
        }

        # 验证人员信息的合法性
        is_valid = True
        if not name or name.lower() == 'unknown' or len(name.split()) < 2:
            print(f"[-] 跳过: {name} (姓名不完整)")
            is_valid = False
        if not domain or domain.lower() == 'unknown':
            print(f"[!] 跳过: {name} @ 未知域名 (缺少关键信息)")
            is_valid = False

        if not is_valid:
            base_info['邮件联系方式'] = '缺乏域名或全名'
            missing_info.append(base_info)
            continue

        print(f"[>] 模拟查找: {name} @ {domain} ... ")
        
        try:
            # 找到输入框
            name_input = page.ele('@id=fullName', timeout=5)
            domain_input = page.ele('@id=domain', timeout=2)
            btn = page.ele('@aria-label=Find email address', timeout=2)
            
            if not name_input or not domain_input or not btn:
                print("\033[91m[!] 页面元素丢失，可能网页结构已更改，或者被防机器人的 5 秒盾完全挡住。\033[0m")
                base_info['邮件联系方式'] = '防爬盾致页面加载失败'
                results.append(base_info)
                continue
            
            # 填表动作（极速，不要傻等）
            name_input.clear()
            name_input.input(name)
            time.sleep(random.uniform(0.1, 0.4))
            
            domain_input.clear()
            domain_input.input(domain)
            time.sleep(random.uniform(0.1, 0.4))
            
            btn.click()
            
            # --- 视觉凝视：监听 DOM 的变化判定结果 ---
            timeout = 120.0 # 最多等 120 秒出结果（两分钟极光级防御，应对超慢速服务器）
            elapsed = 0.0
            found_email = "等待结果超时"
            cloudflare_stuck = True
            
            while elapsed < timeout:
                time.sleep(0.5)
                elapsed += 0.5
                
                # 方案 1：全局捕捉 IP 封锁（如果被封锁，通常是弹窗或覆盖全屏）
                body_ele = page.ele('t:body', timeout=0)
                visible_text = body_ele.text.lower() if body_ele else ""
                
                if "too many requests" in visible_text or "limit reached" in visible_text:
                    found_email = "网站提示: IP调用达极限"
                    cloudflare_stuck = False
                    break
                
                # 方案 2：精准狙击结果渲染区域（也就是您截图里的 #email-finder-results）
                result_section = page.ele('#email-finder-results', timeout=0)
                if result_section:
                    sec_text = result_section.text.lower()
                    
                    # 极其精确：我们已经在这个结果小盒子里了，只要这里面出现任何合法的邮箱格式（不再死磕某个特定域名，彻底防止 usa 这种别名），直接掏出来！
                    # 也不死磕 CSS 类名（Mailmeteor 对不同认证状态的邮箱可能会换衣服变色）
                    generic_email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
                    match = re.search(generic_email_regex, sec_text)
                    if match:
                        found_email = match.group(0).lower()
                        cloudflare_stuck = False
                        break
                    
                    # 如果结果区域里没有邮箱格式，说明出错了，直接读取该区域里的报错文本
                    if "no result" in sec_text or "not found" in sec_text or "couldn't find" in sec_text or "no format found" in sec_text or "unverified email" in sec_text:
                        found_email = "No results found"
                        cloudflare_stuck = False
                        break

            if cloudflare_stuck:
                # 过了 120 秒既没有拿到邮箱，也没有看到 failed 的文字提示
                print("\033[91m    [!!] 警告报错: 这个操作卡死了至少 120 秒 (死活不出结果)，疑似遭到 Cloudflare 发难或者网页结构卡顿。\033[0m")
                found_email = "被静默防御墙拦截"
            else:
                print(f"    -> 成功抓取: [{found_email}]")

            base_info['邮件联系方式'] = found_email
            results.append(base_info)
            
            # -------- 强制摸鱼休息时间 (规避第二道墙：IP 行为限流) --------
            # [随机 4 到 8 秒马拉松乌龟档：速度提升，但在大型列表中提供长续航安全性]
            delay = random.uniform(4.0, 8.0)
            print(f"    [摸鱼防封] 实习生正在假装看屏幕，强制休息 {delay:.2f} 秒...\n")
            time.sleep(delay)
            
            # 刷新页面以清理上一轮的数据痕迹（有助于降低被封禁几率）
            page.get('https://mailmeteor.com/tools/email-finder', retry=2)
            time.sleep(1.5)
            
        except Exception as e:
            print(f"\033[91m    [!!] 页面交互崩溃: {e}\033[0m")
            base_info['邮件联系方式'] = '页面崩溃跳过'
            results.append(base_info)
            break 
            
    print("[*] 断开全息操控，关闭浏览器...")
    page.quit()

    if not results and not missing_info:
        print("\n[-] 警告：名单完全为空，未生成任何表格。")
        return

    print(f"[*] 综合记录 {len(results)} 条。正在写入 {output_file} ... ", end="", flush=True)
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
