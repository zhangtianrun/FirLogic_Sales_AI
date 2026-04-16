import argparse
import os
import pandas as pd
from docx import Document
from core.pipeline import process_leads

def read_input(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file {file_path} not found.")
        
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.txt', '.csv']:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == '.docx':
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
        # Convert the whole dataframe to text to pass to the extractor
        return df.to_string()
    else:
        raise ValueError("Unsupported valid format. Use txt, docx, csv, or xlsx.")

def write_to_excel(results, output_path):
    from openpyxl.styles import Font
    
    target_softwood = []
    target_hardwood = []
    excluded = []
    
    for r in results:
        # Copy to avoid modifying the original objects if they are reused
        item = r.copy()
        tab = item.pop("__tab__", "Excluded")
        wood_raw = item.pop("__wood_raw__", "").lower()
        
        if tab == "Target":
            if "硬木" in wood_raw or "hardwood" in wood_raw:
                target_hardwood.append(item)
            else:
                target_softwood.append(item)
        else:
            excluded.append(item)
            
    df_softwood = pd.DataFrame(target_softwood)
    df_hardwood = pd.DataFrame(target_hardwood)
    df_excluded = pd.DataFrame(excluded)
    
    # Updated Column Order (Chinese)
    cols_target = [
        "公司名称", "网站", "木材类别", "人员数量", "厂数量", 
        "业务分类", "具体品种", "自动化程度", 
        "竞品设备", "理由"
    ]
    
    cols_excluded = ["公司名称", "业务分类", "理由", "网站"]
    
    # Reorder columns
    if not df_softwood.empty: df_softwood = df_softwood.reindex(columns=cols_target)
    if not df_hardwood.empty: df_hardwood = df_hardwood.reindex(columns=cols_target)
    if not df_excluded.empty: df_excluded = df_excluded.reindex(columns=cols_excluded)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_softwood.to_excel(writer, sheet_name="重点关注_软木及混合", index=False)
        df_hardwood.to_excel(writer, sheet_name="重点关注_硬木", index=False)
        df_excluded.to_excel(writer, sheet_name="非目标_已剔除", index=False)
        
        workbook = writer.book
        bold_font = Font(bold=True)
        
        for sheetname in writer.sheets:
            worksheet = writer.sheets[sheetname]
            # 1. Bold the header row
            for cell in worksheet[1]:
                cell.font = bold_font
            
            # 2. Adjust column widths and bold "木材类别" column if in sheet
            header_map = {cell.value: cell.column_letter for cell in worksheet[1]}
            
            # Default widths for all columns
            for col in worksheet.columns:
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = 25
            
            # Specific wider columns
            for hdr in ["理由", "自动化程度", "竞品设备", "具体品种"]:
                if hdr in header_map:
                    worksheet.column_dimensions[header_map[hdr]].width = 45
            
            # 3. Bold the wood category column content
            if "木材类别" in header_map:
                col_letter = header_map["木材类别"]
                for row in range(2, worksheet.max_row + 1):
                    worksheet[f"{col_letter}{row}"].font = bold_font

    print(f"\n[Success] Report generated: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Fir Logic - AI Sales Intel Generator (AI Grounding Edition)")
    default_output = os.path.expanduser("~/Downloads/FirLogic_Sales_Intel_Report.xlsx")
    parser.add_argument('--input', type=str, required=True, help="Input file path (txt, docx, or xlsx)")
    parser.add_argument('--output', type=str, default=default_output, help=f"Output file path (default: {default_output})")
    args = parser.parse_args()
    
    print(f"Reading input from {args.input}...")
    try:
        raw_text = read_input(args.input)
    except Exception as e:
        print(f"Error reading file: {e}")
        return
        
    results = process_leads(raw_text)
    
    print(f"\nWriting {len(results)} records to Excel...")
    write_to_excel(results, args.output)

if __name__ == "__main__":
    main()
