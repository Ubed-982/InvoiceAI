import os
import json
import time
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from datetime import datetime, date

#importing the LLM client
try:
    from llm_client import get_llm_client
except ImportError:
    get_llm_client = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_CSV = BASE_DIR / "extracted_invoices.csv"
DB_PATH = BASE_DIR / "invoices.db"

MAX_RETRIES = 3
RETRY_DELAY = 5 

#DATABASE UTILITIES 

def save_to_db(invoice_data: dict):
    if not invoice_data: return
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO invoices (
                    invoice_id, vendor, amount, issue_date, due_date, 
                    items, location, status, recommended_action
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_data.get('Invoice_ID'),
                invoice_data.get('Vendor'),
                invoice_data.get('Amount'),
                invoice_data.get('Issue_Date'),
                invoice_data.get('Due_Date'),
                str(invoice_data.get('Items')), 
                invoice_data.get('Store_Location'),
                invoice_data.get('Status'),
                invoice_data.get('Recommended_Action')
            ))
            conn.commit()
            print(f"      💾 Saved {invoice_data.get('Invoice_ID', 'Unknown ID')} to Database.")
    except sqlite3.Error as e:
        print(f"      ❌ Database Error: {e}")

#PDF UTILITIES

def read_pdf_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
    except Exception as e:
        print(f"      ❌ Error reading PDF {pdf_path}: {e}")
        return ""

#BUSINESS LOGIC

def apply_business_rules(invoice: dict) -> dict:
    """
    Applies deterministic business logic to the extracted data.
    """
    try:
        # 1. Parse Data
        today = date.today()
        try:
            due_date = datetime.strptime(invoice.get("Due_Date", ""), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            due_date = None

       
        raw_status = invoice.get("Payment_Status", "").lower().strip()
        
        try:
            amount = float(invoice.get("Amount", 0))
        except (ValueError, TypeError):
            amount = 0.0

       
        
        # Rule 1: Paid Check (FIXED: Strict check so "unpaid" doesn't trigger it)
        if raw_status == "paid":
            invoice["Status"] = "Paid"
            invoice["Recommended_Action"] = "Archive"
            return invoice
        
        # Rule 2: High Value Check (Moved Up)
        if amount > 5000:
             invoice["Status"] = "Pending"
             invoice["Recommended_Action"] = "Requires Manager Approval"
             return invoice
         
        # Rule 2: Overdue Check
        if due_date and today > due_date:
            invoice["Status"] = "Overdue"
            invoice["Recommended_Action"] = "Urgent: Contact Vendor & Pay"
            return invoice

        # Rule 3: High Value Check
        if amount > 5000:
            invoice["Status"] = "Pending"
            invoice["Recommended_Action"] = "Requires Manager Approval"
            return invoice

        # Default
        invoice["Status"] = "Pending"
        invoice["Recommended_Action"] = "Schedule for Payment"
        return invoice

    except Exception as e:
        print(f"      ⚠️ Logic Error: {e}")
        invoice["Status"] = "Review Required"
        invoice["Recommended_Action"] = "Manual Review"
        return invoice


def extract_invoice_with_llm(invoice_text: str) -> dict:
    """
    LLM is used STRICTLY for extraction, not decision making.
    """
    if not get_llm_client: return {}
    client, model = get_llm_client()

    
    prompt = f"""
    You are an AI data extraction assistant. 
    
    Task: Extract factual invoice data ONLY. 
    Do NOT apply business rules. Do NOT infer urgency.
    
    Output Format: strictly valid JSON.
    
    Data Schema:
    - Invoice_ID (string)
    - Vendor (string)
    - Amount (number)
    - Issue_Date (YYYY-MM-DD)
    - Due_Date (YYYY-MM-DD)
    - Items (list of strings)
    - Store_Location (string)
    - Payment_Status (Strictly: "Paid" or "Unpaid")
    
    Input Text:
    \"\"\"
    {invoice_text[:10000]} 
    \"\"\"
    """

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a JSON-only extraction bot."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print(f"      ❌ Failed after {MAX_RETRIES} attempts.")
                raise e

#Main Processing Function

def analyze_invoice_file(file_path: str):
    print(f"🚀 Analyzing file: {file_path}")
    text = read_pdf_text(file_path)
    if not text.strip(): return None

   
    print("      🤖 Sending to AI...")
    raw_data = extract_invoice_with_llm(text)
    

    print("      🧠 Applying Business Rules...")
    enriched_data = apply_business_rules(raw_data)
    
    return enriched_data

def process_pdfs(data_dir: Path) -> pd.DataFrame:
    pdf_files = list(data_dir.glob("*.pdf"))
    print(f"📂 Found {len(pdf_files)} PDFs in {data_dir}")
    records = []

    for pdf in pdf_files:
        print(f"   📖 Processing: {pdf.name}...")
        invoice_json = analyze_invoice_file(str(pdf))
        if invoice_json:
            save_to_db(invoice_json)
            records.append(invoice_json)
            print(f"      ✅ Extracted: {invoice_json.get('Vendor')} | Action: {invoice_json.get('Recommended_Action')}")
        time.sleep(1)

    df = pd.DataFrame(records)
 
    if "Amount" in df.columns: df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    for col in ["Issue_Date", "Due_Date"]:
        if col in df.columns: df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


if __name__ == "__main__":
    if not DB_PATH.exists():
        print("⚠️ Database not found. Run init_db.py.")
    if DATA_DIR.exists():
        invoices_df = process_pdfs(DATA_DIR)
        if not invoices_df.empty:
            invoices_df.to_csv(OUTPUT_CSV, index=False)
            print(f"\n✅ Pipeline Complete.")
    else:
        print(f"❌ Data directory not found: {DATA_DIR}")