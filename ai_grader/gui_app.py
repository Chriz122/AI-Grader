import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import logging
import threading
import os
import sys
import json
import csv
import re

try:
    from hw2json import hw_to_json
    from pdf2md import pdf_to_markdown
    from grader import HomeworkGrader
    from plagiarism_or_not import plagiarism_check
except ImportError:
    from .hw2json import hw_to_json
    from .pdf2md import pdf_to_markdown
    from .grader import HomeworkGrader
    from .plagiarism_or_not import plagiarism_check

# 獲取基礎路徑的函式
def get_base_path():
    if getattr(sys, "frozen", False):
        # 如果是打包後的執行檔
        return Path(sys.executable).parent
    else:
        # 如果是開發環境
        return Path.cwd()


# 語法高亮類
class SyntaxHighlighter:  
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.setup_tags()
    
    def setup_tags(self):
        # Markdown 樣式 - 
        self.text_widget.tag_config("heading1", foreground="#0055AA", font=("Consolas", 16, "bold"))
        self.text_widget.tag_config("heading2", foreground="#006666", font=("Consolas", 14, "bold"))
        self.text_widget.tag_config("heading3", foreground="#007777", font=("Consolas", 12, "bold"))
        self.text_widget.tag_config("heading4", foreground="#336699", font=("Consolas", 11, "bold"))
        self.text_widget.tag_config("bold", foreground="#8B4500", font=("Consolas", 10, "bold"))
        self.text_widget.tag_config("italic", foreground="#A0522D", font=("Consolas", 10, "italic"))
        self.text_widget.tag_config("code", foreground="#B22222", background="#EEEEEE")
        self.text_widget.tag_config("code_block", foreground="#2F4F4F", background="#EEEEEE")
        self.text_widget.tag_config("list", foreground="#800080")
        self.text_widget.tag_config("link", foreground="#0066CC", underline=True)
        self.text_widget.tag_config("blockquote", foreground="#2E8B57", font=("Consolas", 10, "italic"))
        
        # JSON 樣式 - 
        self.text_widget.tag_config("json_key", foreground="#0066CC")
        self.text_widget.tag_config("json_string", foreground="#B22222")
        self.text_widget.tag_config("json_number", foreground="#008B45")
        self.text_widget.tag_config("json_boolean", foreground="#0000CD")
        self.text_widget.tag_config("json_null", foreground="#0000CD")
        self.text_widget.tag_config("json_bracket", foreground="#FF8C00")
        
        # 一般樣式
        self.text_widget.tag_config("comment", foreground="#228B22", font=("Consolas", 10, "italic"))
    
    def highlight_markdown(self, content):
        self.text_widget.delete(1.0, tk.END)
        
        lines = content.split('\n')
        in_code_block = False
        
        for i, line in enumerate(lines):
            
            # 檢查程式碼區塊
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    pass
                else:
                    # 高亮整個程式碼區塊
                    self.text_widget.insert(tk.END, line + '\n', "code_block")
                    continue
                self.text_widget.insert(tk.END, line + '\n', "code_block")
                continue
            
            if in_code_block:
                self.text_widget.insert(tk.END, line + '\n', "code_block")
                continue
            
            # 標題
            if line.startswith('# '):
                self.text_widget.insert(tk.END, line + '\n', "heading1")
            elif line.startswith('## '):
                self.text_widget.insert(tk.END, line + '\n', "heading2")
            elif line.startswith('### '):
                self.text_widget.insert(tk.END, line + '\n', "heading3")
            elif line.startswith('#### '):
                self.text_widget.insert(tk.END, line + '\n', "heading4")
            elif line.startswith('>'):
                # 引用
                self.text_widget.insert(tk.END, line + '\n', "blockquote")
            elif re.match(r'^[\*\-\+]\s+', line) or re.match(r'^\d+\.\s+', line):
                # 列表
                self.text_widget.insert(tk.END, line + '\n', "list")
            else:
                # 處理行內樣式
                self.highlight_inline_markdown(line)
                self.text_widget.insert(tk.END, '\n')
    
    def highlight_inline_markdown(self, line):
        pos = 0
        
        # 粗體 **text**
        for match in re.finditer(r'\*\*(.+?)\*\*', line):
            # 插入前面的普通文字
            if match.start() > pos:
                self.text_widget.insert(tk.END, line[pos:match.start()])
            # 插入粗體文字
            self.text_widget.insert(tk.END, match.group(0), "bold")
            pos = match.end()
        
        # 斜體 *text* 或 _text_
        for match in re.finditer(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', line[pos:]):
            actual_pos = pos + match.start()
            if actual_pos > pos:
                self.text_widget.insert(tk.END, line[pos:actual_pos])
            self.text_widget.insert(tk.END, match.group(0), "italic")
            pos = pos + match.end()
        
        # 行內程式碼 `code`
        remaining = line[pos:]
        code_pos = 0
        for match in re.finditer(r'`([^`]+?)`', remaining):
            if match.start() > code_pos:
                self.text_widget.insert(tk.END, remaining[code_pos:match.start()])
            self.text_widget.insert(tk.END, match.group(0), "code")
            code_pos = match.end()
        
        # 插入剩餘文字
        if code_pos < len(remaining):
            self.text_widget.insert(tk.END, remaining[code_pos:])
    
    def highlight_json(self, content):
        self.text_widget.delete(1.0, tk.END)
        
        # 嘗試格式化 JSON
        try:
            json_obj = json.loads(content)
            content = json.dumps(json_obj, indent=2, ensure_ascii=False)
        except:
            pass
        
        pos = 0
        for match in re.finditer(
            r'"([^"\\]|\\.)*"(?=\s*:)|'  # JSON key
            r'"([^"\\]|\\.)*"(?!\s*:)|'  # JSON 字串
            r'\b\d+\.?\d*\b|'  # 數字
            r'\btrue\b|\bfalse\b|'  # 布林值
            r'\bnull\b|'  # 空值
            r'[\{\}\[\]]',  # 括號
            content
        ):
            # 插入匹配前的文字
            if match.start() > pos:
                self.text_widget.insert(tk.END, content[pos:match.start()])
            
            matched_text = match.group(0)
            
            # 決定標籤
            if matched_text.startswith('"') and ':' in content[match.end():match.end()+10]:
                tag = "json_key"
            elif matched_text.startswith('"'):
                tag = "json_string"
            elif matched_text in ['true', 'false']:
                tag = "json_boolean"
            elif matched_text == 'null':
                tag = "json_null"
            elif matched_text in ['{', '}', '[', ']']:
                tag = "json_bracket"
            elif matched_text.replace('.', '').replace('-', '').isdigit():
                tag = "json_number"
            else:
                tag = None
            
            self.text_widget.insert(tk.END, matched_text, tag)
            pos = match.end()
        
        # 插入剩餘文字
        if pos < len(content):
            self.text_widget.insert(tk.END, content[pos:])


class AIGraderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Grader")
        # 視窗大小（寬 x 高），之後會以此置中
        self._initial_width = 1000
        self._initial_height = 720
        self.center_window(self._initial_width, self._initial_height)   # 將視窗置中（會設定 geometry）
        self.base_path = get_base_path()
        self.root.iconbitmap(str(self.base_path / "ai_grader" / "resources" / "images" / "icon.ico"))
        
        # 設定主題顏色
        self.setup_theme()
        
        # 初始化變數
        self.hw_paths = []
        self.cls_names = []
        self.api_keys = []
        
        # 配置檔案路徑
        self.config_path = self.base_path / "ai_grader" / "configs" / "config.json"
        
        # 載入配置或使用預設值
        self.load_config()
        self.setup_translations()
        
        # 建立主要介面
        self.create_widgets()
        
        # 載入現有的 API Keys
        self.load_existing_api_keys()
    
    # 載入配置檔案
    def load_config(self):
        default_config = {
            "language": "zh-TW",
            "default_model": "gemini-2.5-flash",
            "default_output_path": str(self.base_path / "RUN"),
            "default_grading_criteria": str(self.base_path / "knowledge" / "grading_criteria.md"),
            "default_output_format": str(self.base_path / "knowledge" / "output_format.md"),
            "default_questions": str(self.base_path / "knowledge" / "questions.md"),
            "default_students_data": str(self.base_path / "knowledge" / "students_data.json"),
            "default_hw_classes": ["上課完成", "回家完成"]
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 合併配置,如果缺少某些鍵則使用預設值
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
            else:
                config = default_config
                # 第一次使用,儲存預設配置
                self.save_config(config)
        except Exception as e:
            logging.error(f"載入配置失敗,使用預設值: {e}")
            config = default_config
        
        # 設定為實例變數
        self.current_language = config.get("language", "zh-TW")
        self.default_model = config.get("default_model", "gemini-2.5-flash")
        self.default_output_path = config.get("default_output_path", str(self.base_path / "RUN"))
        self.default_grading_criteria = config.get("default_grading_criteria", str(self.base_path / "knowledge" / "grading_criteria.md"))
        self.default_output_format = config.get("default_output_format", str(self.base_path / "knowledge" / "output_format.md"))
        self.default_questions = config.get("default_questions", str(self.base_path / "knowledge" / "questions.md"))
        self.default_students_data = config.get("default_students_data", str(self.base_path / "knowledge" / "students_data.json"))
        self.default_hw_classes = config.get("default_hw_classes", ["上課完成", "回家完成"])
    
    # 儲存配置檔案
    def save_config(self, config=None):

        if config is None:
            config = {
                "language": self.current_language,
                "default_model": self.default_model,
                "default_output_path": self.default_output_path,
                "default_grading_criteria": self.default_grading_criteria,
                "default_output_format": self.default_output_format,
                "default_questions": self.default_questions,
                "default_students_data": self.default_students_data,
                "default_hw_classes": self.default_hw_classes
            }
        
        try:
            # 確保配置檔案的目錄存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"儲存配置失敗: {e}")
            return False
    
    # 設定主題顏色
    def setup_theme(self):
        style = ttk.Style()
        
        # 設定分頁標籤樣式 - 藍色主題
        style.configure("TNotebook.Tab", padding=[15, 8])
        style.map("TNotebook.Tab",
                 foreground=[("selected", "#2B2BB0")])

        # 設定執行按鈕樣式
        style.configure("Accent.TButton",
                       foreground="#228B22",
                       font=("Microsoft JhengHei", 10, "bold"),
                       padding=[15, 8])
        style.map("Accent.TButton",
                 foreground=[("active", "#206C21")])  # hover 時的顏色
        # 設定拖動手柄樣式
        style.configure("DragHandle.TLabel",
                       foreground="#222222",
                       padding=(6, 2),
                       font=("Microsoft JhengHei", 10))
        style.configure("DragHandleHover.TLabel",
                       foreground="#222222",
                       padding=(6, 2),
                       font=("Microsoft JhengHei", 10))  # hover 時的顏色
        style.configure("DragHandleActive.TLabel",
                       foreground="#222222",
                       padding=(6, 2),
                       font=("Microsoft JhengHei", 10))
        # 設定查看按鈕樣式
        style.configure("View.TButton",
                       foreground="#222222",
                       font=("Microsoft JhengHei", 10,),
                       padding=[15, 8])
        style.map("View.TButton",
                 foreground=[("active", "#000000")])  # hover 時的顏色

    # 將視窗置中在螢幕上
    def center_window(self, width, height):
        try:
            # 確保 widget metrics 已更新
            # self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = int((screen_width - width) / 2)
            y = int(((screen_height - height) / 2)*0.6)
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            # 若在尚未完全初始時呼叫出錯，fallback 為直接設定 geometry
            self.root.geometry(f"{width}x{height}")
    
    # 設定語言翻譯字典
    def setup_translations(self):
        trans_dir = self.base_path / "ai_grader" / "resources" / "translations"
        # 確保資料夾存在
        try:
            trans_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self.translations = {}

        # 先嘗試從資料夾載入所有 json 翻譯檔
        try:
            for p in trans_dir.glob("*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # 檔名（不含副檔名）作為語言代碼
                        lang = p.stem
                        if isinstance(data, dict):
                            self.translations[lang] = data
                except Exception as e:
                    logging.error(f"載入翻譯檔 {p} 失敗: {e}")
        except Exception as e:
            logging.error(f"搜尋翻譯資料夾失敗: {e}")
    
    # 取得當前語言的翻譯文字
    def t(self, key):
        return self.translations.get(self.current_language, {}).get(key, key)

    def create_widgets(self):
        # 建立 Notebook (分頁)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 建立各個分頁
        self.create_hw2json_tab()
        self.create_pdf2md_tab()
        self.create_grader_tab()
        self.create_plagiarism_tab()
        self.create_settings_tab()
    
    # 作業轉 JSON 功能分頁
    def create_hw2json_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="1. 作業轉JSON")
        
        # 主框架
        main_frame = ttk.Frame(tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        self.hw2json_title = ttk.Label(main_frame, text=self.t("hw2json_title"), font=("Microsoft JhengHei", 17, "bold"))
        self.hw2json_title.pack(pady=(0, 10))
        
        # 作業路徑區域
        self.hw2json_frame = ttk.LabelFrame(main_frame, text=self.t("hw2json_paths"), padding="10")
        self.hw2json_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 滾動區域
        canvas = tk.Canvas(self.hw2json_frame, height=200)
        scrollbar = ttk.Scrollbar(self.hw2json_frame, orient="vertical", command=canvas.yview)
        self.hw_scroll_frame = ttk.Frame(canvas)
        
        self.hw_scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.hw_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 根據 config 建立預設的輸入框
        for class_name in self.default_hw_classes:
            self.add_hw_path_entry(default_name=class_name)
        
        # 按鈕區域
        btn_frame = ttk.Frame(self.hw2json_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.hw2json_add_btn = ttk.Button(btn_frame, text=self.t("hw2json_add_path"), command=self.add_hw_path_entry)
        self.hw2json_add_btn.pack(side=tk.LEFT, padx=5)
        
        # 其他設定
        self.hw2json_other_frame = ttk.LabelFrame(main_frame, text=self.t("hw2json_other_settings"), padding="10")
        self.hw2json_other_frame.pack(fill=tk.X, pady=5)
        
        # 學生名單
        self.hw2json_students_label = ttk.Label(self.hw2json_other_frame, text=self.t("hw2json_students"))
        self.hw2json_students_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.hw2json_students_entry = ttk.Entry(self.hw2json_other_frame, width=60)
        self.hw2json_students_entry.insert(0, self.default_students_data)
        self.hw2json_students_entry.grid(row=0, column=1, padx=5, pady=5)
        self.hw2json_students_browse = ttk.Button(self.hw2json_other_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.hw2json_students_entry, filetypes=[("JSON files", "*.json")]))
        self.hw2json_students_browse.grid(row=0, column=2, pady=5)
        
        # 輸出路徑
        self.hw2json_output_label = ttk.Label(self.hw2json_other_frame, text=self.t("hw2json_output"))
        self.hw2json_output_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.hw2json_output_entry = ttk.Entry(self.hw2json_other_frame, width=60)
        self.hw2json_output_entry.insert(0, self.default_output_path)
        self.hw2json_output_entry.grid(row=1, column=1, padx=5, pady=5)
        self.hw2json_output_browse = ttk.Button(self.hw2json_other_frame, text=self.t("btn_browse"), command=lambda: self.browse_folder(self.hw2json_output_entry))
        self.hw2json_output_browse.grid(row=1, column=2, pady=5)
        
        # 執行按鈕區域
        btn_run_frame = ttk.Frame(main_frame)
        btn_run_frame.pack(pady=10)
        
        self.hw2json_run_btn = ttk.Button(btn_run_frame, text=self.t("hw2json_run"), command=self.run_hw2json, style="Accent.TButton")
        self.hw2json_run_btn.pack(side=tk.LEFT, padx=5)
        
        self.hw2json_view_btn = ttk.Button(btn_run_frame, text=self.t("btn_view_output"), command=self.view_hw2json_output, style="View.TButton")
        self.hw2json_view_btn.pack(side=tk.LEFT, padx=5)
        
        # 輸出訊息
        self.hw2json_output_frame = ttk.LabelFrame(main_frame, text=self.t("hw2json_messages"), padding="10")
        self.hw2json_output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.hw2json_output = scrolledtext.ScrolledText(self.hw2json_output_frame, height=8, wrap=tk.WORD)
        self.hw2json_output.pack(fill=tk.BOTH, expand=True)
    
    # 新增作業路徑輸入組
    def add_hw_path_entry(self, default_name=None):
        frame = ttk.Frame(self.hw_scroll_frame)
        frame.pack(fill=tk.X, pady=5)
        
        # 類別名稱
        label_cls = ttk.Label(frame, text=self.t("hw2json_class_name"))
        label_cls.pack(side=tk.LEFT, padx=5)
        cls_entry = ttk.Entry(frame, width=20)
        # 如果有提供預設名稱就使用,否則使用編號
        if default_name:
            cls_entry.insert(0, default_name)
        else:
            cls_entry.insert(0, f"{self.t('hw2json_class_default')}{len(self.hw_paths)+1}")
        
        # 失焦時自動儲存 hw classes 到 config
        def save_hw_classes_to_config(event=None):
            new_classes = []
            for ce, pe, f, lc, lp, bb, bd in self.hw_paths:
                class_name = ce.get().strip()
                if class_name:
                    new_classes.append(class_name)
            self.default_hw_classes = new_classes
            self.save_config()
        
        cls_entry.bind("<FocusOut>", save_hw_classes_to_config)
        cls_entry.pack(side=tk.LEFT, padx=5)
        
        # 路徑
        label_path = ttk.Label(frame, text=self.t("hw2json_path"))
        label_path.pack(side=tk.LEFT, padx=5)
        path_entry = ttk.Entry(frame, width=50)
        path_entry.pack(side=tk.LEFT, padx=5)
        
        btn_browse = ttk.Button(frame, text=self.t("btn_browse"), command=lambda: self.browse_folder(path_entry))
        btn_browse.pack(side=tk.LEFT, padx=5)
        
        # 刪除按鈕
        def remove_this_entry():
            if len(self.hw_paths) > 1:
                # 找到並移除這個項目
                for i, (ce, pe, f, lc, lp, bb, bd) in enumerate(self.hw_paths):
                    if f == frame:
                        self.hw_paths.pop(i)
                        frame.destroy()
                        # 刪除後也要更新 config
                        save_hw_classes_to_config()
                        break
        
        btn_delete = ttk.Button(frame, text=self.t("btn_delete"), width=3, command=remove_this_entry)
        btn_delete.pack(side=tk.LEFT, padx=5)
        
        # 儲存所有元素的參考以便語言切換時更新
        self.hw_paths.append((cls_entry, path_entry, frame, label_cls, label_path, btn_browse, btn_delete))
    
    # PDF 轉 Markdown 功能分頁
    def create_pdf2md_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="2. PDF轉MD")
        
        main_frame = ttk.Frame(tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        self.pdf2md_title = ttk.Label(main_frame, text=self.t("pdf2md_title"), font=("Microsoft JhengHei", 17, "bold"))
        self.pdf2md_title.pack(pady=(0, 10))
        
        # 設定區域
        self.pdf2md_settings_frame = ttk.LabelFrame(main_frame, text=self.t("pdf2md_settings"), padding="10")
        self.pdf2md_settings_frame.pack(fill=tk.X, pady=5)
        
        # PDF 路徑
        self.pdf2md_pdf_label = ttk.Label(self.pdf2md_settings_frame, text=self.t("pdf2md_pdf_file"))
        self.pdf2md_pdf_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pdf_path_entry = ttk.Entry(self.pdf2md_settings_frame, width=60)
        self.pdf_path_entry.grid(row=0, column=1, padx=5, pady=5)
        self.pdf2md_pdf_browse = ttk.Button(self.pdf2md_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.pdf_path_entry, filetypes=[("PDF files", "*.pdf")]))
        self.pdf2md_pdf_browse.grid(row=0, column=2, pady=5)
        
        # 輸出路徑
        self.pdf2md_output_label = ttk.Label(self.pdf2md_settings_frame, text=self.t("pdf2md_output"))
        self.pdf2md_output_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pdf2md_output_entry = ttk.Entry(self.pdf2md_settings_frame, width=60)
        self.pdf2md_output_entry.insert(0, str(self.base_path / "knowledge"))
        self.pdf2md_output_entry.grid(row=1, column=1, padx=5, pady=5)
        self.pdf2md_output_browse = ttk.Button(self.pdf2md_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_folder(self.pdf2md_output_entry))
        self.pdf2md_output_browse.grid(row=1, column=2, pady=5)
        
        # 模型選擇
        self.pdf2md_model_label = ttk.Label(self.pdf2md_settings_frame, text=self.t("pdf2md_model"))
        self.pdf2md_model_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.pdf2md_model_var = tk.StringVar(value=self.default_model)
        self.pdf2md_model_combo = ttk.Combobox(self.pdf2md_settings_frame, textvariable=self.pdf2md_model_var, width=57)
        self.pdf2md_model_combo["values"] = ("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-2.0-flash-lite")
        self.pdf2md_model_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # 執行按鈕區域
        btn_run_frame = ttk.Frame(main_frame)
        btn_run_frame.pack(pady=10)
        
        self.pdf2md_run_btn = ttk.Button(btn_run_frame, text=self.t("pdf2md_run"), command=self.run_pdf2md, style="Accent.TButton")
        self.pdf2md_run_btn.pack(side=tk.LEFT, padx=5)
        
        self.pdf2md_view_btn = ttk.Button(btn_run_frame, text=self.t("btn_view_output"), command=self.view_pdf2md_output, style="View.TButton")
        self.pdf2md_view_btn.pack(side=tk.LEFT, padx=5)
        
        # 輸出訊息
        self.pdf2md_output_frame = ttk.LabelFrame(main_frame, text=self.t("pdf2md_messages"), padding="10")
        self.pdf2md_output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.pdf2md_output = scrolledtext.ScrolledText(self.pdf2md_output_frame, height=15, wrap=tk.WORD)
        self.pdf2md_output.pack(fill=tk.BOTH, expand=True)
    
    # 評分功能分頁
    def create_grader_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="3. 作業評分")
        
        main_frame = ttk.Frame(tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        self.grader_title = ttk.Label(main_frame, text=self.t("grader_title"), font=("Microsoft JhengHei", 17, "bold"))
        self.grader_title.pack(pady=(0, 10))
        
        # 設定區域
        self.grader_settings_frame = ttk.LabelFrame(main_frame, text=self.t("grader_settings"), padding="10")
        self.grader_settings_frame.pack(fill=tk.X, pady=5)
        
        # 評分標準
        self.grader_criteria_label = ttk.Label(self.grader_settings_frame, text=self.t("grader_criteria"))
        self.grader_criteria_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.grader_criteria_entry = ttk.Entry(self.grader_settings_frame, width=60)
        self.grader_criteria_entry.insert(0, self.default_grading_criteria)
        self.grader_criteria_entry.grid(row=0, column=1, padx=5, pady=5)
        self.grader_criteria_browse = ttk.Button(self.grader_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.grader_criteria_entry, filetypes=[("Markdown files", "*.md")]))
        self.grader_criteria_browse.grid(row=0, column=2, pady=5)
        
        # 輸出格式
        self.grader_format_label = ttk.Label(self.grader_settings_frame, text=self.t("grader_format"))
        self.grader_format_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.grader_format_entry = ttk.Entry(self.grader_settings_frame, width=60)
        self.grader_format_entry.insert(0, self.default_output_format)
        self.grader_format_entry.grid(row=1, column=1, padx=5, pady=5)
        self.grader_format_browse = ttk.Button(self.grader_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.grader_format_entry, filetypes=[("Markdown files", "*.md")]))
        self.grader_format_browse.grid(row=1, column=2, pady=5)

        # 題目
        self.grader_questions_label = ttk.Label(self.grader_settings_frame, text=self.t("grader_questions"))
        self.grader_questions_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.grader_questions_entry = ttk.Entry(self.grader_settings_frame, width=60)
        self.grader_questions_entry.insert(0, self.default_questions)
        self.grader_questions_entry.grid(row=2, column=1, padx=5, pady=5)
        self.grader_questions_browse = ttk.Button(self.grader_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.grader_questions_entry, filetypes=[("Markdown files", "*.md")]))
        self.grader_questions_browse.grid(row=2, column=2, pady=5)
        
        # 作業資料
        self.grader_homework_label = ttk.Label(self.grader_settings_frame, text=self.t("grader_homework"))
        self.grader_homework_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.grader_homework_entry = ttk.Entry(self.grader_settings_frame, width=60)
        self.grader_homework_entry.insert(0, str(self.base_path / "RUN" / "hw_all.json"))
        self.grader_homework_entry.grid(row=3, column=1, padx=5, pady=5)
        self.grader_homework_browse = ttk.Button(self.grader_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.grader_homework_entry, filetypes=[("JSON files", "*.json")]))
        self.grader_homework_browse.grid(row=3, column=2, pady=5)
        
        # 學生名單
        self.grader_students_label = ttk.Label(self.grader_settings_frame, text=self.t("grader_students"))
        self.grader_students_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        self.grader_students_entry = ttk.Entry(self.grader_settings_frame, width=60)
        self.grader_students_entry.insert(0, self.default_students_data)
        self.grader_students_entry.grid(row=4, column=1, padx=5, pady=5)
        self.grader_students_browse = ttk.Button(self.grader_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.grader_students_entry, filetypes=[("JSON files", "*.json")]))
        self.grader_students_browse.grid(row=4, column=2, pady=5)
        
        # 輸出路徑
        self.grader_output_label = ttk.Label(self.grader_settings_frame, text=self.t("grader_output"))
        self.grader_output_label.grid(row=5, column=0, sticky=tk.W, pady=5)
        self.grader_output_entry = ttk.Entry(self.grader_settings_frame, width=60)
        self.grader_output_entry.insert(0, self.default_output_path)
        self.grader_output_entry.grid(row=5, column=1, padx=5, pady=5)
        self.grader_output_browse = ttk.Button(self.grader_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_folder(self.grader_output_entry))
        self.grader_output_browse.grid(row=5, column=2, pady=5)
        
        # 模型選擇
        self.grader_model_label = ttk.Label(self.grader_settings_frame, text=self.t("grader_model"))
        self.grader_model_label.grid(row=6, column=0, sticky=tk.W, pady=5)
        self.grader_model_var = tk.StringVar(value=self.default_model)
        self.grader_model_combo = ttk.Combobox(self.grader_settings_frame, textvariable=self.grader_model_var, width=57)
        self.grader_model_combo["values"] = ("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-2.0-flash-lite")
        self.grader_model_combo.grid(row=6, column=1, padx=5, pady=5)
        
        # 執行按鈕區域
        btn_run_frame = ttk.Frame(main_frame)
        btn_run_frame.pack(pady=10)
        
        self.grader_run_btn = ttk.Button(btn_run_frame, text=self.t("grader_run"), command=self.run_grader, style="Accent.TButton")
        self.grader_run_btn.pack(side=tk.LEFT, padx=5)
        
        self.grader_view_btn = ttk.Button(btn_run_frame, text=self.t("btn_view_output"), command=self.view_grader_output, style="View.TButton")
        self.grader_view_btn.pack(side=tk.LEFT, padx=5)
        
        # 輸出訊息
        self.grader_output_frame = ttk.LabelFrame(main_frame, text=self.t("grader_messages"), padding="10")
        self.grader_output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.grader_output = scrolledtext.ScrolledText(self.grader_output_frame, height=8, wrap=tk.WORD)
        self.grader_output.pack(fill=tk.BOTH, expand=True)
    
    # 抄襲檢測功能分頁
    def create_plagiarism_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="4. 抄襲檢測")
        
        main_frame = ttk.Frame(tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        self.plag_title = ttk.Label(main_frame, text=self.t("plag_title"), font=("Microsoft JhengHei", 17, "bold"))
        self.plag_title.pack(pady=(0, 10))
        
        # 設定區域
        self.plag_settings_frame = ttk.LabelFrame(main_frame, text=self.t("plag_settings"), padding="10")
        self.plag_settings_frame.pack(fill=tk.X, pady=5)
        
        # 作業路徑
        self.plag_homework_label = ttk.Label(self.plag_settings_frame, text=self.t("plag_homework"))
        self.plag_homework_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.plag_homework_entry = ttk.Entry(self.plag_settings_frame, width=60)
        self.plag_homework_entry.insert(0, str(self.base_path / "RUN" / "hw_all.json"))
        self.plag_homework_entry.grid(row=0, column=1, padx=5, pady=5)
        self.plag_homework_browse = ttk.Button(self.plag_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.plag_homework_entry, filetypes=[("JSON files", "*.json")]))
        self.plag_homework_browse.grid(row=0, column=2, pady=5)
        
        # 類別
        self.plag_class_label = ttk.Label(self.plag_settings_frame, text=self.t("plag_class"))
        self.plag_class_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.plag_cls_entry = ttk.Entry(self.plag_settings_frame, width=60)
        self.plag_cls_entry.insert(0, ",".join(self.default_hw_classes))
        
        # 失焦時自動儲存 hw classes 到 config
        def save_plag_classes_to_config(event=None):
            cls_text = self.plag_cls_entry.get().strip()
            if cls_text:
                new_classes = [c.strip() for c in cls_text.split(",") if c.strip()]
                self.default_hw_classes = new_classes
                self.save_config()
        
        self.plag_cls_entry.bind("<FocusOut>", save_plag_classes_to_config)
        self.plag_cls_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # 題目路徑
        self.plag_questions_label = ttk.Label(self.plag_settings_frame, text=self.t("plag_questions"))
        self.plag_questions_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.plag_questions_entry = ttk.Entry(self.plag_settings_frame, width=60)
        self.plag_questions_entry.insert(0, self.default_questions)
        self.plag_questions_entry.grid(row=2, column=1, padx=5, pady=5)
        self.plag_questions_browse = ttk.Button(self.plag_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.plag_questions_entry, filetypes=[("Markdown files", "*.md")]))
        self.plag_questions_browse.grid(row=2, column=2, pady=5)
        
        # 相似度閾值
        self.plag_threshold_label = ttk.Label(self.plag_settings_frame, text=self.t("plag_threshold"))
        self.plag_threshold_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.plag_threshold_var = tk.DoubleVar(value=0.80)
        threshold_frame = ttk.Frame(self.plag_settings_frame)
        threshold_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 用於標記是否正在手動輸入
        self.is_manual_input = False
        
        ttk.Scale(threshold_frame, from_=0.0, to=1.0, variable=self.plag_threshold_var, 
                 orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT)
        
        # 直接輸入框
        self.plag_threshold_entry = ttk.Entry(threshold_frame, width=10)
        self.plag_threshold_entry.insert(0, "0.80")
        self.plag_threshold_entry.pack(side=tk.LEFT, padx=5)
        
        # 當開始輸入時標記為手動輸入模式
        def on_entry_focus_in(event=None):
            self.is_manual_input = True
        
        # 當輸入框失去焦點時自動套用和 Enter 鍵套用
        def auto_apply_threshold(event=None):
            self.is_manual_input = False
            try:
                value = float(self.plag_threshold_entry.get().strip())
                # 限制範圍在 0.0 到 1.0 之間
                value = max(0.0, min(value, 1.0))
                self.plag_threshold_var.set(value)
                self.plag_threshold_entry.delete(0, tk.END)
                self.plag_threshold_entry.insert(0, f"{value:.2f}")
            except ValueError:
                # 如果輸入無效,恢復為當前的閾值
                current_value = self.plag_threshold_var.get()
                self.plag_threshold_entry.delete(0, tk.END)
                self.plag_threshold_entry.insert(0, f"{current_value:.2f}")
        
        # 綁定事件
        self.plag_threshold_entry.bind("<FocusIn>", on_entry_focus_in)
        self.plag_threshold_entry.bind("<FocusOut>", auto_apply_threshold)
        self.plag_threshold_entry.bind("<Return>", auto_apply_threshold)
        
        # 當拉桿改變時更新輸入框
        def update_threshold_display(*args):
            # 如果正在手動輸入,不要更新輸入框
            if self.is_manual_input:
                return
            value = self.plag_threshold_var.get()
            formatted_value = f"{value:.2f}"
            self.plag_threshold_entry.delete(0, tk.END)
            self.plag_threshold_entry.insert(0, formatted_value)
        
        self.plag_threshold_var.trace_add("write", update_threshold_display)
        
        # 學生名單
        self.plag_students_label = ttk.Label(self.plag_settings_frame, text=self.t("plag_students"))
        self.plag_students_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        self.plag_students_entry = ttk.Entry(self.plag_settings_frame, width=60)
        self.plag_students_entry.insert(0, self.default_students_data)
        self.plag_students_entry.grid(row=4, column=1, padx=5, pady=5)
        self.plag_students_browse = ttk.Button(self.plag_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.plag_students_entry, filetypes=[("JSON files", "*.json")]))
        self.plag_students_browse.grid(row=4, column=2, pady=5)
        
        # 輸出路徑
        self.plag_output_label = ttk.Label(self.plag_settings_frame, text=self.t("plag_output"))
        self.plag_output_label.grid(row=5, column=0, sticky=tk.W, pady=5)
        self.plag_output_entry = ttk.Entry(self.plag_settings_frame, width=60)
        self.plag_output_entry.insert(0, self.default_output_path)
        self.plag_output_entry.grid(row=5, column=1, padx=5, pady=5)
        self.plag_output_browse = ttk.Button(self.plag_settings_frame, text=self.t("btn_browse"), command=lambda: self.browse_folder(self.plag_output_entry))
        self.plag_output_browse.grid(row=5, column=2, pady=5)
        
        # 執行按鈕區域
        btn_run_frame = ttk.Frame(main_frame)
        btn_run_frame.pack(pady=10)
        
        self.plag_run_btn = ttk.Button(btn_run_frame, text=self.t("plag_run"), command=self.run_plagiarism, style="Accent.TButton")
        self.plag_run_btn.pack(side=tk.LEFT, padx=5)
        
        self.plag_view_btn = ttk.Button(btn_run_frame, text=self.t("btn_view_output"), command=self.view_plagiarism_output, style="View.TButton")
        self.plag_view_btn.pack(side=tk.LEFT, padx=5)
        
        # 輸出訊息
        self.plag_output_frame = ttk.LabelFrame(main_frame, text=self.t("plag_messages"), padding="10")
        self.plag_output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.plag_output = scrolledtext.ScrolledText(self.plag_output_frame, height=10, wrap=tk.WORD)
        self.plag_output.pack(fill=tk.BOTH, expand=True)
    
    # 系統設定分頁
    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙ 設定")
        
        main_frame = ttk.Frame(tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        self.settings_title_label = ttk.Label(main_frame, text=self.t("settings_title"), font=("Microsoft JhengHei", 17, "bold"))
        self.settings_title_label.pack(pady=(0, 10))
        
        # 語言設定區域
        self.language_frame = ttk.LabelFrame(main_frame, text="語言設定 / Language Settings", padding="10")
        self.language_frame.pack(fill=tk.X, pady=5)
        
        self.settings_language_label = ttk.Label(self.language_frame, text="選擇語言 / Select Language:")
        self.settings_language_label.pack(side=tk.LEFT, padx=5)
        # 根據當前語言設定初始值
        initial_lang = "繁體中文" if self.current_language == "zh-TW" else "English"
        self.language_var = tk.StringVar(value=initial_lang)
        language_combo = ttk.Combobox(self.language_frame, textvariable=self.language_var, width=20, state="readonly")
        language_combo["values"] = ("繁體中文", "English")
        language_combo.pack(side=tk.LEFT, padx=5)
        self.settings_language_apply_btn = ttk.Button(self.language_frame, text="套用 / Apply", command=self.apply_language)
        self.settings_language_apply_btn.pack(side=tk.LEFT, padx=5)
        
        # API Keys 設定
        self.api_frame = ttk.LabelFrame(main_frame, text=self.t("settings_api_keys"), padding="10")
        self.api_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 說明
        self.api_info_label = ttk.Label(self.api_frame, text=self.t("settings_api_info"), wraplength=800)
        self.api_info_label.pack(pady=5)
        
        # API Keys 輸入區域
        keys_canvas = tk.Canvas(self.api_frame, height=150)
        keys_scrollbar = ttk.Scrollbar(self.api_frame, orient="vertical", command=keys_canvas.yview)
        self.api_keys_frame = ttk.Frame(keys_canvas)
        
        self.api_keys_frame.bind(
            "<Configure>",
            lambda e: keys_canvas.configure(scrollregion=keys_canvas.bbox("all"))
        )
        
        keys_canvas.create_window((0, 0), window=self.api_keys_frame, anchor="nw")
        keys_canvas.configure(yscrollcommand=keys_scrollbar.set)
        
        keys_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        keys_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按鈕區域
        api_btn_frame = ttk.Frame(self.api_frame)
        api_btn_frame.pack(fill=tk.X, pady=5)
        
        self.api_add_btn = ttk.Button(api_btn_frame, text=self.t("settings_add_key"), command=self.add_api_key_entry)
        self.api_add_btn.pack(side=tk.LEFT, padx=5)
        self.api_save_btn = ttk.Button(api_btn_frame, text=self.t("settings_save_keys"), command=self.save_api_keys)
        self.api_save_btn.pack(side=tk.LEFT, padx=5)
        
        # 模型設定
        self.model_frame = ttk.LabelFrame(main_frame, text=self.t("settings_default_model"), padding="10")
        self.model_frame.pack(fill=tk.X, pady=5)
        
        self.model_label = ttk.Label(self.model_frame, text=self.t("settings_model_label"))
        self.model_label.pack(side=tk.LEFT, padx=5)
        self.default_model_var = tk.StringVar(value=self.default_model)
        model_combo = ttk.Combobox(self.model_frame, textvariable=self.default_model_var, width=30)
        model_combo["values"] = ("gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-2.0-flash-lite")
        model_combo.pack(side=tk.LEFT, padx=5)
        self.model_apply_btn = ttk.Button(self.model_frame, text=self.t("settings_model_apply"), command=self.apply_default_model)
        self.model_apply_btn.pack(side=tk.LEFT, padx=5)
        
        # 預設路徑設定
        self.path_frame = ttk.LabelFrame(main_frame, text=self.t("settings_paths"), padding="10")
        self.path_frame.pack(fill=tk.X, pady=5)
        
        # 輸出資料夾
        self.settings_output_label = ttk.Label(self.path_frame, text=self.t("settings_output_folder"))
        self.settings_output_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.settings_output_entry = ttk.Entry(self.path_frame, width=50)
        self.settings_output_entry.insert(0, self.default_output_path)
        self.settings_output_entry.grid(row=0, column=1, padx=5, pady=5)
        self.settings_output_browse = ttk.Button(self.path_frame, text=self.t("btn_browse"), command=lambda: self.browse_folder(self.settings_output_entry))
        self.settings_output_browse.grid(row=0, column=2, pady=5)
        
        # 評分標準
        self.settings_criteria_label = ttk.Label(self.path_frame, text=self.t("settings_criteria"))
        self.settings_criteria_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.settings_criteria_entry = ttk.Entry(self.path_frame, width=50)
        self.settings_criteria_entry.insert(0, self.default_grading_criteria)
        self.settings_criteria_entry.grid(row=1, column=1, padx=5, pady=5)
        self.settings_criteria_browse = ttk.Button(self.path_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.settings_criteria_entry, filetypes=[("Markdown files", "*.md")]))
        self.settings_criteria_browse.grid(row=1, column=2, pady=5)
        self.settings_criteria_edit = ttk.Button(self.path_frame, text=self.t("btn_edit"), command=lambda: self.edit_file(self.settings_criteria_entry.get()))
        self.settings_criteria_edit.grid(row=1, column=3, pady=5, padx=5)
        
        # 輸出格式
        self.settings_format_label = ttk.Label(self.path_frame, text=self.t("settings_format"))
        self.settings_format_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        self.settings_format_entry = ttk.Entry(self.path_frame, width=50)
        self.settings_format_entry.insert(0, self.default_output_format)
        self.settings_format_entry.grid(row=2, column=1, padx=5, pady=5)
        self.settings_format_browse = ttk.Button(self.path_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.settings_format_entry, filetypes=[("Markdown files", "*.md")]))
        self.settings_format_browse.grid(row=2, column=2, pady=5)
        self.settings_format_edit = ttk.Button(self.path_frame, text=self.t("btn_edit"), command=lambda: self.edit_file(self.settings_format_entry.get()))
        self.settings_format_edit.grid(row=2, column=3, pady=5, padx=5)
        
        # 題目
        self.settings_questions_label = ttk.Label(self.path_frame, text=self.t("settings_questions"))
        self.settings_questions_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.settings_questions_entry = ttk.Entry(self.path_frame, width=50)
        self.settings_questions_entry.insert(0, self.default_questions)
        self.settings_questions_entry.grid(row=3, column=1, padx=5, pady=5)
        self.settings_questions_browse = ttk.Button(self.path_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.settings_questions_entry, filetypes=[("Markdown files", "*.md")]))
        self.settings_questions_browse.grid(row=3, column=2, pady=5)
        self.settings_questions_edit = ttk.Button(self.path_frame, text=self.t("btn_edit"), command=lambda: self.edit_file(self.settings_questions_entry.get()))
        self.settings_questions_edit.grid(row=3, column=3, pady=5, padx=5)
        
        # 學生名單
        self.settings_students_label = ttk.Label(self.path_frame, text=self.t("settings_students"))
        self.settings_students_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        self.settings_students_entry = ttk.Entry(self.path_frame, width=50)
        self.settings_students_entry.insert(0, self.default_students_data)
        self.settings_students_entry.grid(row=4, column=1, padx=5, pady=5)
        self.settings_students_browse = ttk.Button(self.path_frame, text=self.t("btn_browse"), command=lambda: self.browse_file(self.settings_students_entry, filetypes=[("JSON files", "*.json")]))
        self.settings_students_browse.grid(row=4, column=2, pady=5)
        self.settings_students_edit = ttk.Button(self.path_frame, text=self.t("btn_edit"), command=lambda: self.edit_file(self.settings_students_entry.get()))
        self.settings_students_edit.grid(row=4, column=3, pady=5, padx=5)
        
        # 套用設定按鈕
        self.settings_save_all_btn = ttk.Button(main_frame, text=self.t("settings_save_all"), command=self.save_all_settings, style="Accent.TButton")
        self.settings_save_all_btn.pack(pady=10)
    
    # 載入現有的 API Keys
    def load_existing_api_keys(self):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            # 嘗試載入 GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...
            i = 1
            found_keys = []
            while True:
                key = os.getenv(f"GEMINI_API_KEY_{i}")
                if key:
                    found_keys.append(key)
                    i += 1
                else:
                    break
            
            # 如果沒有找到編號的 KEY，嘗試載入單一的 GEMINI_API_KEY
            if not found_keys:
                single_key = os.getenv("GEMINI_API_KEY")
                if single_key:
                    found_keys.append(single_key)
            
            # 顯示找到的 keys
            if found_keys:
                for key in found_keys:
                    self.add_api_key_entry(key)
                # 儲存到 os.environ 為 GEMINI_API_KEY_1... 或 GEMINI_API_KEY
                for i, key in enumerate(found_keys, 1):
                    os.environ[f"GEMINI_API_KEY_{i}"] = key
                if len(found_keys) == 1:
                    os.environ["GEMINI_API_KEY"] = found_keys[0]
            else:
                # 如果沒有找到，至少顯示一個空的輸入框
                self.add_api_key_entry()
        except:
            # 如果載入失敗，顯示一個空的輸入框
            self.add_api_key_entry()

    # 新增 API Key 輸入框
    def add_api_key_entry(self, key_value=""):
        frame = ttk.Frame(self.api_keys_frame, relief=tk.FLAT, borderwidth=1)
        frame.pack(fill=tk.X, pady=2, padx=2)
        
        # 拖動手柄
        drag_label = ttk.Label(
            frame,
            text="⠿",
            cursor="fleur",
            style="DragHandle.TLabel"
        )
        drag_label.pack(side=tk.LEFT)
        
        # 懸停效果
        def on_enter(e):
            drag_label.config(style="DragHandleHover.TLabel")
        def on_leave(e):
            drag_label.config(style="DragHandle.TLabel")
        drag_label.bind("<Enter>", on_enter)
        drag_label.bind("<Leave>", on_leave)
        
        index = len(self.api_keys) + 1
        label = ttk.Label(frame, text=f"{self.t('settings_api_key')} {index}:")
        label.pack(side=tk.LEFT)

        entry = ttk.Entry(frame, width=55, show="*")
        if key_value:
            entry.insert(0, key_value)
        entry.pack(side=tk.LEFT, padx=5)

        # 失焦時自動儲存 API Keys
        def on_entry_focus_out(event=None):
            try:
                self.save_api_keys()
            except Exception:
                pass

        entry.bind("<FocusOut>", on_entry_focus_out)
        
        # 顯示/隱藏按鈕
        show_var = tk.BooleanVar(value=False)
        def toggle_show():
            if show_var.get():
                entry.config(show="")
            else:
                entry.config(show="*")
        
        show_btn = ttk.Checkbutton(frame, text=self.t("plag_show"), variable=show_var, command=toggle_show)
        show_btn.pack(side=tk.LEFT, padx=5)
        
        # 實作拖動功能
        def on_drag_start(event):
            # 記錄拖動開始的位置和當前項目
            widget = event.widget
            # 找到對應的 frame
            current_frame = widget.master
            self._drag_data = {
                "frame": current_frame,
                "y": event.y_root
            }
            # 改變外觀表示正在拖動
            current_frame.configure(relief=tk.RIDGE, borderwidth=2)
            widget.config(style="DragHandleActive.TLabel")
        
        def on_drag_motion(event):
            if not hasattr(self, '_drag_data'):
                return
            
            # 計算移動距離
            delta_y = event.y_root - self._drag_data["y"]
            drag_frame = self._drag_data["frame"]
            
            # 找到當前項目的索引
            drag_idx = None
            for i, (e, f, lbl, sbtn, delb) in enumerate(self.api_keys):
                if f == drag_frame:
                    drag_idx = i
                    break
            
            if drag_idx is None:
                return
            
            # 根據移動方向決定是否交換位置（降低閾值使拖動更靈敏）
            if delta_y < -15 and drag_idx > 0:  # 向上拖動
                # 與上一個交換
                self.api_keys[drag_idx - 1], self.api_keys[drag_idx] = \
                    self.api_keys[drag_idx], self.api_keys[drag_idx - 1]
                self._drag_data["y"] = event.y_root
                self._repack_api_keys()
            elif delta_y > 15 and drag_idx < len(self.api_keys) - 1:  # 向下拖動
                # 與下一個交換
                self.api_keys[drag_idx + 1], self.api_keys[drag_idx] = \
                    self.api_keys[drag_idx], self.api_keys[drag_idx + 1]
                self._drag_data["y"] = event.y_root
                self._repack_api_keys()
        
        def on_drag_end(event):
            if not hasattr(self, '_drag_data'):
                return
            
            drag_frame = self._drag_data["frame"]
            drag_frame.configure(relief=tk.FLAT, borderwidth=1)
            # 恢復拖動手柄的外觀
            event.widget.config(style="DragHandle.TLabel")
            del self._drag_data
            
            # 更新標籤並自動儲存
            self.update_api_key_labels()
            try:
                self.save_api_keys()
            except Exception:
                pass
        
        # 綁定拖動事件到拖動手柄
        drag_label.bind("<Button-1>", on_drag_start)
        drag_label.bind("<B1-Motion>", on_drag_motion)
        drag_label.bind("<ButtonRelease-1>", on_drag_end)
        
        # 刪除按鈕
        def remove_this_key():
            if len(self.api_keys) > 1:
                # 找到並移除這個項目
                for i, (e, f, lbl, sbtn, dbtn) in enumerate(self.api_keys):
                    if f == frame:
                        self.api_keys.pop(i)
                        frame.destroy()
                        # 更新剩餘的 API Key 標籤編號
                        self.update_api_key_labels()
                        try:
                            self.save_api_keys()
                        except Exception:
                            pass
                        break

        delete_btn = ttk.Button(frame, text=self.t("btn_delete"), width=3, command=remove_this_key)
        delete_btn.pack(side=tk.LEFT, padx=5)

        # 儲存所有元素的參考 (entry, frame, label, show_btn, delete_btn)
        self.api_keys.append((entry, frame, label, show_btn, delete_btn))
    
    # 更新 API Key 標籤編號
    def update_api_key_labels(self):
        for i, (entry, frame, label, show_btn, delete_btn) in enumerate(self.api_keys):
            # 更新標籤文字
            label.config(text=f"{self.t('settings_api_key')} {i+1}:")
            # 更新顯示按鈕文字
            show_btn.config(text=self.t("plag_show"))
            # 更新刪除按鈕文字
            delete_btn.config(text=self.t("btn_delete"))
    
    # 重新排列 API Keys UI
    def _repack_api_keys(self):
        for _, frame, *_ in self.api_keys:
            frame.pack_forget()
            frame.pack(fill=tk.X, pady=3, padx=2)
        self.update_api_key_labels()
    
    # 移除最後一個 API Key 輸入框（保留此方法以支援舊的移除按鈕）
    def remove_api_key_entry(self):
        if len(self.api_keys) > 1:
            entry, frame, *_ = self.api_keys.pop()
            frame.destroy()
            self.update_api_key_labels()
    
    # 儲存 API Keys 到 .env 檔案
    def save_api_keys(self):
        try:
            env_path = self.base_path / ".env"
            
            # 讀取現有的 .env 內容
            existing_lines = []
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    existing_lines = f.readlines()
            
            # 移除舊的 GEMINI_API_KEY 相關行（更嚴格，包含 GEMINI_API_KEY, GEMINI_API_KEY_1 等）
            import re
            pattern = re.compile(r"^\s*GEMINI_API_KEY(?:_\d+)?\s*=", re.IGNORECASE)
            new_lines = [line for line in existing_lines if not pattern.match(line)]
            
            # 新增新的 API Keys
            keys_to_save = []
            for entry, frame, label, show_btn, delete_btn in self.api_keys:
                key = entry.get().strip()
                if key:
                    keys_to_save.append(key)
            
            if not keys_to_save:
                messagebox.showwarning("警告", "請至少輸入一個 API Key")
                return
            
            # 寫入新的 keys
            with open(env_path, "w", encoding="utf-8") as f:
                # 先寫入其他設定
                f.writelines(new_lines)
                # 寫入 API Keys
                if len(keys_to_save) == 1:
                    f.write(f"GEMINI_API_KEY = \"{keys_to_save[0]}\"\n")
                else:
                    for i, key in enumerate(keys_to_save, 1):
                        f.write(f"GEMINI_API_KEY_{i} = \"{key}\"\n")
            # 更新當前執行程序的環境變數, 讓程式可以立即使用新的 keys
            for k in list(os.environ.keys()):
                if k.startswith("GEMINI_API_KEY"):
                    os.environ.pop(k, None)

            if len(keys_to_save) == 1:
                os.environ["GEMINI_API_KEY"] = keys_to_save[0]
            else:
                for i, key in enumerate(keys_to_save, 1):
                    os.environ[f"GEMINI_API_KEY_{i}"] = key

            # messagebox.showinfo("成功", f"已儲存 {len(keys_to_save)} 個 API Key 到 .env 檔案")
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存 API Keys 失敗: {str(e)}")
    
    # 套用預設模型到各功能
    def apply_default_model(self):
        model = self.default_model_var.get()
        self.default_model = model
        self.pdf2md_model_var.set(model)
        self.grader_model_var.set(model)
        
        # 儲存模型設定
        self.save_config()
        
        messagebox.showinfo("成功", f"已將預設模型設為: {model}")
    
    # 儲存所有設定
    def save_all_settings(self):
        # 更新預設值
        self.default_output_path = self.settings_output_entry.get()
        self.default_grading_criteria = self.settings_criteria_entry.get()
        self.default_output_format = self.settings_format_entry.get()
        self.default_questions = self.settings_questions_entry.get()
        self.default_students_data = self.settings_students_entry.get()
        
        # 儲存 API Keys
        self.save_api_keys()
        
        # 儲存配置到 config.json
        self.save_config()
        
        messagebox.showinfo("成功", "已儲存所有設定")
    
    # 瀏覽並選擇檔案
    def browse_file(self, entry_widget, filetypes=None):
        if filetypes is None:
            filetypes = [("All files", "*.*")]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)
    
    # 瀏覽並選擇資料夾
    def browse_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder)
    
    # 記錄訊息到輸出視窗
    def log_message(self, output_widget, message):
        output_widget.insert(tk.END, message + "\n")
        output_widget.see(tk.END)
        output_widget.update()
    
    # 執行作業轉 JSON
    def run_hw2json(self):
        def task():
            try:
                self.hw2json_output.delete(1.0, tk.END)
                self.log_message(self.hw2json_output, self.t("log_hw2json_start"))
                
                # 收集路徑和類別名稱
                paths = []
                cls_names = []
                for cls_entry, path_entry, *_ in self.hw_paths:
                    cls_name = cls_entry.get().strip()
                    path = path_entry.get()
                    if path:
                        cls_names.append(cls_name)
                        paths.append(path)
                
                if not paths:
                    self.log_message(self.hw2json_output, self.t("log_hw2json_error_no_path"))
                    return
                
                students_data_path = self.hw2json_students_entry.get()
                output_path = self.hw2json_output_entry.get()
                
                self.log_message(self.hw2json_output, f"{self.t('log_hw2json_class')} {cls_names}")
                self.log_message(self.hw2json_output, f"{self.t('log_hw2json_path')} {paths}")
                self.log_message(self.hw2json_output, f"{self.t('log_hw2json_students')} {students_data_path}")
                self.log_message(self.hw2json_output, f"{self.t('log_hw2json_output')} {output_path}")
                
                # 執行轉換
                hw_to_json(
                    cls=cls_names,
                    path=paths,
                    students_data_path=Path(students_data_path),
                    output_path=Path(output_path)
                )
                
                self.log_message(self.hw2json_output, self.t("log_hw2json_complete"))
                self.view_hw2json_output()
                messagebox.showinfo(self.t("msg_complete"), self.t("log_hw2json_complete"))
            except Exception as e:
                error_msg = f"{self.t('log_error')} {str(e)}"
                self.log_message(self.hw2json_output, error_msg)
                messagebox.showerror(self.t("msg_error"), error_msg)
        
        # 在新執行緒中執行
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()
    
    # 執行 PDF 轉 Markdown
    def run_pdf2md(self):
        def task():
            try:
                self.pdf2md_output.delete(1.0, tk.END)
                self.log_message(self.pdf2md_output, self.t("log_pdf2md_start"))
                
                pdf_path = self.pdf_path_entry.get()
                output_path = self.pdf2md_output_entry.get()
                model = self.pdf2md_model_var.get()
                
                if not pdf_path:
                    self.log_message(self.pdf2md_output, self.t("log_pdf2md_error_no_file"))
                    return
                
                self.log_message(self.pdf2md_output, f"{self.t('log_pdf2md_file')} {pdf_path}")
                self.log_message(self.pdf2md_output, f"{self.t('log_pdf2md_output')} {output_path}")
                self.log_message(self.pdf2md_output, f"{self.t('log_pdf2md_model')} {model}")
                
                # 執行轉換
                pdf_to_markdown(
                    pdf_path=pdf_path,
                    output_path=Path(output_path),
                    model=model
                )
                
                self.log_message(self.pdf2md_output, self.t("log_pdf2md_complete"))
                self.view_pdf2md_output()
                messagebox.showinfo(self.t("msg_complete"), self.t("log_pdf2md_complete"))
            except Exception as e:
                error_msg = f"{self.t('log_error')} {str(e)}"
                self.log_message(self.pdf2md_output, error_msg)
                messagebox.showerror(self.t("msg_error"), error_msg)
        
        # 在新執行緒中執行
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()
    
    # 執行作業評分
    def run_grader(self):
        def task():
            try:
                self.grader_output.delete(1.0, tk.END)
                self.log_message(self.grader_output, self.t("log_grader_start"))
                
                grading_criteria_path = self.grader_criteria_entry.get()
                output_format_path = self.grader_format_entry.get()
                questions_path = self.grader_questions_entry.get()
                homework_data_path = self.grader_homework_entry.get()
                students_data_path = self.grader_students_entry.get()
                output_path = self.grader_output_entry.get()
                model_name = self.grader_model_var.get()
                
                self.log_message(self.grader_output, f"{self.t('log_grader_criteria')} {grading_criteria_path}")
                self.log_message(self.grader_output, f"{self.t('log_grader_format')} {output_format_path}")
                self.log_message(self.grader_output, f"{self.t('log_grader_questions')} {questions_path}")
                self.log_message(self.grader_output, f"{self.t('log_grader_homework')} {homework_data_path}")
                self.log_message(self.grader_output, f"{self.t('log_grader_model')} {model_name}")
                
                # 執行評分
                HomeworkGrader(
                    grading_criteria_path=grading_criteria_path,
                    output_format_path=output_format_path,
                    questions_path=questions_path,
                    homework_data_path=homework_data_path,
                    students_data_path=Path(students_data_path),
                    output_path=Path(output_path),
                    model_name=model_name
                )
                
                self.log_message(self.grader_output, self.t("log_grader_complete"))
                self.view_grader_output()
                messagebox.showinfo(self.t("msg_complete"), self.t("log_grader_complete"))
            except Exception as e:
                error_msg = f"{self.t('log_error')} {str(e)}"
                self.log_message(self.grader_output, error_msg)
                messagebox.showerror(self.t("msg_error"), error_msg)
        
        # 在新執行緒中執行
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()
    
    # 執行抄襲檢測
    def run_plagiarism(self):
        def task():
            try:
                self.plag_output.delete(1.0, tk.END)
                self.log_message(self.plag_output, self.t("log_plag_start"))
                
                homework_file = self.plag_homework_entry.get()
                cls = self.plag_cls_entry.get().strip()
                questions_path = self.plag_questions_entry.get()
                threshold = self.plag_threshold_var.get()
                students_data_path = self.plag_students_entry.get()
                output_path = self.plag_output_entry.get()
                
                if not homework_file:
                    self.log_message(self.plag_output, self.t("log_plag_error_no_file"))
                    return
                
                # 如果有指定類別，將其轉換為列表；否則傳入 None 讓函數使用預設值
                cls_list = [c.strip() for c in cls.split(",")] if cls else None
                
                self.log_message(self.plag_output, f"{self.t('log_plag_file')} {homework_file}")
                self.log_message(self.plag_output, f"{self.t('log_plag_class')} {cls_list}")
                self.log_message(self.plag_output, f"{self.t('log_plag_threshold')} {threshold}")
                
                # 執行檢測
                plagiarism_check(
                    homework_file=Path(homework_file),
                    cls=cls_list,
                    questions_path=Path(questions_path),
                    threshold=threshold,
                    students_data_path=Path(students_data_path),
                    output_path=Path(output_path)
                )
                
                self.log_message(self.plag_output, self.t("log_plag_complete"))
                self.view_plagiarism_output()
                messagebox.showinfo(self.t("msg_complete"), self.t("log_plag_complete"))
            except Exception as e:
                error_msg = f"{self.t('log_error')} {str(e)}"
                self.log_message(self.plag_output, error_msg)
                messagebox.showerror(self.t("msg_error"), error_msg)
        
        # 在新執行緒中執行
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()
    
    # 查看 hw2json 輸出
    def view_hw2json_output(self):
        output_path = Path(self.hw2json_output_entry.get()) / "hw_all.json"
        if not output_path.exists():
            messagebox.showwarning(self.t("msg_warning"), f"{self.t('file_not_found')}\n{output_path}")
            return
        
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 建立查看視窗
            viewer = tk.Toplevel(self.root)
            viewer.title(f"{self.t('view_output')} - hw_all.json")
            viewer.geometry("900x600")
            
            # 文字區域
            text_frame = ttk.Frame(viewer, padding="10")
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = scrolledtext.ScrolledText(
                text_frame, 
                wrap=tk.WORD,
                font=("Consolas", 10),
                background="#EEEEEE",
                foreground="#2F4F4F",
                insertbackground="#2F4F4F"
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # 應用 JSON 語法高亮
            highlighter = SyntaxHighlighter(text_widget)
            highlighter.highlight_json(content)
            
            text_widget.config(state=tk.DISABLED)  # 唯讀
            
        except Exception as e:
            messagebox.showerror(self.t("msg_error"), f"{self.t('log_error')} {str(e)}")
    
    # 查看 pdf2md 輸出
    def view_pdf2md_output(self):
        output_path = Path(self.pdf2md_output_entry.get()) / "questions.md"
        if not output_path.exists():
            messagebox.showwarning(self.t("msg_warning"), f"{self.t('file_not_found')}\n{output_path}")
            return
        
        # 推測輸出檔名
        pdf_name = Path(output_path).stem
        output_path = Path(self.pdf2md_output_entry.get()) / f"{pdf_name}.md"
        
        if not output_path.exists():
            messagebox.showwarning(self.t("msg_warning"), f"{self.t('file_not_found')}\n{output_path}")
            return
        
        self.edit_markdown_file(output_path)
    
    # 查看 grader 輸出
    def view_grader_output(self):
        output_path = Path(self.grader_output_entry.get()) / "homework_scores.csv"
        if not output_path.exists():
            messagebox.showwarning(self.t("msg_warning"), f"{self.t('file_not_found')}\n{output_path}")
            return
        
        try:
            # 建立查看視窗
            viewer = tk.Toplevel(self.root)
            viewer.title(f"{self.t('view_output')} - homework_scores.csv")
            viewer.geometry("1000x600")
            
            # 讀取 CSV
            with open(output_path, "r", encoding="utf-8-sig") as f:
                csv_reader = csv.reader(f)
                data = list(csv_reader)
            
            # 建立表格
            frame = ttk.Frame(viewer, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # 建立 Treeview
            tree_scroll_y = ttk.Scrollbar(frame, orient="vertical")
            tree_scroll_x = ttk.Scrollbar(frame, orient="horizontal")
            
            tree = ttk.Treeview(frame, 
                               yscrollcommand=tree_scroll_y.set,
                               xscrollcommand=tree_scroll_x.set)
            
            tree_scroll_y.config(command=tree.yview)
            tree_scroll_x.config(command=tree.xview)
            
            tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
            tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
            tree.pack(fill=tk.BOTH, expand=True)
            
            # 設定欄位
            if data:
                tree["columns"] = list(range(len(data[0])))
                tree["show"] = "headings"
                
                # 設定欄位標題
                for i, col in enumerate(data[0]):
                    tree.heading(i, text=col)
                    tree.column(i, width=120)
                
                # 插入資料
                for row in data[1:]:
                    tree.insert("", tk.END, values=row)
            
        except Exception as e:
            messagebox.showerror(self.t("msg_error"), f"{self.t('log_error')} {str(e)}")
    
    # 查看 plagiarism 輸出
    def view_plagiarism_output(self):
        output_path = Path(self.plag_output_entry.get()) / "plagiarism_report.md"
        if not output_path.exists():
            messagebox.showwarning(self.t("msg_warning"), f"{self.t('file_not_found')}\n{output_path}")
            return
        
        self.view_markdown_file(output_path)
    
    # 編輯檔案（通用）
    def edit_file(self, file_path):
        if not file_path:
            messagebox.showwarning(self.t("msg_warning"), self.t("no_file_selected"))
            return
        
        file_path = Path(file_path)
        if not file_path.exists():
            messagebox.showwarning(self.t("msg_warning"), f"{self.t('file_not_found')}\n{file_path}")
            return
        
        # 根據檔案類型選擇編輯器
        if file_path.suffix.lower() == ".md":
            self.edit_markdown_file(file_path)
        elif file_path.suffix.lower() == ".json":
            self.edit_json_file(file_path)
        else:
            messagebox.showwarning(self.t("msg_warning"), f"{self.t('unsupported_file_type')}: {file_path.suffix}")
    
    # 編輯 Markdown 檔案
    def edit_markdown_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 建立編輯視窗
            editor = tk.Toplevel(self.root)
            editor.title(f"{self.t('edit_file')} - {file_path.name}")
            editor.geometry("900x700")
            
            # 文字區域
            text_frame = ttk.Frame(editor, padding="10")
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = scrolledtext.ScrolledText(
                text_frame, 
                wrap=tk.WORD, 
                undo=True,
                font=("Consolas", 10),
                background="#EEEEEE",
                foreground="#2F4F4F",
                insertbackground="#2F4F4F"
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # 應用初始語法高亮
            highlighter = SyntaxHighlighter(text_widget)
            highlighter.highlight_markdown(content)
            
            # 啟用編輯模式
            text_widget.config(state=tk.NORMAL)
            
            # 即時更新語法高亮
            def on_key_release(event=None):
                # 暫時禁用以避免遞迴
                text_widget.unbind('<KeyRelease>')
                
                # 保存游標位置
                cursor_pos = text_widget.index(tk.INSERT)
                
                # 獲取當前內容並重新高亮
                current_content = text_widget.get(1.0, tk.END).rstrip()
                highlighter.highlight_markdown(current_content)
                
                # 恢復游標位置
                try:
                    text_widget.mark_set(tk.INSERT, cursor_pos)
                    text_widget.see(cursor_pos)
                except:
                    pass
                
                # 重新綁定事件
                text_widget.bind('<KeyRelease>', on_key_release)
            
            # 綁定按鍵釋放事件(延遲更新以提高性能)
            text_widget.bind('<KeyRelease>', on_key_release)
            
            # 儲存函數
            def save_file(event=None):
                try:
                    new_content = text_widget.get(1.0, tk.END).rstrip()
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    messagebox.showinfo(self.t("msg_success"), self.t("file_saved"))
                except Exception as e:
                    messagebox.showerror(self.t("msg_error"), f"{self.t('log_error')} {str(e)}")
            
            # 按鈕區域
            btn_frame = ttk.Frame(editor, padding="10")
            btn_frame.pack(fill=tk.X)
            
            save_btn = ttk.Button(btn_frame, text=self.t("btn_save"), command=save_file, style="Accent.TButton")
            save_btn.pack(side=tk.LEFT, padx=5)
            
            # 綁定 Ctrl+S
            editor.bind("<Control-s>", save_file)
            editor.bind("<Control-S>", save_file)
            
        except Exception as e:
            messagebox.showerror(self.t("msg_error"), f"{self.t('log_error')} {str(e)}")
    
    # 編輯 JSON 檔案
    def edit_json_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 建立編輯視窗
            editor = tk.Toplevel(self.root)
            editor.title(f"{self.t('edit_file')} - {file_path.name}")
            editor.geometry("900x700")
            
            # 文字區域
            text_frame = ttk.Frame(editor, padding="10")
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = scrolledtext.ScrolledText(
                text_frame, 
                wrap=tk.WORD, 
                undo=True,
                font=("Consolas", 10),
                background="#EEEEEE",
                foreground="#2F4F4F",
                insertbackground="#2F4F4F"
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # 應用初始語法高亮
            highlighter = SyntaxHighlighter(text_widget)
            highlighter.highlight_json(content)
            
            # 啟用編輯模式
            text_widget.config(state=tk.NORMAL)
            
            # 儲存函數
            def save_file(event=None):
                try:
                    new_content = text_widget.get(1.0, tk.END).rstrip()
                    # 驗證 JSON 格式
                    json.loads(new_content)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    messagebox.showinfo(self.t("msg_success"), self.t("file_saved"))
                except json.JSONDecodeError as e:
                    messagebox.showerror(self.t("msg_error"), f"{self.t('invalid_json')}\n{str(e)}")
                except Exception as e:
                    messagebox.showerror(self.t("msg_error"), f"{self.t('log_error')} {str(e)}")
                        
            # 按鈕區域
            btn_frame = ttk.Frame(editor, padding="10")
            btn_frame.pack(fill=tk.X)
            
            save_btn = ttk.Button(btn_frame, text=self.t("btn_save"), command=save_file, style="Accent.TButton")
            save_btn.pack(side=tk.LEFT, padx=5)
            
            # 綁定 Ctrl+S
            editor.bind("<Control-s>", save_file)
            editor.bind("<Control-S>", save_file)
            
        except Exception as e:
            messagebox.showerror(self.t("msg_error"), f"{self.t('log_error')} {str(e)}")
    
    # 查看 Markdown 檔案（唯讀）
    def view_markdown_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 建立查看視窗
            viewer = tk.Toplevel(self.root)
            viewer.title(f"{self.t('view_output')} - {file_path.name}")
            viewer.geometry("900x700")
            
            # 文字區域
            text_frame = ttk.Frame(viewer, padding="10")
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = scrolledtext.ScrolledText(
                text_frame, 
                wrap=tk.WORD,
                font=("Consolas", 10),
                background="#EEEEEE",
                foreground="#2F4F4F",
                insertbackground="#2F4F4F"
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # 應用 Markdown 語法高亮
            highlighter = SyntaxHighlighter(text_widget)
            highlighter.highlight_markdown(content)
            
            text_widget.config(state=tk.DISABLED)  # 唯讀
            
            # 關閉按鈕
            btn_frame = ttk.Frame(viewer, padding="10")
            btn_frame.pack(fill=tk.X)
            
        except Exception as e:
            messagebox.showerror(self.t("msg_error"), f"{self.t('log_error')} {str(e)}")
    
    # 套用語言設定
    def apply_language(self):
        lang_name = self.language_var.get()
        if lang_name == "繁體中文":
            self.current_language = "zh-TW"
        elif lang_name == "English":
            self.current_language = "en"
        
        # 儲存語言設定
        self.save_config()
        
        # 更新整個介面
        self.update_ui_language()
    
    # 更新介面語言
    def update_ui_language(self):
        # 更新視窗標題
        self.root.title(self.t("title"))
        
        # 更新分頁標籤
        self.notebook.tab(0, text=self.t("tab_hw2json"))
        self.notebook.tab(1, text=self.t("tab_pdf2md"))
        self.notebook.tab(2, text=self.t("tab_grader"))
        self.notebook.tab(3, text=self.t("tab_plagiarism"))
        self.notebook.tab(4, text=self.t("tab_settings"))
        
        # 更新作業轉JSON分頁
        if hasattr(self, 'hw2json_title'):
            self.hw2json_title.config(text=self.t("hw2json_title"))
            self.hw2json_frame.config(text=self.t("hw2json_paths"))
            self.hw2json_add_btn.config(text=self.t("hw2json_add_path"))
            self.hw2json_other_frame.config(text=self.t("hw2json_other_settings"))
            self.hw2json_students_label.config(text=self.t("hw2json_students"))
            self.hw2json_students_browse.config(text=self.t("btn_browse"))
            self.hw2json_output_label.config(text=self.t("hw2json_output"))
            self.hw2json_output_browse.config(text=self.t("btn_browse"))
            self.hw2json_run_btn.config(text=self.t("hw2json_run"))
            self.hw2json_view_btn.config(text=self.t("btn_view_output"))
            self.hw2json_output_frame.config(text=self.t("hw2json_messages"))
            
            # 更新動態新增的作業路徑輸入框
            for cls_entry, path_entry, frame, label_cls, label_path, btn_browse, btn_delete in self.hw_paths:
                label_cls.config(text=self.t("hw2json_class_name"))
                label_path.config(text=self.t("hw2json_path"))
                btn_browse.config(text=self.t("btn_browse"))
                btn_delete.config(text=self.t("btn_delete"))
                label_cls.config(text=self.t("hw2json_class_name"))
                label_path.config(text=self.t("hw2json_path"))
                btn_browse.config(text=self.t("btn_browse"))
                btn_delete.config(text=self.t("btn_delete"))
        
        # 更新PDF轉MD分頁
        if hasattr(self, 'pdf2md_title'):
            self.pdf2md_title.config(text=self.t("pdf2md_title"))
            self.pdf2md_settings_frame.config(text=self.t("pdf2md_settings"))
            self.pdf2md_pdf_label.config(text=self.t("pdf2md_pdf_file"))
            self.pdf2md_pdf_browse.config(text=self.t("btn_browse"))
            self.pdf2md_output_label.config(text=self.t("pdf2md_output"))
            self.pdf2md_output_browse.config(text=self.t("btn_browse"))
            self.pdf2md_model_label.config(text=self.t("pdf2md_model"))
            self.pdf2md_run_btn.config(text=self.t("pdf2md_run"))
            self.pdf2md_view_btn.config(text=self.t("btn_view_output"))
            self.pdf2md_output_frame.config(text=self.t("pdf2md_messages"))
        
        # 更新評分分頁
        if hasattr(self, 'grader_title'):
            self.grader_title.config(text=self.t("grader_title"))
            self.grader_settings_frame.config(text=self.t("grader_settings"))
            self.grader_criteria_label.config(text=self.t("grader_criteria"))
            self.grader_criteria_browse.config(text=self.t("btn_browse"))
            self.grader_format_label.config(text=self.t("grader_format"))
            self.grader_format_browse.config(text=self.t("btn_browse"))
            self.grader_questions_label.config(text=self.t("grader_questions"))
            self.grader_questions_browse.config(text=self.t("btn_browse"))
            self.grader_homework_label.config(text=self.t("grader_homework"))
            self.grader_homework_browse.config(text=self.t("btn_browse"))
            self.grader_students_label.config(text=self.t("grader_students"))
            self.grader_students_browse.config(text=self.t("btn_browse"))
            self.grader_output_label.config(text=self.t("grader_output"))
            self.grader_output_browse.config(text=self.t("btn_browse"))
            self.grader_model_label.config(text=self.t("grader_model"))
            self.grader_run_btn.config(text=self.t("grader_run"))
            self.grader_view_btn.config(text=self.t("btn_view_output"))
            self.grader_output_frame.config(text=self.t("grader_messages"))
        
        # 更新抄襲檢測分頁
        if hasattr(self, 'plag_title'):
            self.plag_title.config(text=self.t("plag_title"))
            self.plag_settings_frame.config(text=self.t("plag_settings"))
            self.plag_homework_label.config(text=self.t("plag_homework"))
            self.plag_homework_browse.config(text=self.t("btn_browse"))
            self.plag_class_label.config(text=self.t("plag_class"))
            self.plag_questions_label.config(text=self.t("plag_questions"))
            self.plag_questions_browse.config(text=self.t("btn_browse"))
            self.plag_threshold_label.config(text=self.t("plag_threshold"))
            self.plag_students_label.config(text=self.t("plag_students"))
            self.plag_students_browse.config(text=self.t("btn_browse"))
            self.plag_output_label.config(text=self.t("plag_output"))
            self.plag_output_browse.config(text=self.t("btn_browse"))
            self.plag_run_btn.config(text=self.t("plag_run"))
            self.plag_view_btn.config(text=self.t("btn_view_output"))
            self.plag_output_frame.config(text=self.t("plag_messages"))
        
        # 更新設定頁面的文字（如果已建立）
        if hasattr(self, 'settings_title_label'):
            self.settings_title_label.config(text=self.t("settings_title"))
            # 語言框架標籤在切換時保持雙語
            if self.current_language == "zh-TW":
                self.language_frame.config(text="語言設定 / Language Settings")
                self.settings_language_label.config(text="選擇語言 / Select Language:")
                self.settings_language_apply_btn.config(text="套用 / Apply")
            else:
                self.language_frame.config(text="Language Settings / 語言設定")
                self.settings_language_label.config(text="Select Language / 選擇語言:")
                self.settings_language_apply_btn.config(text="Apply / 套用")
            
            self.api_frame.config(text=self.t("settings_api_keys"))
            self.api_info_label.config(text=self.t("settings_api_info"))
            self.api_add_btn.config(text=self.t("settings_add_key"))
            self.api_save_btn.config(text=self.t("settings_save_keys"))
            
            # 更新動態新增的 API Key 輸入框
            for i, (entry, frame, label, show_btn, delete_btn) in enumerate(self.api_keys):
                label.config(text=f"{self.t('settings_api_key')} {i+1}:")
                show_btn.config(text=self.t("plag_show"))
                delete_btn.config(text=self.t("btn_delete"))
            
            self.model_frame.config(text=self.t("settings_default_model"))
            self.model_label.config(text=self.t("settings_model_label"))
            self.model_apply_btn.config(text=self.t("settings_model_apply"))
            self.path_frame.config(text=self.t("settings_paths"))
            self.settings_output_label.config(text=self.t("settings_output_folder"))
            self.settings_criteria_label.config(text=self.t("settings_criteria"))
            self.settings_format_label.config(text=self.t("settings_format"))
            self.settings_questions_label.config(text=self.t("settings_questions"))
            self.settings_students_label.config(text=self.t("settings_students"))
            self.settings_save_all_btn.config(text=self.t("settings_save_all"))
            # 更新所有瀏覽按鈕
            self.settings_output_browse.config(text=self.t("btn_browse"))
            self.settings_criteria_browse.config(text=self.t("btn_browse"))
            self.settings_format_browse.config(text=self.t("btn_browse"))
            self.settings_questions_browse.config(text=self.t("btn_browse"))
            self.settings_students_browse.config(text=self.t("btn_browse"))
            # 更新所有編輯按鈕
            self.settings_criteria_edit.config(text=self.t("btn_edit"))
            self.settings_format_edit.config(text=self.t("btn_edit"))
            self.settings_questions_edit.config(text=self.t("btn_edit"))
            self.settings_students_edit.config(text=self.t("btn_edit"))

def app():
    root = tk.Tk()
    AIGraderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    app()
