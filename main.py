import os
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd
import re
from collections import Counter
from datetime import datetime

# 🧹 Remove leading time/date (supports comma, dash, time, AM/PM, etc.)
def clean_leading_datetime(text):
    text = text.strip()

    # Remove optional commas/dashes/spaces before time
    text = re.sub(r'^[\s,–-]*\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm|giờ|sáng|chiều)?\s*', '', text)

    # Remove date formats like: Ngày 15/04/2020, 2020-04-15, 15-04-2020
    text = re.sub(r'^[\s,–-]*(Ngày\s+)?\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s*', '', text)
    text = re.sub(r'^[\s,–-]*\d{4}[-/]\d{2}[-/]\d{2}\s*', '', text)

    return text.strip()

# 🧹 Remove taglines like "Nóng nhất hôm nay:"
def clean_news_tagline(text):
    return re.sub(r'^(Nóng nhất hôm nay|Tin mới nhất|Cập nhật):\s*', '', text, flags=re.IGNORECASE)

# 📁 Folder containing PDFs
pdf_folder = '/home/trongan93/Projects/covid-doc-feature/data/2020'

# 📋 Store results
data = []

# 🔁 Loop through all PDF files
for filename in os.listdir(pdf_folder):
    if filename.endswith('.pdf'):
        filepath = os.path.join(pdf_folder, filename)
        print(f"📄 Đang xử lý: {filename}")

        try:
            with pdfplumber.open(filepath) as pdf:
                text = ''
                for page in pdf.pages:
                    page_text = page.extract_text()

                    # OCR fallback
                    if not page_text:
                        img_obj = page.to_image(resolution=300)
                        page_text = pytesseract.image_to_string(img_obj.original, lang='vie')

                    text += page_text + '\n'

                # ----- TITLE -----
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                title_candidates = [line for line in lines if (
                    line.isupper() or line.istitle()
                ) and 10 < len(line) < 120]

                if title_candidates:
                    title = title_candidates[0]
                elif lines:
                    title = lines[0]
                else:
                    title = 'Không tìm thấy tiêu đề'

                # Clean title
                title = clean_leading_datetime(title)
                title = clean_news_tagline(title)

                # ----- DATE -----
                date_patterns = [
                    r'(\d{4}-\d{2}-\d{2})',
                    r'(\d{2}/\d{2}/\d{4})',
                    r'Ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})'
                ]

                date = 'Không tìm thấy ngày'
                for pattern in date_patterns:
                    match = re.search(pattern, text)
                    if match:
                        if len(match.groups()) == 1:
                            date = match.group(1)
                        else:
                            d, m, y = match.groups()
                            date = f"{y}-{int(m):02d}-{int(d):02d}"
                        break

                # ----- SUMMARY -----
                raw_sentences = text.split('。')
                clean_sentences = []

                for sentence in raw_sentences:
                    sentence = clean_leading_datetime(sentence)
                    sentence = clean_news_tagline(sentence)
                    clean_sentences.append(sentence)
                    if len(clean_sentences) == 2:
                        break

                summary = '。'.join(clean_sentences) + '。'

                # ----- KEYWORDS -----
                words = re.findall(r'\b\w{4,}\b', text.lower())
                common_words = Counter(words).most_common(5)
                keywords = ', '.join([w[0] for w in common_words])

                # ----- CATEGORY -----
                categories = {
                    'vắc-xin': 'vắc-xin|tiêm chủng',
                    'hỗ trợ công nhân': 'hỗ trợ công nhân|trợ cấp',
                    'tuyên truyền phòng dịch': 'tuyên truyền|giáo dục phòng dịch',
                    'doanh nghiệp phòng dịch': 'doanh nghiệp|phòng chống dịch',
                    'hoạt động công đoàn': 'hoạt động công đoàn|công đoàn'
                }

                category_vn = None
                for cat, pattern in categories.items():
                    if re.search(pattern, text, re.IGNORECASE):
                        category_vn = cat
                        break

                if not category_vn:
                    keyword_list = [w for w, _ in Counter(words).most_common(20)
                                    if w not in ['công', 'người', 'việc', 'phòng', 'dịch', 'bệnh']]
                    category_vn = f"Tự động分類: {keyword_list[0]}" if keyword_list else 'khác'

                # ----- WORKER-RELATED -----
                worker_related = 'công nhân' in text.lower()

                # ----- SAVE RESULT -----
                data.append({
                    '日期': date,
                    '越南文標題': title,
                    '越南文摘要': summary,
                    '越南文關鍵字': keywords,
                    '越南文分類': category_vn,
                    '是否與工人相關': worker_related
                })

        except Exception as e:
            print(f"❌ Lỗi khi xử lý {filename}: {e}")

# ----- EXPORT TO CSV -----
timestamp = datetime.now().strftime('%Y%m%d_%H%M')
output_path = f'新聞分析結果_越文版_{timestamp}.csv'
df = pd.DataFrame(data)
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"✅ Hoàn tất! Kết quả được lưu tại: {output_path}")
