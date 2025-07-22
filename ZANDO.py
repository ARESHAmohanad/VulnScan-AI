import os
import sys
import json
import requests
import datetime
from fpdf import FPDF
from dotenv import load_dotenv
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QDialog, QComboBox, QPushButton, QCheckBox

# =============== تحميل متغيرات البيئة ===============
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS_AI = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

SUPPORTED_EXTS = [".py", ".js", ".php", ".java", ".c", ".cpp", ".rb", ".go",".yml",".html",".cfg",".toml",".lock"]

# =============== إعدادات التطبيق الافتراضية ===============
SETTINGS_PATH = "user_settings.json"
def load_settings():
    defaults = {
        "theme": "dark",
        "language": "ar",
        "scan_level": "accurate" # options: fast, accurate, deep
    }
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            defaults.update(user)
        except Exception:
            pass
    return defaults

def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

APP_SETTINGS = load_settings()

# =============== اللغة (ديناميكي) ===============
def tr(text):
    ar = {
        "AI Cyber Security Analyzer": "محلل أمني سيبراني بالذكاء الاصطناعي",
        "Choose Project Folder": "اختر مجلد المشروع",
        "Scan Project": "🔍 فحص مشروع",
        "Scan Reports": "تقارير الفحص",
        "Scan History": "سجل الفحوصات",
        "Settings": "الإعدادات",
        "Dark Mode": "الوضع الداكن",
        "Light Mode": "الوضع الفاتح",
        "Language": "اللغة",
        "Scan Level": "مستوى الفحص",
        "Fast": "سريع",
        "Accurate": "دقيق",
        "Deep": "عميق",
        "Save": "حفظ",
        "Cancel": "إلغاء",
        "Vulnerabilities": "الثغرات",
        "Critical": "خطيرة",
        "Medium": "متوسطة",
        "Low": "ضعيفة",
        "No Vulnerabilities Found": "لم يتم العثور على ثغرات أمنية",
        "Scan Date": "تاريخ الفحص",
        "Total Files": "عدد الملفات",
        "Critical Flaws": "ثغرات خطيرة",
        "Medium Flaws": "ثغرات متوسطة",
        "Low Flaws": "ثغرات ضعيفة",
        "Show Report": "عرض التقرير",
        "File": "الملف",
        "Analysis": "التحليل",
        "Report Saved To": "تم حفظ التقرير في",
        "Ready": "جاهز",
        "Scan Finished": "تم الانتهاء من الفحص",
        "No Supported Files": "❗ لم يتم العثور على ملفات مدعومة!",
        "OK": "موافق",
        "Error": "خطأ",
        "Scan Error Occurred": "حدث خطأ أثناء الفحص:"
    }
    return ar[text] if APP_SETTINGS["language"] == "ar" and text in ar else text

# =============== إرسال التقرير عبر تيليجرام (اختياري) ===============
def send_telegram_file(file_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ تيليجرام غير مفعّل، تخطّي الإرسال.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TELEGRAM_CHAT_ID}
            resp = requests.post(url, files=files, data=data)
            if resp.status_code != 200:
                print("❌ فشل إرسال التقرير إلى تيليجرام:", resp.text)
    except Exception as e:
        print("❌ خطأ في إرسال تيليجرام:", e)

# =============== التواصل مع OpenRouter ===============
def ask_openrouter(prompt, model="openai/gpt-4o", max_tokens=1500):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=HEADERS_AI, data=json.dumps(payload), timeout=90)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"AI API Error: {resp.status_code} {resp.text}"
    except Exception as e:
        return f"خطأ أثناء الاتصال بـ OpenRouter: {e}"

