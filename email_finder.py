import os
import argparse
import time
import random
import re
import pandas as pd
from DrissionPage import ChromiumPage

def get_args():
    parser = argparse.ArgumentParser(description="FirLogic Email Finder - DrissionPage Geek Mode")
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

    print("\n---------------------------------------------------------")
    print("[*] 启动极客实习生模式 (DrissionPage 前端伪装自动爬虫)")
    print("---------------------------------------------------------")
    print("[*] 正在拉起本地 Chrome 浏览器...")
    try:
        page = ChromiumPage()
    except Exception as e:
        print(f"\n\033[91m[!] 启动浏览器失败！可能没有找到 Chrome 浏览器。报错: {e}\033[0m")
        return

    print("[*] 导航至 Mailmeteor 首页...")
    page.get('https://mailmeteor.com/tools/email-finder')
    time.sleep(3) # 给它留够时间加载初步的反爬 JS
    
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
            timeout = 15.0 # 最多等 15 秒出结果
            elapsed = 0.0
            found_email = "未查到公开邮箱"
            cloudflare_stuck = True
            
            while elapsed < timeout:
                time.sleep(0.5)
                elapsed += 0.5
                html_text = str(page.html)
                
                # 方案 1：匹配真实的邮箱输出（确保后缀正是我们在查的这家公司）
                # 注意：邮件里可能会有下划线或短横线
                email_regex = r'[a-zA-Z0-9_.+-]+@' + re.escape(domain)
                match = re.search(email_regex, html_text, re.IGNORECASE)
                if match:
                    # 去除非属于目标邮箱的脏数据
                    found_email = match.group(0).lower()
                    cloudflare_stuck = False
                    break
                    
                # 方案 2：捕捉明确的“报错文本”或“没找到文本”
                lower_html = html_text.lower()
                if "unverified email" in lower_html or "couldn't find" in lower_html or "no format found" in lower_html or "not found" in lower_html:
                    found_email = "未查到公开邮箱"
                    cloudflare_stuck = False
                    break
                
                # 方案 3：捕捉 IP 限流（Rate Limit）
                if "too many requests" in lower_html or "limit reached" in lower_html:
                    found_email = "网站提示: IP调用达极限"
                    cloudflare_stuck = False
                    break

            if cloudflare_stuck:
                # 过了 15 秒既没有拿到邮箱，也没有看到 failed 的文字提示，说明整个网页死循环或者卡验证码了
                print("\033[91m    [!!] 警告报错: 这个操作被 Cloudflare 彻底卡死 (死活不出结果)，已被静默防御墙拦截。\033[0m")
                found_email = "被静默防御墙拦截"
            else:
                print(f"    -> 成功抓取: [{found_email}]")

            base_info['邮件联系方式'] = found_email
            results.append(base_info)
            
            # -------- 强制摸鱼休息时间 (规避第二道墙：IP 行为限流) --------
            # [随机 5 到 10 秒]
            delay = random.uniform(5.0, 10.0)
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
