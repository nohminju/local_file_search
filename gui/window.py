"""문서 본문 검색과 임시 구현된 이미지 유사도 검색 화면."""
import tkinter as tk
from tkinter import filedialog, ttk


# %% 1. 화면 준비
class DocumentSearchApp:
    def __init__(self, root, service_factory):
        self.root = root
        self.service_factory = service_factory
        self.service = None
        self.folder = tk.StringVar()
        self.query = tk.StringVar()
        self.mode = tk.StringVar(value="문서 본문")
        self.status = tk.StringVar(value="폴더 선택 → 분석 → 검색")

        root.title("코드·문서 검색")
        root.geometry("760x480")
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="문서 본문 검색 / 이미지 유사도 검색(임시 구현)").pack(anchor="w")
        ttk.Label(frame, textvariable=self.folder).pack(anchor="w", pady=6)
        ttk.Button(frame, text="폴더 선택", command=self.select_folder).pack(anchor="w")
        ttk.Button(frame, text="분석", command=self.analyze).pack(anchor="w", pady=6)

        ttk.Entry(frame, textvariable=self.query).pack(fill="x")
        ttk.Combobox(frame, textvariable=self.mode, values=("문서 본문", "이미지 유사도 검색(임시 구현)"), state="readonly").pack(anchor="w")
        self.search_button = ttk.Button(frame, text="검색", command=self.search, state="disabled")
        self.search_button.pack(anchor="w", pady=6)
        ttk.Label(frame, textvariable=self.status).pack(anchor="w")

        self.output = tk.Text(frame, height=12, wrap="word", state="disabled")
        self.output.pack(fill="both", expand=True, pady=6)

    def select_folder(self):
        # 2. 폴더 변경 시 이전 검색 상태를 지운다.
        path = filedialog.askdirectory(parent=self.root)
        if path:
            self.folder.set(path)
            self.service = None
            self.search_button.configure(state="disabled")
            self.show_text("")
            self.status.set("분석 버튼을 누르세요.")

    def analyze(self):
        # 3. 실제 로더·인코더·DB 연결을 실행하고 오류는 화면에 알린다.
        if not self.folder.get():
            self.status.set("폴더를 먼저 선택하세요.")
            return

        self.service = None
        self.search_button.configure(state="disabled")
        self.show_text("")
        self.status.set("실제 모델 준비·파일 분석 중입니다. 완료까지 기다려 주세요.")
        self.root.update_idletasks()

        try:
            service = self.service_factory()
            saved_files, failures = service.analyze(self.folder.get())
        except Exception as error:
            self.status.set(f"분석 실패: {error}")
            return

        self.service = service
        self.search_button.configure(state="normal")
        self.status.set(f"저장 {len(saved_files)}개 / 읽기 실패 {len(failures)}개")
        lines = []
        for path, reason in failures:
            lines.append(f"읽기 실패: {path.name} / {reason}")
        self.show_text("\n".join(lines))

    def search(self):
        # 4. 같은 인코더·DB로 검색하고 실제 이름과 경로를 표시한다.
        if self.service is None:
            return
        if not self.query.get().strip():
            self.status.set("검색 문장을 입력하세요.")
            return

        self.show_text("")
        try:
            mode = 'documents' if self.mode.get() == '문서 본문' else 'images'
            results = self.service.search(self.query.get(), mode=mode)
        except Exception as error:
            self.status.set(f"검색 실패: {error}")
            return

        lines = []
        for info, score in results:
            lines.append(f"{info.file_name} / 유사도 {score:.4f}\n{info.file_path}\n")
        self.show_text("\n".join(lines))
        self.status.set(f"검색 결과 {len(results)}개")

    def show_text(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")
