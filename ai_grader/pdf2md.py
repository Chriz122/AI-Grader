from pathlib import Path
try:
    from api_key_manager import GeminiAPIKeyManager
except ImportError:
    from .api_key_manager import GeminiAPIKeyManager

MODEL_NAME = "gemini-2.5-flash"  # Google Gemini 模型
OUTPUT_PATH = Path("knowledge")

# 將 PDF 轉為 Markdown
def pdf_to_markdown(pdf_path, output_path=OUTPUT_PATH, model=MODEL_NAME):
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"找不到 PDF 檔案：{pdf_path}")

    # 使用 GeminiAPIKeyManager 進行自動重試與 key 切換
    key_manager = GeminiAPIKeyManager()

    # 要求轉為 Markdown（以 LaTeX 呈現數學公式）
    system_prompt = (
        "你是資工系助教，負責將 PDF 內容轉寫為乾淨、結構化的 Markdown。"
        "請遵守以下規則：\n"
        "- 以 Markdown 輸出全文，保留標題階層與段落。\n"
        "- 所有數學公式請使用 LaTeX（行內公式使用 $...$，區塊公式使用 $$...$$）。\n"
        "- 表格請以 Markdown 表格格式呈現。\n"
        "- 程式碼（若有）請使用對應語言的程式碼區塊。\n"
        "- 若有圖片/圖表，不需嵌入圖片檔。\n"
        "- 移除與作業無關的頁尾頁碼、浮水印或多餘空白。\n"
    )
    user_prompt = (
        "請將這份 PDF 的內容完整轉為 Markdown。\n"
        "重點：所有數學內容以 LaTeX 呈現，並確保段落與標題層級正確。"
    )
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    old_full_prompt = None  # 追蹤相同 prompt 的重試輪次（先輪替 KEY，一輪全試過才 sleep）
    try_times = 0  # 計數：在同一份 prompt 下，已輪替過幾次 KEY
    
    while True:
        try:
            # 配置當前的 API KEY 並取得 client
            client = key_manager.configure_genai()

            # 若 prompt 改變就重置輪次統計
            if old_full_prompt != full_prompt:
                old_full_prompt = full_prompt
                try_times = 0

            # 上傳 PDF
            uploaded = client.files.upload(file=pdf_path)
            uploaded_name = getattr(uploaded, "name", None)
            if not uploaded_name:
                raise RuntimeError("檔案上傳失敗，未取得檔名/識別。")

            # 使用 models.generate_content，直接傳入上傳檔與文字提示
            response = client.models.generate_content(
                model=model,
                contents=[uploaded, full_prompt],
                config={
                    "temperature": 0.3,
                    "response_mime_type": "text/plain",
                },
            )

            # 保證目錄存在
            output_path.mkdir(exist_ok=True)
            with open(output_path / "questions.md", "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"已輸出 Markdown 至: {output_path / 'questions.md'}")
            return

        except Exception as e:
            # 檢查是否為 429 配額錯誤
            if "429" in str(e) and "RESOURCE_EXHAUSTED" in str(e):
                print(f"API KEY #{key_manager.current_index + 1} 配額已用盡")
                
                # 嘗試切換到下一個 KEY
                if not key_manager.switch_to_next_key():
                    print("所有 API KEY 的配額都已用盡")
                    return None
                
                continue  # 切換 KEY 後重試生成
            
            # 改成先換成其他 KEY，如果同一組 prompt 試過一輪都沒成功，再執行 sleep(30)
            elif "503 UNAVAILABLE" in str(e):
                # 先輪替 KEY；若同一組 prompt 已嘗試到目前 KEY 的序號（表示轉滿一輪），才 sleep
                if (full_prompt == old_full_prompt) and (try_times == key_manager.current_index + 1):
                    print(f"模型過載，正在重試...({str(e)})")
                    from time import sleep
                    sleep(30)
                    # 新一輪開始
                    try_times = 0
                else:
                    key_manager.rotate_to_next_key()
                    try_times += 1
                continue

            elif "getaddrinfo failed" in str(e):
                if (full_prompt == old_full_prompt) and (try_times == key_manager.current_index + 1):
                    print(f"網路錯誤，正在重試...({str(e)})")
                    from time import sleep
                    sleep(30)
                    try_times = 0
                else:
                    key_manager.rotate_to_next_key()
                    try_times += 1
                continue

            elif "Invalid \\escape" in str(e) or "Expecting" in str(e):
                if (full_prompt == old_full_prompt) and (try_times == key_manager.current_index + 1):
                    print(f"回應格式錯誤，正在重試...({str(e)})")
                    from time import sleep
                    sleep(30)
                    try_times = 0
                else:
                    key_manager.rotate_to_next_key()
                    try_times += 1
                continue
                
            else:
                # 其他錯誤
                print(f"錯誤: {str(e)}")
                return None

if __name__ == "__main__":
    pdf_to_markdown(pdf_path=r"data/Homework.pdf")
