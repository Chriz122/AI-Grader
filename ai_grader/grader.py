import json
import csv
import re
from pathlib import Path
try:
    from api_key_manager import GeminiAPIKeyManager
except ImportError:
    from .api_key_manager import GeminiAPIKeyManager

MODEL_NAME = "gemini-2.5-flash"  # Google Gemini 模型
OUTPUT_PATH = Path("RUN")
STUDENTS_DATA_PATH = Path("knowledge") / "students_data.json"

# 作業批改系統主類別
class HomeworkGrader:
    def __init__(self, grading_criteria_path, output_format_path, questions_path, homework_data_path, 
                 students_data_path=STUDENTS_DATA_PATH, output_path=OUTPUT_PATH, model_name=MODEL_NAME):
        self.key_manager = GeminiAPIKeyManager()
        self.questions_path = Path(questions_path)
        self.grading_criteria_path = Path(grading_criteria_path)
        self.output_format_path = Path(output_format_path)
        self.homework_data_path = Path(homework_data_path)
        self.students_data_path = Path(students_data_path)
        self.output_path = Path(output_path)
        self.model_name = model_name
        self.old_full_prompt = None  # 追蹤相同 prompt 的重試輪次（先輪替 KEY，一輪全試過才 sleep）
        self.try_times = 0           # 計數：在同一份 prompt 下，已輪替過幾次 KEY
        self.load_resources()
        self.run()
    
    # 載入題目、評分標準與學生作業
    def load_resources(self):
        # 載入題目
        try:
            with open(self.questions_path, "r", encoding="utf-8") as f:
                self.questions = f.read()
        except Exception as e:
            raise RuntimeError(f"載入題目時發生錯誤: {e}")

        # 載入評分標準
        try:
            with open(self.grading_criteria_path, "r", encoding="utf-8") as f:
                self.grading_criteria = f.read()
        except Exception as e:
            raise RuntimeError(f"載入評分標準時發生錯誤: {e}")

        # 載入輸出格式
        try:
            with open(self.output_format_path, "r", encoding="utf-8") as f:
                self.output_format = f.read()
        except Exception as e:
            raise RuntimeError(f"載入輸出格式時發生錯誤: {e}")

        # 載入學生作業
        try:
            with open(self.homework_data_path, "r", encoding="utf-8") as f:
                self.homework_data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"載入學生作業時發生錯誤: {e}")

        # 載入學生名單
        try:
            with open(self.students_data_path, "r", encoding="utf-8") as f:
                self.students_data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"載入學生名單時發生錯誤: {e}")

    # 建立批改提示
    def create_grading_prompt(self, student_id, student_name, homework):
        prompt = f"""你是一位專業的程式設計課程助教，負責批改學生的 Python 程式作業。

## 題目內容
{self.questions}

## 評分標準
{self.grading_criteria}

## 學生資訊
- 學號：{student_id}
- 姓名：{student_name}

## 學生繳交作業內容
"""
        
        if isinstance(homework, dict) and "content" in homework:
            if homework["content"] == "未繳交":
                prompt += "\n**此學生未繳交作業**\n"
            else:
                prompt += homework["content"]
        elif isinstance(homework, dict):
            for filename, code in homework.items():
                prompt += f"\n### 檔案：{filename}\n```python\n{code}\n```\n"
        else:
            prompt += str(homework)

        # 輸出格式
        prompt += f"\n\n## 輸出格式\n{self.output_format}\n\n請仔細批改並提供建設性的回饋意見。"
             
        return prompt
    
    # 批改單個學生作業
    def grade_homework(self, student_id, student_name, homework):
        prompt = self.create_grading_prompt(student_id, student_name, homework)
        
        full_prompt = """你是一位專業且富有教學經驗的程式設計助教。你會仔細檢查學生程式碼,並提供具建設性的回饋,但僅檢查學生是否有語法錯誤或邏輯(公式)錯誤。

請以 JSON 格式回覆,不要包含任何其他文字。

""" + prompt
        
        while True:
            try:
                # 配置當前的 API KEY 並取得 client
                client = self.key_manager.configure_genai()

                # 若 prompt 改變就重置輪次統計
                if self.old_full_prompt != full_prompt:
                    self.old_full_prompt = full_prompt
                    self.try_times = 0

                print(f"正在批改: {student_id} {student_name} (使用 API KEY #{self.key_manager.current_index + 1})")
                
                # 使用 client.models.generate_content 進行生成
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config={
                        "temperature": 0.3,
                        "response_mime_type": "application/json"
                    }
                )
                
                # 解析 JSON 回應
                result = json.loads(response.text)
                return result

            except Exception as e:
                # 檢查是否為 429 配額錯誤
                if "429" in str(e) and "RESOURCE_EXHAUSTED" in str(e):
                    print(f"API KEY #{self.key_manager.current_index + 1} 配額已用盡")
                    
                    # 嘗試切換到下一個 KEY
                    if not self.key_manager.switch_to_next_key():
                        print("所有 API KEY 的配額都已用盡")
                        return None
                    
                    continue  # 切換 KEY 後重試生成
                
                # 改成先換成其他 KEY，如果同一組 prompt 試過一輪都沒成功，再執行 sleep(30)
                elif "503 UNAVAILABLE" in str(e):
                    # 先輪替 KEY；若同一組 prompt 已嘗試到目前 KEY 的序號（表示轉滿一輪），才 sleep
                    if (full_prompt == self.old_full_prompt) and (self.try_times == self.key_manager.current_index + 1):
                        print(f"模型過載，正在重試...({str(e)})")
                        from time import sleep
                        sleep(30)
                        # 新一輪開始
                        self.try_times = 0
                    else:
                        self.key_manager.rotate_to_next_key()
                        self.try_times += 1
                    continue

                elif "getaddrinfo failed" in str(e):
                    if (full_prompt == self.old_full_prompt) and (self.try_times == self.key_manager.current_index + 1):
                        print(f"網路錯誤，正在重試...({str(e)})")
                        from time import sleep
                        sleep(30)
                        self.try_times = 0
                    else:
                        self.key_manager.rotate_to_next_key()
                        self.try_times += 1
                    continue

                elif "Invalid \\escape" in str(e) or "Expecting" in str(e):
                    if (full_prompt == self.old_full_prompt) and (self.try_times == self.key_manager.current_index + 1):
                        print(f"回應格式錯誤，正在重試...({str(e)})")
                        from time import sleep
                        sleep(30)
                        self.try_times = 0
                    else:
                        self.key_manager.rotate_to_next_key()
                        self.try_times += 1
                    continue
                    
                else:
                    # 其他錯誤
                    print(f"錯誤: {str(e)}")
                    return None

    # 批改所有學生作業
    def grade_all_homework(self):
        results = []
        
        for student_info, homework in self.homework_data.items():
            # 解析學號和姓名
            parts = student_info.split(" ", 1)
            student_id = parts[0]
            student_name = parts[1] if len(parts) > 1 else ""
            
            # 批改作業
            result = self.grade_homework(student_id, student_name, homework)
            if result:
                results.append(result)
        
        return results
    
    # 儲存批改結果到 JSON 檔案
    def save_results(self, results):
        # 確保 output_path 目錄存在
        self.output_path.mkdir(exist_ok=True)

        # 儲存完整 JSON 結果
        report_file = self.output_path / "grading_results.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n已輸出完整批改結果至：{report_file}")

        self.generate_excel_format(results)

    # 從 questions.md 讀取題數
    def get_question_count(self):
        if not self.questions_path.exists():
            return int(input("找不到 questions.md,請輸入題數: "))

        content = self.questions_path.read_text(encoding="utf-8")
        # 匹配行首的數字加點(如: 1., 2., 3.)
        pattern = r'^\d+\.\s+'
        matches = re.findall(pattern, content, re.MULTILINE)
        count = len(matches)

        print(f"從 {self.questions_path} 讀取到 {count} 題")
        return count

    # 產生 Excel 格式的文字檔
    def generate_excel_format(self, results):
        # 確保 output_path 目錄存在
        self.output_path.mkdir(exist_ok=True)

        # 建立結果字典以便快速查找（以字串學號為 key）
        results_dict = {r.get("student_id"): r for r in (results or [])}

        # 載入學生名單
        student_list = [
            (idx + 1, student["id"], student["name"]) 
            for idx, student in enumerate(self.students_data)
        ]

        # 寫入 CSV
        with open(self.output_path / "homework_scores.csv", "w", encoding="utf-8-sig", newline="") as csvfile:
            writer = csv.writer(csvfile)

            # 標頭（配合 Excel 欄位）
            questions_count = self.get_question_count()
            writer.writerow(["編號", "學號", "中文姓名", "作業成績"] + [f"{i}" for i in range(1, questions_count + 1)] + ["備註"])

            for idx, student_id, name in student_list:
                r = results_dict.get(student_id)
                if r:
                    total = r.get("total_score", "")
                    # 動態依題數取值：question_1..question_n
                    q_scores = [r.get(f"question_{i}", "") for i in range(1, questions_count + 1)]
                    remarks = r.get("remarks", "")
                else:
                    total = ""
                    q_scores = [""] * questions_count
                    remarks = ""

                writer.writerow([idx, student_id, name, total] + q_scores + [remarks])

        print(f"已輸出 CSV 至：{self.output_path / 'homework_scores.csv'}")
    
    def run(self):
        print("=" * 40)
        print("AI Grader - 作業批改系統")
        print("=" * 40)
        print(f"\n載入資源完成：")
        print(f"- 題目檔案：{self.questions_path}")
        print(f"- 評分標準：{self.grading_criteria_path}")
        print(f"- 學生作業：{self.homework_data_path}")
        print(f"- 學生人數：{len(self.homework_data)} 人\n")
        
        # 開始批改
        print("開始批改作業...\n")
        results = self.grade_all_homework()
        
        # 儲存結果
        print(f"\n批改完成！共批改 {len(results)} 位學生作業")
        self.save_results(results)
        
        # 顯示統計
        self.show_statistics(results)
    
    # 顯示批改統計
    def show_statistics(self, results):
        if not results:
            return
        
        scores = [int(r["total_score"]) for r in results]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        print("\n" + "=" * 40)
        print("批改統計")
        print("=" * 40)
        print(f"平均分數：{avg_score:.2f}")
        print(f"最高分數：{max_score}")
        print(f"最低分數：{min_score}")
        print("=" * 40)

if __name__ == "__main__":
    grader = HomeworkGrader(
        grading_criteria_path=r"knowledge/grading_criteria.md",
        output_format_path=r"knowledge/output_format.md",
        questions_path=r"knowledge/questions.md",
        homework_data_path=r"RUN/hw_all.json"
    )