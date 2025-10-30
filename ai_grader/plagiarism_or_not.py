import json
import re
from pathlib import Path
from difflib import SequenceMatcher
from itertools import combinations

OUTPUT_PATH = Path("RUN")
STUDENTS_DATA_PATH = Path("knowledge") / "students_data.json"
QUESTIONS_PATH = Path("knowledge") / "questions.md"

# 從 questions.md 讀取題數
def get_question_count(questions_path):
    if not questions_path.exists():
        return int(input("找不到 questions.md, 請輸入題數: "))
    
    content = questions_path.read_text(encoding="utf-8")
    # 匹配行首的數字加點(如: 1., 2., 3.)
    pattern = r'^\d+\.\s+'
    matches = re.findall(pattern, content, re.MULTILINE)
    count = len(matches)
    
    print(f"從 {questions_path} 讀取到 {count} 題")
    return count

# 載入學生名單
def _load_students(students_data_path):
    students_file = students_data_path
    if students_file.exists():
        students_data = json.loads(students_file.read_text(encoding="utf-8"))
        # {"id":..., "name":...}
        return [(student["id"], student["name"]) for student in students_data]
    else:
        raise FileNotFoundError(f"找不到學生資料檔案：{students_file}")

# 計算兩段文字的相似度
def calculate_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1, text2).ratio()

# 根據檔名推斷題號
def infer_question(file_name, max_questions=4):
    pattern = rf"([1-{max_questions}])(?=[^\d]*\.py$)"
    m = re.search(pattern, file_name)
    if m:
        return int(m.group(1))
    else:
        print(f"無法推斷題號: {file_name}")
        return None

# 執行抄襲檢查
def check_plagiarism(homework_data, student_list, threshold, questions, cls=None):
    student_dict = {}
    student_keys = []
    for sid, name in student_list:
        for key in homework_data.keys():
            if sid in key:
                student_dict[key] = (sid, name)
                student_keys.append(key)
                break

    print(f"找到 {len(student_keys)} 位學生的作業資料")

    if cls is None:
        raise SystemExit("未指定類別，停止執行")

    submissions_by_q = {q: [] for q in range(1, questions + 1)}
    for student_key in student_keys:
        data = homework_data.get(student_key, {})
        for category in cls:
            files = data.get(category, {})
            for fname, content in files.items():
                q = infer_question(fname, max_questions=questions)
                if q in submissions_by_q:
                    submissions_by_q[q].append((student_key, fname, content))

    plagiarism_cases = []

    for q in range(1, questions + 1):
        per_student = {}
        for student_key, fname, content in submissions_by_q[q]:
            per_student.setdefault(student_key, (fname, content))
        entries = [(sk, fn, ct) for sk, (fn, ct) in per_student.items()]

        # print(f"第{q}題可比對學生數: {len(entries)}")

        count_for_q = 0
        for (k1, f1, c1), (k2, f2, c2) in combinations(entries, 2):
            sim = calculate_similarity(str(c1), str(c2))
            if sim >= threshold:
                info1 = student_dict.get(k1, (k1, "未知"))
                info2 = student_dict.get(k2, (k2, "未知"))
                plagiarism_cases.append({
                    "question": q,
                    "student1": {"id": info1[0], "name": info1[1]},
                    "student2": {"id": info2[0], "name": info2[1]},
                    "file1": f1,
                    "file2": f2,
                    "similarity": round(sim * 100, 2)
                })
                count_for_q += 1
        # print(f"第{q}題完成比對，發現 {count_for_q} 組疑似抄襲")

    return plagiarism_cases

# 產生報告
def generate_plagiarism_report(plagiarism_cases, questions, output_path=OUTPUT_PATH):
    output_path.mkdir(exist_ok=True)
    with (output_path / "plagiarism_report.md").open("w", encoding="utf-8") as f:
        f.write("# 學生作業抄襲檢查報告\n\n")

        if not plagiarism_cases:
            f.write("未發現疑似抄襲的情況。\n")
            return

        sorted_cases = sorted(plagiarism_cases, key=lambda c: c.get("similarity", 0), reverse=True)
        f.write(f"共發現 {len(sorted_cases)} 組疑似抄襲的配對。\n\n")

        by_q = {q: [] for q in range(1, questions + 1)}
        for case in sorted_cases:
            by_q.setdefault(case["question"], []).append(case)

        for q in range(1, questions + 1):
            cases = by_q.get(q, [])
            if not cases:
                continue
            f.write(f"## 第 {q} 題\n\n")
            for case in cases:
                s1 = case["student1"]; s2 = case["student2"]
                f.write(f"- 相似度: {case['similarity']}%\n")
                f.write(f"  - 學生1: {s1['id']} {s1['name']}  檔案: {case.get('file1','')}\n")
                f.write(f"  - 學生2: {s2['id']} {s2['name']}  檔案: {case.get('file2','')}\n\n")

# 主函數
def plagiarism_check(homework_file, cls=None, questions_path=QUESTIONS_PATH, 
                     threshold=0.7, students_data_path=STUDENTS_DATA_PATH, output_path=OUTPUT_PATH):
    print(f"開始執行抄襲檢查...")

    questions = get_question_count(questions_path)

    homework_data = json.loads(Path(homework_file).read_text(encoding="utf-8"))
    students = _load_students(students_data_path)

    # 檢查抄襲
    plagiarism_cases = check_plagiarism(homework_data, students, threshold=threshold, questions=questions, cls=cls)
    
    # 產生報告
    generate_plagiarism_report(plagiarism_cases, questions=questions, output_path=output_path)

    # 顯示實際報告檔案路徑
    print(f"共發現 {len(plagiarism_cases)} 組疑似抄襲的配對")
    print(f"已輸出報告至: {output_path / 'plagiarism_report.md'}")
    
if __name__ == "__main__":
    homework_path = Path("RUN") / "hw_all.json"
    # 題數自動從 questions.md 讀取
    plagiarism_check(homework_path, cls=["上課完成", "回家完成"])