# =============== تحليل الملف البرمجي ===============
def analyze_code_file(file_path, code, rel_path):
    scan_level = APP_SETTINGS.get("scan_level", "accurate")
    if scan_level == "fast":
        max_tokens = 500
        mode_desc = "تحليل سريع: فقط كشف أخطر الثغرات الظاهرة."
    elif scan_level == "deep":
        max_tokens = 3000
        mode_desc = "تحليل عميق: كشف وتحليل شامل جدًا حتى الثغرات الصغيرة."
    else:
        max_tokens = 1500
        mode_desc = "تحليل دقيق: كشف وتحليل متوازن للثغرات."
    
    prompt = f"""
أنت خبير أمني سيبراني محترف جدًا، مختص في اكتشاف وتحليل الثغرات الأمنية الخطيرة، خصوصًا ثغرات يوم الصفر (Zero-Day).
المطلوب: 
- تحليل الملف التالي بشكل احترافي جدًا في {mode_desc}
- استخرج كل ثغرة وصنفها حسب خطورتها إلى (خطيرة، متوسطة، ضعيفة).
- لكل ثغرة: 
  - اذكر نوعها بدقة مع شرح موجز
  - مدى خطورتها (خطيرة/متوسطة/ضعيفة)
  - السطر أو جزء الكود المسبب مع رقم السطر لو أمكن
  - طريقة استغلال الثغرة بشكل عملي (Proof of Concept)
  - شرح تقني مفصل
  - توصيات عملية للإغلاق أو الحد من الخطر
- إذا لم توجد ثغرات: صرّح "لا توجد ثغرة أمنية"

المسار: {rel_path}
الكود:
{code[:6000]}
"""
    return ask_openrouter(prompt, max_tokens=max_tokens)

# =============== استعراض الملفات داخل مجلد المشروع ===============
def walk_project_files(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_EXTS:
                yield os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path)

