import json
import sys
import os
from pathlib import Path

# 確保父目錄在 sys.path，這樣可以使用絕對匯入 `ai_grader`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ai_grader import HomeworkGrader

# 載入題目
questions_path = Path("knowledge/questions.md")
with open(questions_path, "r", encoding="utf-8") as f:
    questions = f.read()

# 載入評分標準
grading_criteria_path = Path("knowledge/grading_criteria.md")
with open(grading_criteria_path, "r", encoding="utf-8") as f:
    grading_criteria = f.read()

# 載入輸出格式
output_format_path = Path("knowledge/output_format.md")
with open(output_format_path, "r", encoding="utf-8") as f:
    output_format = f.read()

# 載入學生作業
hw_path = Path("RUN/hw_all.json")
with open(hw_path, "r", encoding="utf-8") as f:
    homework_data = json.load(f)

# 避免在 __init__ 建立 Groq client（需 API key），建一個空的實例然後手動設置屬性
# 使用 object.__new__ 來繞過 __init__
inst = object.__new__(HomeworkGrader)
inst.questions = questions
inst.grading_criteria = grading_criteria
inst.output_format = output_format
inst.homework_data = homework_data

# 選一個學生來測試
first_student = list(homework_data.items())[-1]
student_info, homework = first_student
parts = student_info.split(" ", 1)
student_id = parts[0]
student_name = parts[1] if len(parts) > 1 else ""

prompt = inst.create_grading_prompt(student_id, student_name, homework)
with open(Path("test") / "test_output.md", "w", encoding="utf-8") as f:
    f.write(prompt)
print(f"已輸出 Markdown 至: {Path('test') / 'test_output.md'}")