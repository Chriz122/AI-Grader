import json
from pathlib import Path

OUTPUT_PATH = Path("RUN")
STUDENTS_DATA_PATH = Path("knowledge") / "students_data.json"

# 插入巢狀字典
def insert_nested(dictionary, path_parts, content):
    current = dictionary
    for part in path_parts[:-1]:
        current = current.setdefault(part, {})
    current[path_parts[-1]] = content

# 載入學生名單
def _load_students(students_data_path):
    students_file = students_data_path
    if students_file.exists():
        students_data = json.loads(students_file.read_text(encoding="utf-8"))
        # {"id":..., "name":...}
        return [(student["id"], student["name"]) for student in students_data]
    else:
        raise FileNotFoundError(f"找不到學生資料檔案：{students_file}")

# 將資料夾內的 Python 程式碼輸出為巢狀 JSON 結構
def hw_to_json(cls=["上課完成", "回家完成"], path=None, 
               students_data_path=STUDENTS_DATA_PATH, output_path=OUTPUT_PATH):
    students = _load_students(students_data_path)

    # 建立與 cls 對應的 base_dirs 清單
    if path:
        base_dirs = [Path(p) for p in path]
    else:
        base_dirs = [None] * len(cls)

    result = {}

    for sid, name in students:
        key = f"{sid} {name}"
        entry = {}
        
        def collect_from(base_dir: Path):
            if not base_dir:
                return {}
            # 找出學生資料夾（支援用空白或 tab 分隔的命名）
            candidates = [d for d in base_dir.iterdir() if d.is_dir() and (d.name.startswith(f"{sid} {name}") or d.name.startswith(f"{sid}\t{name}"))]
            if not candidates:
                return {}
            folder = sorted(candidates, key=lambda p: p.name)[0]
            student_dict = {}
            found = False
            for p in folder.rglob("*.py"):
                found = True
                content = p.read_text(encoding="utf-8")
                rel_path = p.relative_to(folder)
                insert_nested(student_dict, rel_path.parts, content)
            if not found:
                return {}
            return student_dict

        # 依照 cls 清單與 base_dirs 清單逐一收集
        for idx, label in enumerate(cls):
            base_dir = base_dirs[idx] if idx < len(base_dirs) else None
            entry[label] = collect_from(base_dir)

        result[key] = entry

    output_path.mkdir(exist_ok=True)
    (output_path / "hw_all.json").write_text(json.dumps(result, ensure_ascii=False, indent=4, sort_keys=False), encoding="utf-8")
    print(f"已輸出 JSON 至: {output_path / 'hw_all.json'}")
    
if __name__ == "__main__":
    hw_path_1 = r"data\HW\Homework (課堂上完成)"
    hw_path_2 = r"data\HW\Homework (非課堂上完成)"

    hw_to_json(path=[hw_path_1, hw_path_2], cls=["上課完成", "回家完成"])
