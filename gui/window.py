"""CustomTkinter 기반 로컬 파일 검색 화면."""
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DocumentSearchApp(ctk.CTk):
    """폴더 분석, 검색, 결과 표시를 담당하는 메인 GUI 창."""

    def __init__(self, service_factory):
        super().__init__()
        self.service_factory = service_factory
        self.service = None
        self.folder = ""
        self.busy = False
        self.messages = queue.Queue()
        self.tasks = queue.Queue()
        threading.Thread(target=self.worker_loop, daemon=True).start()

        self.title("Local File Search")
        self.geometry("900x650")
        self.minsize(720, 500)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=22)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(content, text="Local File Search", font=ctk.CTkFont(size=25, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 18)
        )

        folder_row = ctk.CTkFrame(content, fg_color="transparent")
        folder_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        folder_row.grid_columnconfigure(0, weight=1)
        self.folder_label = ctk.CTkLabel(
            folder_row, text="분석할 폴더를 선택하세요", anchor="w", fg_color="#252a34", corner_radius=8
        )
        self.folder_label.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=9, ipadx=12)
        self.folder_button = ctk.CTkButton(folder_row, text="폴더 선택", width=90, command=self.select_folder)
        self.folder_button.grid(row=0, column=1, padx=(0, 8))
        self.analyze_button = ctk.CTkButton(folder_row, text="분석", width=75, command=self.analyze)
        self.analyze_button.grid(row=0, column=2)

        search_row = ctk.CTkFrame(content, fg_color="transparent")
        search_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        search_row.grid_columnconfigure(0, weight=1)
        self.query_entry = ctk.CTkEntry(
            search_row, height=42, placeholder_text="찾고 싶은 파일의 내용을 입력하세요"
        )
        self.query_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.query_entry.bind("<Return>", lambda event: self.search())
        self.mode = ctk.StringVar(value="문서")
        self.mode_switch = ctk.CTkSegmentedButton(
            search_row, values=["문서", "이미지"], variable=self.mode
        )
        self.mode_switch.grid(row=0, column=1, padx=(0, 8))
        self.search_button = ctk.CTkButton(search_row, text="검색", width=80, command=self.search)
        self.search_button.grid(row=0, column=2)
        self.search_button.configure(state="disabled")

        self.status = ctk.CTkLabel(content, text="폴더 선택 → 분석 → 검색", anchor="w", text_color="#aab2c0")
        self.status.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self.results_frame = ctk.CTkScrollableFrame(content, corner_radius=10, label_text="검색 결과")
        self.results_frame.grid(row=4, column=0, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.show_message("분석 후 검색 결과가 여기에 표시됩니다.")

        self.after(100, self.poll_messages)

    def show_message(self, text):
        self.clear_results()
        ctk.CTkLabel(self.results_frame, text=text, text_color="#9ba4b4", anchor="w").grid(
            row=0, column=0, sticky="ew", padx=12, pady=12
        )

    def clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

    def set_busy(self, busy, text=""):
        self.busy = busy
        self.folder_button.configure(state="disabled" if busy else "normal")
        self.analyze_button.configure(state="disabled" if busy else "normal")
        self.search_button.configure(state="normal" if self.service and not busy else "disabled")
        if text:
            self.status.configure(text=text)

    def select_folder(self):
        folder = filedialog.askdirectory(parent=self)
        if not folder:
            return
        self.folder = folder
        self.folder_label.configure(text=folder)
        self.service = None
        self.search_button.configure(state="disabled")
        self.show_message("분석 버튼을 눌러 파일을 준비하세요.")
        self.status.configure(text="분석 대기 중")

    def worker_loop(self):
        """모델 작업은 이 스레드에서, 화면 갱신은 poll_messages에서 처리한다."""
        while True:
            job, args = self.tasks.get()
            try:
                self.messages.put((job, job(*args), None))
            except Exception as error:
                self.messages.put((job, None, error))

    def run_worker(self, job, *args):
        self.tasks.put((job, args))

    def analyze(self):
        if self.busy:
            return
        if not self.folder:
            self.status.configure(text="먼저 폴더를 선택하세요.")
            return
        self.service = None
        self.set_busy(True, "모델 준비 및 파일 분석 중... (첫 실행은 시간이 걸릴 수 있습니다)")
        self.show_message("파일을 분석하고 있습니다...")
        self.run_worker(self.analyze_job, self.folder)

    def analyze_job(self, folder):
        service = self.service_factory()
        documents, failures = service.analyze(folder)
        return service, documents, failures

    def search(self):
        if self.busy or self.service is None:
            return
        query = self.query_entry.get().strip()
        if not query:
            self.status.configure(text="검색어를 입력하세요.")
            return
        mode = "documents" if self.mode.get() == "문서" else "images"
        self.set_busy(True, "검색 중...")
        self.show_message("검색 결과를 불러오고 있습니다...")
        self.run_worker(self.search_job, query, mode)

    def search_job(self, query, mode):
        return self.service.search(query, mode=mode)

    def poll_messages(self):
        try:
            while True:
                job, result, error = self.messages.get_nowait()
                self.set_busy(False)
                if error:
                    self.show_message("작업에 실패했습니다.")
                    self.status.configure(text=f"오류: {error}")
                elif job == self.analyze_job:
                    self.service, documents, failures = result
                    self.set_busy(False, f"분석 완료: {len(documents)}개 파일 / 읽기 실패 {len(failures)}개")
                    if failures:
                        self.show_message("분석 완료. 일부 파일은 읽지 못했습니다. 검색을 진행할 수 있습니다.")
                    else:
                        self.show_message("분석이 완료되었습니다. 검색어를 입력하세요.")
                else:
                    self.show_results(result)
                    self.status.configure(text=f"검색 결과 {len(result)}개 (유사도는 정확도/확률이 아닙니다)")
        except queue.Empty:
            pass
        self.after(100, self.poll_messages)

    def show_results(self, results):
        self.clear_results()
        if not results:
            self.show_message("검색 결과가 없습니다.")
            return
        for index, (info, score) in enumerate(results):
            path = str(info.file_path)
            card = ctk.CTkFrame(self.results_frame, corner_radius=8)
            card.grid(row=index, column=0, sticky="ew", padx=5, pady=5)
            card.grid_columnconfigure(0, weight=1)
            name = ctk.CTkLabel(card, text=info.file_name, anchor="w", font=ctk.CTkFont(weight="bold"))
            name.grid(row=0, column=0, sticky="ew", padx=12, pady=(9, 1))
            detail = ctk.CTkLabel(
                card, text=f"유사도 {score:.4f}  |  {path}", anchor="w", text_color="#aab2c0"
            )
            detail.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 9))
            button = ctk.CTkButton(card, text="열기", width=58, command=lambda p=path: self.open_file(p))
            button.grid(row=0, column=1, rowspan=2, padx=12)
            for widget in (card, name, detail):
                widget.bind("<Double-Button-1>", lambda event, p=path: self.open_file(p))


    def open_file(self, path):
        if not Path(path).is_file():
            messagebox.showerror("파일 열기", "파일이 존재하지 않습니다.", parent=self)
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as error:
            messagebox.showerror("파일 열기", str(error), parent=self)
