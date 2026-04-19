import os
import argparse
import pandas as pd
import imaplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def connect_imap():
    """连接到 Gmail IMAP 服务器"""
    if not config.EMAIL_USER or not config.EMAIL_PASS:
        print("[!] 错误: 请先在 .env 文件中填写 EMAIL_USER 和 EMAIL_PASS (16位专用密码)")
        return None
    
    try:
        print(f"[*] 正在连接到 {config.IMAP_SERVER}...")
        mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
        mail.login(config.EMAIL_USER, config.EMAIL_PASS)
        return mail
    except Exception as e:
        print(f"[!] 连接失败: {e}")
        return None

def find_drafts_folder(mail):
    """自动探测 Gmail 的草稿箱文件夹名称"""
    try:
        # Gmail 的草稿箱通常是 "[Gmail]/Drafts" 或 "Drafts"
        status, folders = mail.list()
        if status == 'OK':
            for folder in folders:
                folder_str = folder.decode('utf-8')
                # 寻找包含 "Draft" 关键字的文件夹
                if 'Draft' in folder_str:
                    # 提取文件夹名称 (通常在最后一个引号内)
                    import re
                    match = re.search(r'"([^"]+)"$', folder_str)
                    if match:
                        return match.group(1)
        return "[Gmail]/Drafts" # 备选默认值
    except:
        return "[Gmail]/Drafts"

def create_draft(mail, folder, subject, body):
    """在指定文件夹中创建一封草稿"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = config.EMAIL_USER
        # 这里暂时不设 To，或者设为 row 中的邮箱
        # msg['To'] = recipient 
        
        msg.attach(MIMEText(body, 'plain'))
        
        # 将邮件转为字节流
        raw_message = msg.as_bytes()
        
        # 使用 append 将邮件存入草稿箱
        # 标志位设为 \Draft 表示这是一封草稿
        mail.append(folder, '\\Draft', imaplib.Time2Internaldate(time.time()), raw_message)
        return True
    except Exception as e:
        print(f"    [!] 创建草稿失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="FirLogic Sales AI - Step 5: Email Dispatcher (Draft Loader)")
    default_input = os.path.expanduser("~/Downloads/FirLogic_Sales_Intel_Report_Step4.xlsx")
    parser.add_argument('--input', type=str, default=default_input, help="Step 4 输出文件路径")
    args = parser.parse_args()

    input_file = os.path.expanduser(args.input)
    if not os.path.exists(input_file):
        print(f"[!] 找不到文件: {input_file}")
        return

    # 读取表格
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"[!] 读取 Excel 失败: {e}")
        return

    # 连接邮箱
    mail = connect_imap()
    if not mail: return

    # 寻找草稿箱
    draft_folder = find_drafts_folder(mail)
    print(f"[*] 探测到草稿箱路径: {draft_folder}")

    print(f"[*] 准备装填 {len(df)} 封邮件...")
    success_count = 0
    
    for idx, row in df.iterrows():
        company = row.get('公司名称', 'Unknown')
        subject = row.get('Subject', '')
        body = row.get('Email body', '')
        recipient = row.get('邮件联系方式', '')

        if not subject or not body:
            print(f"    [-] 跳过第 {idx+1} 行 (缺少主题或正文)")
            continue

        print(f"    [+] 正在为 {company} ({recipient}) 创建草稿...", end="", flush=True)
        
        # 稍微修改一下主题或正文，确保收件人也被包含（可选）
        # 如果需要在草稿中直接填好收件人：
        full_subject = subject
        
        if create_draft(mail, draft_folder, full_subject, body):
            print(" 成功")
            success_count += 1
        else:
            print(" 失败")

    mail.logout()
    print(f"\n[OK] 处理完毕！成功上传 {success_count} 封草稿到您的 Gmail。")
    print("[*] 请现在打开浏览器登录 Gmail，在“草稿箱”中检查并发送。")

if __name__ == "__main__":
    main()
