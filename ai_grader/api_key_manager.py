import os
from google import genai
from dotenv import load_dotenv

MODEL_NAME = "gemini-2.0-flash"


# 管理多個 Gemini API KEY，支援自動輪換
class GeminiAPIKeyManager:
    def __init__(self):
        load_dotenv()
        self.api_keys = []
        self.current_index = 0
        self.client = None
        self._load_api_keys()
        
    # 從環境變數載入所有 API KEY
    def _load_api_keys(self):
        # 嘗試載入 GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... 或 GEMINI_API_KEY
        i = 1
        while True:
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key:
                self.api_keys.append(key)
                i += 1
            else:
                break
        
        # 如果沒有找到編號的 KEY，嘗試載入單一的 GEMINI_API_KEY
        if not self.api_keys:
            single_key = os.getenv('GEMINI_API_KEY')
            if single_key:
                self.api_keys.append(single_key)
        
        if not self.api_keys:
            raise ValueError("未找到任何 Gemini API KEY。請在 .env 檔案中設定 GEMINI_API_KEY 或 GEMINI_API_KEY_1, GEMINI_API_KEY_2...")
        
        print(f"已載入 {len(self.api_keys)} 個 API KEY")
    
    # 取得當前的 API KEY
    def get_current_key(self):
        return self.api_keys[self.current_index]
    
    # 切換到下一個 API KEY
    def rotate_to_next_key(self):
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        print(f"切換到 API_KEY #{self.current_index + 1}")
        return
    
    # 切換到下一個 API KEY，如果沒有可用的 KEY 則返回 False
    def switch_to_next_key(self):
        self.rotate_to_next_key()

        # 檢查是否已經轉回第一個 KEY，表示所有 KEY 都嘗試過了
        if self.current_index == 0 and len(self.api_keys) > 1:
            print("所有 API_KEY 都已嘗試過")
            return False
        return True
    
    # 配置 genai 使用當前的 API KEY
    def configure_genai(self):
        self.client = genai.Client(api_key=self.get_current_key())
        return self.client

# 使用多個 API KEY 進行生成，遇到配額錯誤時自動切換
def generate(prompt, model_name=MODEL_NAME):
    key_manager = GeminiAPIKeyManager()
    
    old_prompt = None  # 追蹤相同 prompt 的重試輪次（先輪替 KEY，一輪全試過才 sleep）
    try_times = 0  # 計數：在同一份 prompt 下，已輪替過幾次 KEY

    while True:
        try:
            # 配置當前的 API KEY 並取得 client
            client = key_manager.configure_genai()

            # 若 prompt 改變就重置輪次統計
            if old_prompt != prompt:
                old_prompt = prompt
                try_times = 0

            # 使用 client.models.generate_content 進行生成
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "temperature": 0.3,
                    "response_mime_type": "application/json"
                }
            )
            return response.text

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
                if (prompt == old_prompt) and (try_times == key_manager.current_index + 1):
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
                if (prompt == old_prompt) and (try_times == key_manager.current_index + 1):
                    print(f"網路錯誤，正在重試...({str(e)})")
                    from time import sleep
                    sleep(30)
                    try_times = 0
                else:
                    key_manager.rotate_to_next_key()
                    try_times += 1
                continue

            elif "Invalid \\escape" in str(e) or "Expecting" in str(e):
                if (prompt == old_prompt) and (try_times == key_manager.current_index + 1):
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
    prompt = "1 + 1 = ?"
    print(f"Q: {prompt}")
    result = generate(prompt, model_name=MODEL_NAME)
    
    if result:
        print(f"Ans: {result}")
    else:
        print("生成失敗")
