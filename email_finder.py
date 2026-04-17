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
            timeout = 60.0 # 最多等 60 秒出结果（真正的无限等很容易造成永久死锁，对于澳洲等慢速服务器需要更长耐力）
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
                # 过了 60 秒既没有拿到邮箱，也没有看到 failed 的文字提示
                print("\033[91m    [!!] 警告报错: 这个操作卡死了至少 60 秒 (死活不出结果)，疑似遭到 Cloudflare 发难或者网页结构卡顿。\033[0m")
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
