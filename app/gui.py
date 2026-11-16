"""tkinter 中文界面（薄层：业务逻辑全部在 collect / durations / rpp）。"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from app.collect import collect_from_files, collect_from_folder
from app.durations import get_duration, get_sample_rate
from app.rpp import RppItem, build_rpp, write_rpp

_AUDIO_PATTERNS = ["*.wav", "*.aiff", "*.aif", "*.flac", "*.mp3", "*.m4a", "*.ogg", "*.oga"]


def _normalize_rpp_suffix(name: str) -> str:
    while name.lower().endswith(".rpp"):
        name = name[:-4]
    return name + ".rpp"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("REAPER 工程生成工具")
        self.geometry("680x520")
        self.groups = []
        self.selected_folder: str | None = None
        self._build_widgets()
        self.lift()
        self.focus_force()
        self.after(100, self._flash_topmost)

    def _flash_topmost(self):
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(200, lambda: self.attributes("-topmost", False))

    def _build_widgets(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)
        self.btn_files = tk.Button(top, text="选择文件…", command=self.select_files)
        self.btn_files.pack(side="left", padx=4)
        self.btn_folder = tk.Button(top, text="选择文件夹…", command=self.select_folder)
        self.btn_folder.pack(side="left", padx=4)

        self.listbox = tk.Listbox(self)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=4)

        self.btn_generate = tk.Button(self, text="生成工程", command=self.generate)
        self.btn_generate.pack(pady=4)

        self.log_text = tk.Text(self, height=9, state="disabled")
        self.log_text.pack(fill="x", padx=8, pady=8)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for button in (self.btn_files, self.btn_folder, self.btn_generate):
            button.configure(state=state)
        if busy:
            self.update_idletasks()

    def _log(self, message: str):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self._log(message))
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _show_groups(self, result):
        self.groups = result.groups
        self.listbox.delete(0, "end")
        for group in self.groups:
            self.listbox.insert("end", f"{group.name}（{len(group.files)} 个文件）")
        for message in result.logs:
            self._log(message)
        if self.groups:
            self._log(f"共 {len(self.groups)} 个分组。点击「生成工程」继续。\n")
        else:
            self._log("未找到任何可用的音频文件。\n")

    def select_files(self):
        self._set_busy(True)
        try:
            paths = filedialog.askopenfilenames(
                title="选择音频文件",
                filetypes=[("音频文件", " ".join(_AUDIO_PATTERNS)), ("所有文件", "*.*")],
            )
        finally:
            self._set_busy(False)
        if not paths:
            return
        self.selected_folder = None
        self._show_groups(collect_from_files(paths))

    def select_folder(self):
        self._set_busy(True)
        try:
            folder = filedialog.askdirectory(title="选择文件夹")
        finally:
            self._set_busy(False)
        if not folder:
            return
        self.selected_folder = folder
        self._show_groups(collect_from_folder(folder))

    def generate(self):
        if not self.groups:
            self._log("请先选择文件或文件夹。\n")
            return
        if len(self.groups) == 1:
            self._generate_single(self.groups[0])
        else:
            self._generate_multiple()

    def _generate_single(self, group):
        audio_dir = str(Path(group.files[0]).parent)
        self._set_busy(True)
        try:
            target = filedialog.asksaveasfilename(
                title="保存工程",
                initialdir=audio_dir,
                initialfile=f"{group.name}.rpp",
            )
        finally:
            self._set_busy(False)
        if not target:
            self._log("已取消保存。\n")
            return
        target = _normalize_rpp_suffix(str(target))
        self._run_generation(group, Path(target))

    def _generate_multiple(self):
        initial = self.selected_folder or str(Path(self.groups[0].files[0]).parent)
        self._set_busy(True)
        try:
            save_dir = filedialog.askdirectory(title="选择保存目录", initialdir=initial)
        finally:
            self._set_busy(False)
        if not save_dir:
            self._log("已取消保存。\n")
            return
        self._multi_dir = Path(save_dir)
        self._multi_generated = 0
        self._multi_pending = list(self.groups)
        self._set_busy(True)
        self._process_next_group()

    def _process_next_group(self):
        if not self._multi_pending:
            self._finish_multiple()
            return
        group = self._multi_pending.pop(0)
        target = self._multi_dir / f"{group.name}.rpp"
        if target.exists():
            if not messagebox.askyesno("确认覆盖", f"{target.name} 已存在，是否覆盖？"):
                self._log(f"已跳过（用户拒绝覆盖）：{target.name}")
                self._process_next_group()
                return
        self._run_generation(group, target, on_done=self._on_group_done)

    def _on_group_done(self):
        self._multi_generated += 1
        self._process_next_group()

    def _finish_multiple(self):
        self._set_busy(False)
        if self._multi_generated == 0:
            self._log("没有生成任何工程。\n")
            return
        messagebox.showinfo("完成", f"已生成 {self._multi_generated} 个工程到：\n{self._multi_dir}")
        self._open_path(str(self._multi_dir))

    def _run_generation(self, group, target: Path, on_done=None):
        self._set_busy(True)

        def work():
            ok = False
            try:
                ok = self._write_group_rpp(group, target)
            except Exception as exc:
                self.after(0, lambda: self._log(f"生成失败：{target}（{exc}）"))
            finally:
                self.after(0, lambda ok=ok: self._generation_done(ok, target, on_done))

        threading.Thread(target=work, daemon=True).start()

    def _generation_done(self, ok, target, on_done):
        if on_done is not None:
            if ok:
                on_done()
            else:
                self._process_next_group()
            return
        self._set_busy(False)
        if ok and messagebox.askyesno("完成", "工程已生成。是否立即用系统默认方式打开？"):
            self._open_path(str(target))

    def _write_group_rpp(self, group, target: Path) -> bool:
        items = []
        for path in group.files:
            try:
                length = get_duration(path)
            except Exception as exc:  # 解析失败跳过并提示（契约 §4）
                self._log(f"跳过（无法读取时长）：{path.name}（{exc}）")
                continue
            items.append(RppItem(path=path, length=length))
        if not items:
            self._log(f"分组「{group.name}」没有可用音频，已跳过。\n")
            return False
        try:
            sample_rate = get_sample_rate(items[0].path)
        except Exception:
            sample_rate = 44100
        try:
            content = build_rpp(items, str(target.parent), sample_rate=sample_rate)
            write_rpp(target, content)
        except ValueError as exc:
            self._log(f"跳过（无法生成相对路径，音频与保存位置可能不在同一磁盘）：{group.name}（{exc}）")
            return False
        except OSError as exc:
            self._log(f"写入失败：{target}（{exc}）\n")
            return False
        self._log(f"已生成：{target}")
        return True

    def _open_path(self, path: str):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            self._log(f"自动打开失败（可手动打开）：{path}（{exc}）")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
