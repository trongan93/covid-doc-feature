import os
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd
import re
from collections import Counter
from datetime import datetime

# Ubuntu: Tesseract will be found automatically (no need to set path)

# Specify your PDF folder
pdf_folder = '/home/trongan93/Projects/covid-doc-feature/data/2023'

# Storage for results
data = []

# Process each PDF file
for filename in os.listdir(pdf_folder):
    if filename.endswith('.pdf'):
        filepath = os.path.join(pdf_folder, filename)
        print(f"📝 Processing: {filename}")

        try:
            with pdfplumber.open(filepath) as pdf:
                text = ''
                for page in pdf.pages:
                    page_text = page.extract_text()

                    # If no text found, use OCR
                    if not page_text:
                        img_obj = page.to_image(resolution=300)
                        page_text = pytesseract.image_to_string(img_obj.original, lang='vie')

                    text += page_text + '\n'

                # Extract title (use longest non-empty line)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                title = max(lines, key=len) if lines else 'Không tìm thấy tiêu đề'

                # Extract date
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                date = date_match.group(1) if date_match else 'Không tìm thấy ngày'

                # Summary (first 2 sentences)
                summary = '。'.join(text.split('。')[:2]) + '。'

                # Keywords (top 5 common long words)
                words = re.findall(r'\b\w{4,}\b', text.lower())
                common_words = Counter(words).most_common(5)
                keywords = ', '.join([w[0] for w in common_words])

                # Categorization
                categories = {
                    'vắc-xin': 'vắc-xin|tiêm chủng',
                    'hỗ trợ công nhân': 'hỗ trợ công nhân|trợ cấp',
                    'tuyên truyền phòng dịch': 'tuyên truyền|giáo dục phòng dịch',
                    'doanh nghiệp phòng dịch': 'doanh nghiệp|phòng chống dịch',
                    'hoạt động công đoàn': 'hoạt động công đoàn|công đoàn'
                }

                category_vn = 'khác'
                for cat, pattern in categories.items():
                    if re.search(pattern, text, re.IGNORECASE):
                        category_vn = cat
                        break

                worker_related = 'công nhân' in text.lower()

                # Append result
                data.append({
                    '日期': date,
                    '越南文標題': title,
                    '越南文摘要': summary,
                    '越南文關鍵字': keywords,
                    '越南文分類': category_vn,
                    '是否與工人相關': worker_related
                })

        except Exception as e:
            print(f"⚠️ Error processing {filename}: {e}")

# Export results as CSV (UTF-8 for Vietnamese support)
timestamp = datetime.now().strftime('%Y%m%d_%H%M')
output_path = f'新聞分析結果_越文版_{timestamp}.csv'
df = pd.DataFrame(data)
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"✅ 分析完成，結果儲存於：{output_path}")
