import tkinter as tk
from tkinter import BooleanVar, StringVar, ttk, scrolledtext
import os
from tkinter import messagebox
from dotenv import load_dotenv
import subprocess
from src.utils.logger import logger
import webbrowser
import threading
import time
import psutil  # 添加到文件顶部的导入语句中


class ControlUITk:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Whisper Input 控制台")
        self.root.geometry("900x650")
        self.root.configure(bg="#f5f5f5")

        # 设置最小窗口尺寸
        self.root.minsize(800, 600)

        # 初始化变量
        self.process = None
        self._log_file_pos = 0

        # 添加日志更新标志
        self.running = True

        # 添加日志更新定时器
        self._log_update_interval = 500  # 500ms

        self.config_expanded = False  # 添加配置面板展开状态标志

        # 清空日志文件
        if not os.path.exists("logs"):
            os.makedirs("logs")
        with open("logs/app.log", "w", encoding="utf-8") as f:
            f.truncate(0)

        logger.info("初始化控制界面")

        # 初始化变量
        self.init_variables()

        # 设置样式
        self.setup_styles()

        # 初始化界面
        self.init_ui()

        # 加载现有配置
        self.load_config()

        # 启动日志监控
        self.start_log_monitor()

        # 添加进程检查和清理
        self.check_and_kill_existing_process()

        # 添加窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def check_and_kill_existing_process(self):
        """检查并清理已存在的进程"""
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] == "python.exe" and proc.pid != current_pid:
                        cmdline = proc.info["cmdline"]
                        if cmdline and "main.py" in cmdline:
                            logger.info(f"发现运行中的主程序进程 (PID: {proc.pid})")
                            proc.terminate()
                            proc.wait(timeout=3)
                            logger.info("已终止运行中的主程序进程")
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.TimeoutExpired,
                ):
                    continue
        except Exception as e:
            logger.error(f"检查进程时出错: {str(e)}")

    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()

        # 定义颜色
        COLORS = {
            "primary": "#1976D2",
            "danger": "#D32F2F",
            "bg": "#f5f5f5",
            "card": "#ffffff",
            "text": "#333333",
            "border": "#e0e0e0",
        }

        # 配置通用样式
        style.configure(
            ".",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=("Microsoft YaHei UI", 9),
        )

        # 配置框架样式
        style.configure("Card.TFrame", background=COLORS["card"])

        # 配置标签框样式
        style.configure("Card.TLabelframe", background=COLORS["card"])
        style.configure(
            "Card.TLabelframe.Label",
            background=COLORS["card"],
            foreground=COLORS["text"],
            font=("Microsoft YaHei UI", 10, "bold"),
        )

        # 配置按钮样式
        style.configure(
            "Primary.TButton",
            background=COLORS["primary"],
            foreground="white",
            padding=(20, 8),
        )

        style.configure(
            "Danger.TButton",
            background=COLORS["danger"],
            foreground="white",
            padding=(20, 8),
        )

        # 添加次要按钮样式
        style.configure(
            "Secondary.TButton",
            background="#f0f0f0",
            foreground="#333333",
            padding=(20, 8),
        )

        # 配置输入框样式
        style.configure("App.TEntry", fieldbackground="white", padding=8)

    def init_variables(self):
        """初始化所有配置变量"""
        # 基础配置
        self.service_platform = StringVar(value="siliconflow")
        self.system_platform = StringVar(value="win")
        self.transcriptions_button = StringVar(value="f2")
        self.translations_button = StringVar(value="shift")

        # 功能选项
        self.convert_to_simplified = BooleanVar(value=True)
        self.add_symbol = BooleanVar(value=True)
        self.optimize_result = BooleanVar(value=False)
        self.keep_original_clipboard = BooleanVar(value=True)

        # GROQ配置
        self.groq_api_key = StringVar()
        self.groq_base_url = StringVar(value="https://api.groq.com/openai/v1")
        self.groq_add_symbol_model = StringVar(value="llama-3.3-70b-versatile")
        self.groq_optimize_result_model = StringVar(value="llama-3.3-70b-versatile")

        # 硅基流动配置
        self.siliconflow_api_key = StringVar()
        self.siliconflow_translate_model = StringVar(value="THUDM/glm-4-9b-chat")

    def init_ui(self):
        """初始化界面"""
        container = ttk.Frame(self.root, style="Card.TFrame", padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 顶部控制区域
        control_frame = ttk.Frame(container)
        control_frame.pack(fill=tk.X)

        # 左侧操作按钮
        left_frame = ttk.Frame(control_frame)
        left_frame.pack(side=tk.LEFT)

        self.start_btn = ttk.Button(
            left_frame,
            text="启动服务",
            command=self.start_main,
            style="Primary.TButton",
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(
            left_frame,
            text="停止服务",
            command=self.stop_main,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_btn.pack(side=tk.LEFT)

        # 右侧设置按钮
        self.config_btn = ttk.Button(
            control_frame,
            text="设置",
            command=self.show_config,
            style="Secondary.TButton",
        )
        self.config_btn.pack(side=tk.RIGHT)

        # 日志显示区域（设置更合适的高度比例）
        self.create_log_area(container)

    def show_config(self):
        """显示配置窗口"""
        if hasattr(self, "config_window") and self.config_window.winfo_exists():
            self.config_window.focus_force()
            return

        # 创建配置窗口
        self.config_window = tk.Toplevel(self.root)
        self.config_window.title("设置")
        self.config_window.geometry("800x600")  # 设置合适的大小
        self.config_window.minsize(800, 600)

        # 设置窗口位置（在按钮下方）
        btn_x = self.config_btn.winfo_rootx()
        btn_y = (
            self.config_btn.winfo_rooty() + self.config_btn.winfo_height()
        )  # 加上按钮高度

        # 调整窗口位置，使其居中对齐按钮
        window_x = max(0, btn_x - 375)  # 750/2=375，使窗口水平居中于按钮
        window_y = btn_y + 5  # 在按钮下方留出一点间距

        self.config_window.geometry(f"+{window_x}+{window_y}")

        # 设置模态窗口
        self.config_window.transient(self.root)
        self.config_window.grab_set()

        # 创建notebook
        notebook = ttk.Notebook(self.config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建各配置页面
        self.create_basic_page(notebook)
        self.create_advanced_page(notebook)
        self.create_api_page(notebook)

        # 创建底部按钮区域
        btn_frame = ttk.Frame(self.config_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            btn_frame,
            text="保存",
            command=lambda: self.save_and_close(),
            style="Primary.TButton",
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(btn_frame, text="取消", command=self.config_window.destroy).pack(
            side=tk.RIGHT
        )

    def save_and_close(self):
        """保存设置并关闭窗口"""
        self.save_settings()
        if hasattr(self, "config_window"):
            self.config_window.destroy()

    def create_basic_page(self, parent):
        """创建基础配置页"""
        basic_frame = ttk.Frame(parent, padding=15)
        parent.add(basic_frame, text="基础配置")

        # 平台选择
        platform_frame = ttk.LabelFrame(basic_frame, text="语音转录平台", padding=10)
        platform_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Radiobutton(
            platform_frame,
            text="硅基流动",
            value="siliconflow",
            variable=self.service_platform,
        ).pack(side=tk.LEFT, padx=10)

        ttk.Radiobutton(
            platform_frame, text="GROQ", value="groq", variable=self.service_platform
        ).pack(side=tk.LEFT, padx=10)

        # 系统配置
        system_frame = ttk.LabelFrame(basic_frame, text="系统配置", padding=10)
        system_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(system_frame, text="系统平台:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            system_frame, text="Windows", value="win", variable=self.system_platform
        ).pack(side=tk.LEFT, padx=10)

        ttk.Radiobutton(
            system_frame, text="MacOS", value="mac", variable=self.system_platform
        ).pack(side=tk.LEFT, padx=10)

        # 快捷键配置
        hotkey_frame = ttk.LabelFrame(basic_frame, text="快捷键配置", padding=10)
        hotkey_frame.pack(fill=tk.X, pady=(0, 10))

        grid = ttk.Frame(hotkey_frame)
        grid.pack(fill=tk.X, padx=5)

        # 转录按钮
        ttk.Label(grid, text="转录按钮:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(grid, textvariable=self.transcriptions_button, width=15).grid(
            row=0, column=1, padx=5, pady=5
        )
        ttk.Label(
            grid, text="推荐：Windows使用f2，MacOS使用alt", foreground="#666666"
        ).grid(row=0, column=2, padx=5, pady=5)

        # 翻译按钮
        ttk.Label(grid, text="翻译按钮:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Entry(grid, textvariable=self.translations_button, width=15).grid(
            row=1, column=1, padx=5, pady=5
        )
        ttk.Label(grid, text="推荐：shift", foreground="#666666").grid(
            row=1, column=2, padx=5, pady=5
        )

    def create_advanced_page(self, parent):
        """创建高级配置页"""
        advanced_frame = ttk.Frame(parent, padding=15)
        parent.add(advanced_frame, text="高级配置")

        # 功能选项
        options_frame = ttk.LabelFrame(advanced_frame, text="功能选项", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            options_frame, text="转换为简体中文", variable=self.convert_to_simplified
        ).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(
            options_frame, text="添加标点符号", variable=self.add_symbol
        ).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(
            options_frame, text="优化识别结果", variable=self.optimize_result
        ).pack(anchor=tk.W, pady=2)

        ttk.Checkbutton(
            options_frame,
            text="保留原始剪贴板内容",
            variable=self.keep_original_clipboard,
        ).pack(anchor=tk.W, pady=2)

    def create_api_page(self, parent):
        """创建 API 配置页"""
        api_frame = ttk.Frame(parent, padding=15)
        parent.add(api_frame, text="API配置")

        # ====== GROQ 配置区域 ======
        groq_frame = ttk.LabelFrame(api_frame, text="GROQ配置", padding=10)
        groq_frame.pack(fill=tk.X, pady=(0, 10))

        # API 配置
        ttk.Label(groq_frame, text="API Key:").pack(anchor=tk.W, pady=(0, 5))
        ttk.Entry(groq_frame, textvariable=self.groq_api_key, show="*", width=50).pack(
            fill=tk.X, pady=(0, 5)
        )

        ttk.Label(groq_frame, text="Base URL:").pack(anchor=tk.W, pady=(0, 5))
        ttk.Entry(groq_frame, textvariable=self.groq_base_url, width=50).pack(
            fill=tk.X, pady=(0, 10)
        )

        # 模型配置
        model_frame = ttk.Frame(groq_frame)
        model_frame.pack(fill=tk.X, padx=5)

        ttk.Label(model_frame, text="标点符号模型:").grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Entry(model_frame, textvariable=self.groq_add_symbol_model, width=40).grid(
            row=0, column=1, sticky="ew", padx=5, pady=5
        )

        ttk.Label(model_frame, text="优化结果模型:").grid(
            row=1, column=0, padx=5, pady=5
        )
        ttk.Entry(
            model_frame, textvariable=self.groq_optimize_result_model, width=40
        ).grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        model_frame.columnconfigure(1, weight=1)

        # ====== 硅基流动配置区域 ======
        sf_frame = ttk.LabelFrame(api_frame, text="硅基流动配置", padding=10)
        sf_frame.pack(fill=tk.X, pady=(10, 0))

        # API配置
        ttk.Label(sf_frame, text="API Key:").pack(anchor=tk.W, pady=(0, 5))
        ttk.Entry(
            sf_frame, textvariable=self.siliconflow_api_key, show="*", width=50
        ).pack(fill=tk.X, pady=(0, 10))

        # 模型配置
        sf_model_frame = ttk.Frame(sf_frame)
        sf_model_frame.pack(fill=tk.X, padx=5)

        ttk.Label(sf_model_frame, text="翻译模型:").grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Entry(
            sf_model_frame, textvariable=self.siliconflow_translate_model, width=40
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        sf_model_frame.columnconfigure(1, weight=1)

        # API Key获取链接
        link_frame = ttk.Frame(sf_frame)
        link_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(link_frame, text="获取API Key:", foreground="#666666").pack(
            side=tk.LEFT
        )

        ttk.Button(
            link_frame,
            text="https://cloud.siliconflow.cn/account/ak",
            command=self.open_key_url,
            style="Link.TButton",
        ).pack(side=tk.LEFT, padx=5)

    def create_control_area(self, parent):
        """创建控制按钮区域"""
        control_frame = ttk.Frame(parent, padding=15)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(
            control_frame,
            text="启动主程序",
            command=self.start_main,
            style="Primary.TButton",
        )
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = ttk.Button(
            control_frame,
            text="停止主程序",
            command=self.stop_main,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)

    def create_log_area(self, parent):
        """创建日志显示区域"""
        log_frame = ttk.Frame(parent, padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_view = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log_view.pack(fill=tk.BOTH, expand=True)

    def save_settings(self):
        """保存所有配置到环境变量文件"""
        try:
            config = {
                # 基础配置
                "SERVICE_PLATFORM": self.service_platform.get(),
                "SYSTEM_PLATFORM": self.system_platform.get(),
                "TRANSCRIPTIONS_BUTTON": self.transcriptions_button.get(),
                "TRANSLATIONS_BUTTON": self.translations_button.get(),
                # 功能选项
                "CONVERT_TO_SIMPLIFIED": str(self.convert_to_simplified.get()).lower(),
                "ADD_SYMBOL": str(self.add_symbol.get()).lower(),
                "OPTIMIZE_RESULT": str(self.optimize_result.get()).lower(),
                "KEEP_ORIGINAL_CLIPBOARD": str(
                    self.keep_original_clipboard.get()
                ).lower(),
                # GROQ配置
                "GROQ_API_KEY": self.groq_api_key.get(),
                "GROQ_BASE_URL": self.groq_base_url.get(),
                "GROQ_ADD_SYMBOL_MODEL": self.groq_add_symbol_model.get(),
                "GROQ_OPTIMIZE_RESULT_MODEL": self.groq_optimize_result_model.get(),
                # 硅基流动配置
                "SILICONFLOW_API_KEY": self.siliconflow_api_key.get(),
                "SILICONFLOW_TRANSLATE_MODEL": self.siliconflow_translate_model.get(),
            }

            # 读取现有配置
            env_lines = []
            if os.path.exists(".env"):
                with open(".env", "r", encoding="utf-8") as f:
                    env_lines = f.readlines()

            # 更新配置
            with open(".env", "w", encoding="utf-8") as f:
                written_keys = set()

                # 更新现有配置
                for line in env_lines:
                    key = line.split("=")[0].strip() if "=" in line else ""
                    if key in config:
                        f.write(f"{key}={config[key]}\n")
                        written_keys.add(key)
                    else:
                        f.write(line)

                # 添加新配置
                for key, value in config.items():
                    if key not in written_keys:
                        f.write(f"{key}={value}\n")

            logger.info("配置保存成功")
            messagebox.showinfo("成功", "设置已保存")
            self.load_config()  # 重新加载配置

        except Exception as e:
            error_msg = f"保存配置时出错：{str(e)}"
            logger.error(error_msg)
            messagebox.showerror("错误", error_msg)

    def load_config(self):
        """加载配置"""
        if os.path.exists(".env"):
            load_dotenv(override=True)

            # 加载基础配置
            self.service_platform.set(os.getenv("SERVICE_PLATFORM", "siliconflow"))
            self.system_platform.set(os.getenv("SYSTEM_PLATFORM", "win"))
            self.transcriptions_button.set(os.getenv("TRANSCRIPTIONS_BUTTON", "f2"))
            self.translations_button.set(os.getenv("TRANSLATIONS_BUTTON", "shift"))

            # 加载功能选项
            self.convert_to_simplified.set(
                os.getenv("CONVERT_TO_SIMPLIFIED", "true").lower() == "true"
            )
            self.add_symbol.set(os.getenv("ADD_SYMBOL", "true").lower() == "true")
            self.optimize_result.set(
                os.getenv("OPTIMIZE_RESULT", "false").lower() == "true"
            )
            self.keep_original_clipboard.set(
                os.getenv("KEEP_ORIGINAL_CLIPBOARD", "true").lower() == "true"
            )

            # 加载GROQ配置
            self.groq_api_key.set(os.getenv("GROQ_API_KEY", ""))
            self.groq_base_url.set(
                os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
            )
            self.groq_add_symbol_model.set(
                os.getenv("GROQ_ADD_SYMBOL_MODEL", "llama-3.3-70b-versatile")
            )
            self.groq_optimize_result_model.set(
                os.getenv("GROQ_OPTIMIZE_RESULT_MODEL", "llama-3.3-70b-versatile")
            )

            # 加载硅基流动配置
            self.siliconflow_api_key.set(os.getenv("SILICONFLOW_API_KEY", ""))
            self.siliconflow_translate_model.set(
                os.getenv("SILICONFLOW_TRANSLATE_MODEL", "THUDM/glm-4-9b-chat")
            )

    def open_key_url(self):
        """打开API Key获取页面"""
        webbrowser.open("https://cloud.siliconflow.cn/account/ak")

    def start_main(self):
        """启动主程序"""
        if not os.path.exists(".env"):
            self.log_view.insert(tk.END, "警告：未找到.env文件\n")
            return

        # 检查当前选择的平台
        current_platform = self.service_platform.get()
        if current_platform == "siliconflow":
            api_key = self.siliconflow_api_key.get().strip()
            if not api_key:
                messagebox.showerror("错误", "请先在设置中输入硅基流动 API Key")
                return
        else:  # groq
            api_key = self.groq_api_key.get().strip()
            if not api_key:
                messagebox.showerror("错误", "请先在设置中输入 GROQ API Key")
                return

        if self.process is None:
            logger.info("启动主程序")
            # 使用虚拟环境中的 Python
            venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
            if not os.path.exists(venv_python):
                messagebox.showerror("错误", "找不到虚拟环境，请确保已创建虚拟环境")
                return

            self.process = subprocess.Popen([venv_python, "main.py"])
            self.start_btn["state"] = "disabled"
            self.stop_btn["state"] = "normal"

    def stop_main(self):
        """停止主程序"""
        if self.process is not None:
            logger.info("停止主程序")
            self.process.terminate()
            self.process = None
            self.start_btn["state"] = "normal"
            self.stop_btn["state"] = "disabled"

    def start_log_monitor(self):
        """启动日志监控"""
        self._check_logs()

    def _check_logs(self):
        """定时检查日志更新"""
        if self.running:
            try:
                encodings = ["utf-8", "gbk", "latin1"]
                content = None

                for encoding in encodings:
                    try:
                        with open("logs/app.log", "r", encoding=encoding) as f:
                            f.seek(self._log_file_pos)
                            content = f.read()
                            self._log_file_pos = f.tell()

                            if self._log_file_pos > os.path.getsize("logs/app.log"):
                                self._log_file_pos = 0
                                f.seek(0)
                                content = f.read()

                            break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        logger.error(f"读取日志文件时出错 ({encoding}): {str(e)}")
                        continue

                if content:
                    self.log_view.insert(tk.END, content)
                    self.log_view.see(tk.END)

            except FileNotFoundError:
                self.log_view.insert(tk.END, "日志文件不存在\n")
            except Exception as e:
                self.log_view.insert(tk.END, f"更新日志显示时出错：{str(e)}\n")
                self._log_file_pos = 0

            # 安排下一次检查
            self.root.after(self._log_update_interval, self._check_logs)

    def on_closing(self):
        """窗口关闭时的处理"""
        try:
            # 停止日志监控
            self.running = False

            # 停止主程序
            if self.process is not None:
                logger.info("正在关闭主程序...")
                self.stop_main()

            # 确保所有 main.py 进程都被清理
            self.check_and_kill_existing_process()

            logger.info("正在关闭控制界面...")
            self.root.quit()  # 使用 quit 而不是 destroy
        except Exception as e:
            logger.error(f"关闭程序时出错: {str(e)}")

    def run(self):
        """运行程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = ControlUITk()
    app.run()
