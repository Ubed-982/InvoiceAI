import os
import json
import time
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from llm_client import get_llm_client

# Load environment variables 
load_dotenv()


# We use Path objects for better cross-platform compatibility 
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_CSV = BASE_DIR / "extracted_invoices.csv"
DB_PATH = BASE_DIR / "invoices.db"

MAX_RETRIES = 3
RETRY_DELAY = 5 

# --- DATABASE UTILITIES ---

def save_to_db(invoice_data: dict):
    """
    Inserts a single invoice record into the SQLite database.
    We use a context manager (with conn:) to ensure the connection always closes,
    even if an error occurs.
    """
    if not invoice_data:
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
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

# --- PDF UTILITIES ---

def read_pdf_text(pdf_path: Path) -> str:
    """
    Extracts raw text from a PDF file using PyPDF2.
    Note: This works for digital PDFs. Scanned images might need OCR (Future Upgrade).
    """
    try:
        reader = PdfReader(str(pdf_path))
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
    except Exception as e:
        print(f"      ❌ Error reading PDF {pdf_path.name}: {e}")
        return ""

# --- AI CORE ---

def extract_invoice_with_llm(invoice_text: str) -> dict:
    """
    Sends invoice text to the LLM (Gemini/Longcat) and expects a JSON response.
    Includes retry logic to handle API hiccups or rate limits.
    """
    client, model = get_llm_client()

    # We ask for JSON specifically to ensure structured data.
    prompt = f"""
    You are an AI data extraction assistant. 
    
    Task: Extract invoice details and generate a recommended action based on status/amount.
    Output Format: strictly valid JSON.
    
    Data Schema:
    - Invoice_ID (string)
    - Vendor (string)
    - Amount (number)
    - Issue_Date (YYYY-MM-DD)
    - Due_Date (YYYY-MM-DD)
    - Items (list of strings)
    - Store_Location (string)
    - Status (Paid, Pending, Overdue)
    
    Business Logic for 'Recommended_Action':
    - Status 'Overdue' -> "Urgent: Contact Vendor & Pay"
    - Amount > 5000 -> "Requires Manager Approval"
    - Status 'Pending' -> "Schedule for Payment"
    - Status 'Paid' -> "Archive"
    
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
                print(f"      ⚠️ API Error ({e}). Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"      ❌ Failed after {MAX_RETRIES} attempts.")
                raise e

# --- MAIN PIPELINE ---

def process_pdfs(data_dir: Path) -> pd.DataFrame:
    """
    Orchestrates the ETL process:
    1. Find PDFs
    2. Extract Text
    3. Process with AI
    4. Save to DB + CSV
    """
  
    pdf_files = list(data_dir.glob("*.pdf"))
    print(f"📂 Found {len(pdf_files)} PDFs in {data_dir}")

    records = []

    for pdf in pdf_files:
        print(f"   📖 Processing: {pdf.name}...")
        

        text = read_pdf_text(pdf)
        if not text.strip():
            print("      ⚠️ Skipping: No text found (might be an image/scan).")
            continue

        print("      🤖 Sending to AI...")
        invoice_json = extract_invoice_with_llm(text)

        if invoice_json:

            save_to_db(invoice_json)
            
            # Add to list for the CSV export
            records.append(invoice_json)
            
            # Log success for the user
            action = invoice_json.get('Recommended_Action', 'N/A')
            vendor = invoice_json.get('Vendor', 'Unknown')
            print(f"      ✅ Extracted: {vendor} | Action: {action}")
        
        # Polite delay to respect free tier API limits
        time.sleep(1)

    # Convert all records to DataFrame for easy CSV saving
    df = pd.DataFrame(records)

    # Basic data type cleanup before saving
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    for col in ["Issue_Date", "Due_Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

if __name__ == "__main__":
    # Ensure the DB is initialized 
    if not DB_PATH.exists():
        print("⚠️ Database not found. Please run 'python scripts/init_db.py' first.")
    
    # Run the pipeline
    if DATA_DIR.exists():
        invoices_df = process_pdfs(DATA_DIR)

        if not invoices_df.empty:
            print("\n📊 Summary of Extracted Data:")
            print(invoices_df[["Vendor", "Amount", "Status", "Recommended_Action"]])
            
            invoices_df.to_csv(OUTPUT_CSV, index=False)
            print(f"\n✅ Pipeline Complete. Data saved to:\n   - DB: {DB_PATH}\n   - CSV: {OUTPUT_CSV}")
        else:
            print("\n⚠️ No data extracted. Check your PDF files.")
    else:
        print(f"❌ Data directory not found: {DATA_DIR}")