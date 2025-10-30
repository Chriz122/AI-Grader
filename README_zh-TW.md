# AI Grader - 作業批改系統

繁體中文 | [English](README.md)

這是一個使用 LLM (Large Language Model) 自動批改 Python 程式作業的系統。

## 功能特色

- 🤖 自動批改學生 Python 作業
- 📝 PDF 題目一鍵轉 Markdown（支援 LaTeX 公式）
- 📊 產生完整評分結果與統計
- 📈 匯出 Excel 可讀的成績表
- 🔄 自動切換 API 金鑰以應對配額限制

## 專案結構

```
AI-Grader/
├── ai_grader/
│   ├── api_key_manager.py        # Gemini API 金鑰管理
│   ├── grader.py                 # 主程式（呼叫 Gemini 進行批改）
│   ├── gui_app.py                # GUI 應用程式（批改介面）
│   ├── pdf2md.py                 # 題目 PDF -> Markdown 工具
│   ├── plagiarism_or_not.py      # 抄襲檢查工具
│   └── hw2json.py                # 學生作業 -> JSON 彙整工具
├── data/                         # 學生原始作業資料夾、作業題目
├── knowledge/                    # 題目、評分標準、輸出格式
│   ├── grading_criteria.md       # 評分標準（可自訂）
│   ├── output_format.md          # LLM 回覆的 JSON 欄位格式（可自訂）
│   ├── questions.md              # 題目（可由 pdf2md 產生）
│   └── students_data.json        # 學生資料（ID、姓名）
├── RUN/                          # 執行輸出
│   ├── grading_results.json      # 批改結果（JSON）
│   ├── homework_scores.csv       # 成績表（Excel 匯入格式）
│   ├── hw_all.json               # 學生作業彙整（由 hw2json 產生）
│   └── plagiarism_report.md      # 抄襲檢查報告（Markdown）
├── test/
│    └── test_create_prompt.py    # 驗證 Prompt 內容（不需 API 呼叫）
└── run_app.bat 				  # 執行 GUI 應用程式的腳本
```

## 安裝與設定

1) 安裝依賴套件（Windows PowerShell）

```powershell
cd c:\Users\USER\Desktop\AI-Grader
pip install -r requirements.txt
```

2) 設定 Gemini API Key（支援多個金鑰託管）

本專案除了支援單一環境變數 `GEMINI_API_KEY` 外，也支援在 `.env` 中託管多個金鑰（例如當一組金鑰達配額上限時會自動輪替）。

程式會優先尋找編號格式的金鑰 `GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...`，若找不到則回退到單一 `GEMINI_API_KEY`。

建議做法：在專案根目錄將 `.env.example` 另存或改名為 `.env`，並填入你的金鑰：

範例（多金鑰）：

```
GEMINI_API_KEY_1 = "your_first_key_here"
GEMINI_API_KEY_2 = "your_second_key_here"
GEMINI_API_KEY_3 = "your_third_key_here"
```

或只使用單一金鑰：

```
GEMINI_API_KEY = "your_key_here"
```

程式行為摘要：
- 程式將載入所有 `GEMINI_API_KEY_<n>`（從 1 開始遞增）並記錄載入數量；若沒有發現編號金鑰，會嘗試讀取 `GEMINI_API_KEY`。
- 當呼叫 API 時若遇到 429 / RESOURCE_EXHAUSTED（配額耗盡）錯誤，`ai_grader` 會自動切換到下一組已註冊的金鑰並重試。
- 若所有已註冊金鑰都嘗試過且配額皆用盡，將會回報失敗並停止重試。

注意事項：
- 金鑰的載入順序依環境變數編號（1,2,3...）決定，請依使用優先順序填寫。
- 若僅提供 `GEMINI_API_KEY`，系統仍可正常運作，但不具備自動輪替功能（除非手動新增多個 `GEMINI_API_KEY_<n>`）。
- 金鑰與配額管理請依供應商政策與帳號限制操作。

- 申請金鑰：https://aistudio.google.com/api-keys

3) 選擇 Gemini 模型

| Model | Category | RPM | TPM | RPD |
|-------|----------|-----|-----|-----|
| gemini-2.0-flash-exp | Text-out models | 0 / 10 | 0 / 250K | 0 / 50 |
| gemini-2.0-flash-lite | Text-out models | 0 / 30 | 0 / 1M | 0 / 200 |
| gemini-2.0-flash-preview-image-generation | Multi-modal generative models | 0 / 10 | 0 / 200K | 0 / 100 |
| gemini-2.0-flash | Text-out models | 0 / 15 | 0 / 1M | 0 / 200 |
| gemini-2.5-flash-lite | Text-out models | 0 / 15 | 0 / 250K | 0 / 1K |
| gemini-2.5-flash-tts | Multi-modal generative models | 0 / 3 | 0 / 10K | 0 / 15 |
| gemini-2.5-flash | Text-out models | 0 / 10 | 0 / 250K | 0 / 250 |
| gemini-2.5-pro | Text-out models | 0 / 2 | 0 / 125K | 0 / 50 |

## 快速啟動

專案根目錄提供了 `run_app.bat` 批次檔案，Windows 使用者可快速啟動 GUI 批改介面：

**方法一：直接執行**
- 雙擊專案根目錄的 `run_app.bat` 檔案即可啟動 GUI 批改介面。

**方法二：命令列執行**
```powershell
cd c:\Users\USER\Desktop\AI-Grader
.\run_app.bat
```

此批次檔會自動：
- 啟用 Python 虛擬環境
- 執行 GUI 應用程式（`gui_app.py`）
- 若環境未正確設定會顯示錯誤訊息

## 自訂與調整

- 修改 `knowledge/grading_criteria.md` 可微調評分細節與配分。
- 修改 `knowledge/output_format.md` 可定義 LLM 回傳的 JSON 欄位。
- `ai_grader/grader.py` 、`ai_grader/plagiarism_or_not.py` 的 `MODEL_NAME` 可調整為其他 Gemini 模型（預設 `gemini-2.5-flash`）。
- `knowledge/students_data.json` 學生名單可依課程情境調整。

## 測試（不需金鑰）

`test/test_create_prompt.py` 會以現有資料產出一份完整的 LLM 提示內容到 `test/test_output.md`，不會連網：

```powershell
python test\test_create_prompt.py
```

## 疑難排解

- 執行 `grader.py` 時提示未設定金鑰：請確認專案根目錄 `.env` 已填入 `GEMINI_API_KEY`。
- 連線錯誤：請確認網路可用，Gemini API 需要對外連線。
- 找不到學生資料：請確認 `knowledge/students_data.json` 是否存在。
- 找不到作業 JSON：請先執行 `hw2json.py` 產生 `RUN/hw_all.json`。
- 找不到題目 Markdown：請先執行 `pdf2md.py` 產生 `knowledge/questions.md`。

## 注意事項

- 批改時間依學生數量與模型延遲而定，建議先以少量資料試跑。
- LLM 會產生成本（若使用計費方案），請自行評估用量與金額。

## 授權與貢獻

歡迎提交 Issue 或 PR 改善說明與流程。