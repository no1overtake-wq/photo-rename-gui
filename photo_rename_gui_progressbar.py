import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from pathlib import Path
import threading
import time
import re
from collections import defaultdict
import shutil

paused = False
start_time = None
total_leaf_folders = 0
processed_leaf_folders = 0


def extract_number(name):
    match = re.search(r'(\d+)', name)
    return int(match.group(1)) if match else None


# =========================
# 파일 이름 변경
# =========================
def process_leaf_folder(leaf_folder: Path, date_str: str):
    groups = defaultdict(list)
    for f in leaf_folder.iterdir():
        if f.is_file():
            groups[f.suffix.lower()].append(f)

    for files in groups.values():
        numbered = [(f, extract_number(f.stem)) for f in files]

        if any(num is not None for _, num in numbered):
            numbered.sort(key=lambda x: (x[1] is None, x[1]))
            sorted_files = [f for f, _ in numbered]
        else:
            sorted_files = sorted(files, key=lambda f: f.name.lower())

        total = len(sorted_files)

        for idx, file in enumerate(sorted_files, start=1):
            if total == 1:
                new_name = f"{date_str}{file.suffix}"
            else:
                new_name = f"{date_str} ({idx:02d}){file.suffix}"

            new_path = file.with_name(new_name)
            if not new_path.exists():
                file.rename(new_path)


def process_date_folder(date_folder: Path):
    global processed_leaf_folders

    if not re.fullmatch(r"\d{6}", date_folder.name):
        return

    date_str = f"20{date_folder.name[:2]}-{date_folder.name[2:4]}-{date_folder.name[4:]}"

    for path in date_folder.rglob("*"):
        if path.is_dir() and not any(p.is_dir() for p in path.iterdir()):
            while paused:
                time.sleep(0.1)

            process_leaf_folder(path, date_str)
            processed_leaf_folders += 1
            update_progress()


# =========================
# story 폴더 이동
# =========================
def move_files_to_story():
    if not folder_path.get():
        messagebox.showwarning("경고", "폴더를 선택하세요.")
        return

    root = Path(folder_path.get())
    moved = 0

    for path in root.rglob("*"):
        if path.is_dir() and not any(p.is_dir() for p in path.iterdir()):
            story_dir = path / "story"
            story_dir.mkdir(exist_ok=True)

            for f in path.iterdir():
                if f.is_file():
                    target = story_dir / f.name
                    if not target.exists():
                        shutil.move(str(f), str(target))
                        moved += 1

    messagebox.showinfo("완료", f"{moved}개 파일을 story 폴더로 이동했습니다.")


# =========================
# 빈 폴더 삭제
# =========================
def remove_empty_folders():
    if not folder_path.get():
        messagebox.showwarning("경고", "폴더를 선택하세요.")
        return

    root = Path(folder_path.get())
    removed = 0

    dirs = sorted(
        [p for p in root.rglob("*") if p.is_dir()],
        key=lambda x: len(x.parts),
        reverse=True
    )

    for d in dirs:
        try:
            if not any(d.iterdir()):
                d.rmdir()
                removed += 1
        except Exception:
            pass

    messagebox.showinfo("완료", f"빈 폴더 {removed}개를 삭제했습니다.")


# =========================
# 진행 표시
# =========================
def update_progress():
    progress = (processed_leaf_folders / total_leaf_folders) * 100 if total_leaf_folders else 0
    progress_var.set(progress)

    elapsed = time.time() - start_time
    elapsed_label.config(text=f"진행 시간: {int(elapsed)}초")


def count_leaf_folders(root: Path):
    return sum(
        1 for p in root.rglob("*")
        if p.is_dir() and not any(c.is_dir() for c in p.iterdir())
    )


def start_process():
    global paused, start_time, processed_leaf_folders, total_leaf_folders

    if not folder_path.get():
        messagebox.showwarning("경고", "폴더를 선택하세요.")
        return

    paused = False
    processed_leaf_folders = 0
    start_time = time.time()

    root = Path(folder_path.get())
    total_leaf_folders = count_leaf_folders(root)

    def run():
        for folder in root.iterdir():
            if folder.is_dir():
                process_date_folder(folder)
        messagebox.showinfo("완료", "파일 이름 변경이 완료되었습니다.")

    threading.Thread(target=run, daemon=True).start()


def toggle_pause():
    global paused
    paused = not paused
    pause_btn.config(text="재개" if paused else "일시 중지")


def select_folder():
    path = filedialog.askdirectory()
    if path:
        folder_path.set(path)


# =========================
# GUI
# =========================
root = tk.Tk()
root.title("파일 정리 도구")
root.geometry("360x220")

folder_path = tk.StringVar()

# ── 폴더 선택 줄 ──
top_frame = tk.Frame(root)
top_frame.pack(pady=8, padx=8, fill="x")

tk.Button(top_frame, text="폴더 선택", command=select_folder).pack(side="left")
tk.Entry(top_frame, textvariable=folder_path).pack(side="left", fill="x", expand=True, padx=6)

# ── 실행 / 일시중지 / 진행바 ──
mid_frame = tk.Frame(root)
mid_frame.pack(pady=8, padx=8, fill="x")

tk.Button(mid_frame, text="실행", width=6, command=start_process).pack(side="left")
pause_btn = tk.Button(mid_frame, text="일시 중지", width=8, command=toggle_pause)
pause_btn.pack(side="left", padx=4)

progress_var = tk.DoubleVar()
ttk.Progressbar(mid_frame, variable=progress_var, maximum=100).pack(
    side="left", fill="x", expand=True, padx=4
)

# ── story / 빈 폴더 버튼 한 줄 ──
bottom_btn_frame = tk.Frame(root)
bottom_btn_frame.pack(pady=6)

tk.Button(
    bottom_btn_frame, text="story 폴더 이동", width=16, command=move_files_to_story
).pack(side="left", padx=4)

tk.Button(
    bottom_btn_frame, text="빈 폴더 삭제", width=16, command=remove_empty_folders
).pack(side="left", padx=4)

# ── 진행 시간 ──
elapsed_label = tk.Label(root, text="진행 시간: 0초")
elapsed_label.pack(pady=6)

root.mainloop()