# =============== إنشاء تقرير PDF ===============
def generate_pdf_report(results, project_name, summary, output_pdf):
    pdf = FPDF()
    pdf.add_font("Unicode", "", "fonts/DejaVuSans.ttf", uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Unicode", "", 16)
    pdf.cell(0, 13, f"{tr('AI Cyber Security Analyzer')} : {project_name}", ln=True, align="C")
    pdf.set_font("Unicode", "", 12)
    pdf.cell(0, 10, f"{tr('Scan Date')}: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="R")
    pdf.ln(6)
    pdf.set_font("Unicode", "", 13)
    pdf.set_text_color(140, 0, 0)
    pdf.multi_cell(0, 8, summary)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(7)
    for entry in results:
        pdf.set_font("Unicode", "", 12)
        pdf.set_text_color(0, 0, 128)
        pdf.cell(0, 8, f"{tr('File')}: {entry['rel_path']}", ln=True)
        pdf.set_font("Unicode", "", 11)
        pdf.set_text_color(60, 60, 60)
        safe_text = entry['analysis'].replace('\u202a', '').replace('\u202c', '')
        pdf.multi_cell(0, 7, safe_text)
        pdf.ln(5)
    pdf.set_text_color(0, 0, 0)
    pdf.output(output_pdf, "F")

# =============== إنشاء تقرير JSON ===============
def generate_json_report(results, project_name, summary, output_json):
    report = {
        "project_name": project_name,
        "scan_date": datetime.datetime.now().isoformat(),
        "summary": summary,
        "results": results
    }
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

# =============== تحليل إحصاءات الثغرات من نتائج AI ===============
import re
def extract_vuln_stats(results):
    crit, med, low = 0, 0, 0
    for entry in results:
        text = entry['analysis']
        crit += len(re.findall(r'خطيرة|Critical', text, re.I))
        med  += len(re.findall(r'متوسطة|Medium', text, re.I))
        low  += len(re.findall(r'ضعيفة|Low', text, re.I))
    return crit, med, low

def create_summary(project_name, files_count, crit, med, low):
    total = crit + med + low
    summary = f"{tr('Project')}: {project_name}\n{tr('Total Files')}: {files_count}\n"
    summary += f"{tr('Critical Flaws')}: {crit} | {tr('Medium Flaws')}: {med} | {tr('Low Flaws')}: {low}\n"
    if total == 0:
        summary += f"\n{tr('No Vulnerabilities Found')}"
    else:
        summary += f"\n{tr('Vulnerabilities')}: {total}"
    return summary

# =============== سجل الفحوصات (History) ===============
HISTORY_FILE = "scan_history.json"
def add_to_history(project_name, pdf_path, json_path, summary):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except Exception: pass
    history.append({
        "project_name": project_name,
        "pdf_path": pdf_path,
        "json_path": json_path,
        "summary": summary,
        "date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception: return []
    return []

# =============== نافذة الإعدادات ===============
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Settings"))
        layout = QtWidgets.QVBoxLayout(self)

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([tr("Dark Mode"), tr("Light Mode")])
        self.theme_combo.setCurrentIndex(0 if APP_SETTINGS["theme"]=="dark" else 1)
        layout.addWidget(QLabel(tr("Dark Mode") + "/" + tr("Light Mode")))
        layout.addWidget(self.theme_combo)

        # Language
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["العربية", "English"])
        self.lang_combo.setCurrentIndex(0 if APP_SETTINGS["language"]=="ar" else 1)
        layout.addWidget(QLabel(tr("Language")))
        layout.addWidget(self.lang_combo)

        # Scan level
        self.level_combo = QComboBox()
        self.level_combo.addItems([tr("Fast"), tr("Accurate"), tr("Deep")])
        idx = {"fast":0, "accurate":1, "deep":2}[APP_SETTINGS["scan_level"]]
        self.level_combo.setCurrentIndex(idx)
        layout.addWidget(QLabel(tr("Scan Level")))
        layout.addWidget(self.level_combo)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(tr("Save"))
        self.cancel_btn = QPushButton(tr("Cancel"))
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_settings(self):
        theme = "dark" if self.theme_combo.currentIndex() == 0 else "light"
        lang = "ar" if self.lang_combo.currentIndex() == 0 else "en"
        level = ["fast", "accurate", "deep"][self.level_combo.currentIndex()]
        return {"theme": theme, "language": lang, "scan_level": level}

# =============== نافذة التقدم أثناء الفحص ===============
class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, total_files):
        super().__init__()
        self.setWindowTitle(tr("AI Cyber Security Analyzer"))
        self.setGeometry(500, 300, 430, 140)
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(tr("Scan Project") + " ...")
        self.bar = QtWidgets.QProgressBar()
        self.bar.setMaximum(total_files)
        self.file_label = QtWidgets.QLabel("")
        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        layout.addWidget(self.file_label)

    def update_progress(self, idx, filename):
        self.bar.setValue(idx)
        self.file_label.setText(f"({idx}) {filename}")
        QtCore.QCoreApplication.processEvents()

# =============== الواجهة الرئيسية ===============
class AnalyzerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("AI Cyber Security Analyzer"))
        self.setGeometry(350, 120, 740, 480)
        self.setMinimumSize(700, 420)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(self.layout)

        # ========== Sidebar (History) ==========
        self.sidebar = QtWidgets.QVBoxLayout()
        self.history_label = QLabel(tr("Scan History"))
        self.history_label.setStyleSheet("font-size:15px; color:#1976d2; font-weight:bold;")
        self.sidebar.addWidget(self.history_label)
        self.history_list = QListWidget()
        self.sidebar.addWidget(self.history_list)
        self.history_list.itemClicked.connect(self.show_history_report)
        self.refresh_history()

        # ========== Main Area ==========
        self.main_area = QtWidgets.QVBoxLayout()
        top_bar = QtWidgets.QHBoxLayout()
        self.title = QLabel(tr("AI Cyber Security Analyzer"))
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setStyleSheet("font-size:21px; color:#1976d2; font-weight:bold; padding:10px;")
        top_bar.addWidget(self.title)
        top_bar.addStretch()
        self.settings_btn = QtWidgets.QPushButton("⚙️")
        self.settings_btn.setFixedSize(36,36)
        self.settings_btn.setStyleSheet("font-size:22px; border-radius:8px; background:#eee;")
        self.settings_btn.clicked.connect(self.open_settings)
        top_bar.addWidget(self.settings_btn)
        self.main_area.addLayout(top_bar)

        self.btn_scan = QtWidgets.QPushButton(tr("Scan Project"))
        self.btn_scan.setStyleSheet("font-size:16px; padding:14px; background:#1976d2; color:#fff; border-radius:10px;")
        self.btn_scan.clicked.connect(self.scan_folder)
        self.main_area.addWidget(self.btn_scan)

        self.stats_label = QLabel(tr("Ready"))
        self.stats_label.setStyleSheet("font-size:13px; color:#666; padding:8px;")
        self.main_area.addWidget(self.stats_label)
        self.main_area.addStretch()

        # ========== Layout ==========
        self.layout.addLayout(self.sidebar, 1)
        self.layout.addLayout(self.main_area, 3)
        self.apply_theme()

    def apply_theme(self):
        if APP_SETTINGS["theme"] == "dark":
            self.setStyleSheet("""
                QWidget { background:#23272f; color:#eee; }
                QPushButton { background:#1976d2; color:#fff; }
                QListWidget { background:#1e2228; color:#ddd; }
                QLineEdit, QLabel { color:#e0e0e0; }
                QDialog { background:#242834; color:#ddd; }
                QProgressBar { background:#222; color:#aaf; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background:#f4f7fb; color:#333; }
                QPushButton { background:#1976d2; color:#fff; }
                QListWidget { background:#fff; color:#222; }
                QLineEdit, QLabel { color:#212121; }
                QDialog { background:#fff; color:#222; }
                QProgressBar { background:#eee; color:#1976d2; }
            """)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            global APP_SETTINGS
            APP_SETTINGS.update(dlg.get_settings())
            save_settings(APP_SETTINGS)
            self.apply_theme()
            QtWidgets.QMessageBox.information(self, tr("Settings"), tr("OK"))
            QtCore.QCoreApplication.processEvents()
            self.refresh_history()

    def refresh_history(self):
        self.history_list.clear()
        history = load_history()
        for entry in reversed(history):
            item = QListWidgetItem(f"{entry['date']}\n{entry['project_name']}")
            item.setData(QtCore.Qt.UserRole, entry)
            self.history_list.addItem(item)

    def show_history_report(self, item):
        entry = item.data(QtCore.Qt.UserRole)
        msg = f"{entry['project_name']}\n{entry['date']}\n\n{entry['summary']}"
        btn = QtWidgets.QMessageBox.information(self, tr("Scan Reports"), msg, QtWidgets.QMessageBox.Ok)
        # Open PDF/JSON option? (يمكنك تطويرها)

    def scan_folder(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, tr("Choose Project Folder"))
            if not folder:
                return

            project_name = os.path.basename(folder.rstrip(os.sep))
            files = list(walk_project_files(folder))
            if not files:
                QMessageBox.information(self, tr("Error"), tr("No Supported Files"))
                return

            dlg = ProgressDialog(len(files))
            dlg.show()
            results = []

            for idx, (fpath, rel_path) in enumerate(files, 1):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
                analysis = analyze_code_file(fpath, code, rel_path)
                results.append({
                    "rel_path": rel_path,
                    "analysis": analysis
                })
                dlg.update_progress(idx, rel_path)

            dlg.close()

            crit, med, low = extract_vuln_stats(results)
            summary = create_summary(project_name, len(files), crit, med, low)

            out_dir = os.path.join(os.getcwd(), "AI_Scan_Reports")
            os.makedirs(out_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_path = os.path.join(out_dir, f"{project_name}_AISCAN_{timestamp}.pdf")
            json_path = os.path.join(out_dir, f"{project_name}_AISCAN_{timestamp}.json")
            generate_pdf_report(results, project_name, summary, pdf_path)
            generate_json_report(results, project_name, summary, json_path)

            add_to_history(project_name, pdf_path, json_path, summary)
            self.refresh_history()
            send_telegram_file(pdf_path)

            self.stats_label.setText(f"✅ {tr('Report Saved To')}:\n📄 PDF: {pdf_path}\n🗂 JSON: {json_path}\n\n{summary}")
            QMessageBox.information(self, tr("Scan Finished"), f"✅ {tr('Report Saved To')}:\n\n📄 {pdf_path}\n🗂 {json_path}\n\n{summary}")

        except Exception as e:
            print("❌ حدث خطأ أثناء الفحص:", e)
            QMessageBox.critical(self, tr("Error"), f"{tr('Scan Error Occurred')}\n{e}")

# =============== تشغيل التطبيق ===============
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = AnalyzerApp()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
