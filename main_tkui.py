import tkinter as tk
from tkinter import ttk, scrolledtext
import os
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
        self.api_key = ""
        self._log_file_pos = 0

        # 添加日志更新标志
        self.running = True

        # 添加日志更新定时器
        self._log_update_interval = 500  # 500ms

        # 清空日志文件
        if not os.path.exists("logs"):
            os.makedirs("logs")
        with open("logs/app.log", "w", encoding="utf-8") as f:
            f.truncate(0)

        logger.info("初始化控制界面")

        # 设置样式
        self.setup_styles()

        # 初始化 UI
        self.init_ui()

        # 加载环境变量
        self.reload_env()

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

        # 配置输入框样式
        style.configure("App.TEntry", fieldbackground="white", padding=8)

    def init_ui(self):
        """初始化界面元素"""
        # 主容器
        container = ttk.Frame(self.root, style="Card.TFrame", padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # === API Key 设置区域 ===
        api_section = ttk.LabelFrame(
            container, text=" API Key 配置 ", style="Card.TLabelframe", padding=15
        )
        api_section.pack(fill=tk.X, padx=5, pady=(0, 15))

        # API Key 输入框
        self.api_key_var = tk.StringVar()
        api_input = ttk.Entry(
            api_section, textvariable=self.api_key_var, style="App.TEntry", width=50
        )
        api_input.pack(fill=tk.X, pady=(5, 10))

        # API Key 操作区域
        api_actions = ttk.Frame(api_section)
        api_actions.pack(fill=tk.X)

        link_label = ttk.Label(api_actions, text="获取 API Key:", foreground="#666666")
        link_label.pack(side=tk.LEFT)

        link_btn = ttk.Button(
            api_actions,
            text="https://cloud.siliconflow.cn/account/ak",
            command=self.open_key_url,
            style="Link.TButton",
        )
        link_btn.pack(side=tk.LEFT, padx=5)

        save_btn = ttk.Button(
            api_actions,
            text="保存设置",
            command=self.save_settings,
            style="Primary.TButton",
        )
        save_btn.pack(side=tk.RIGHT)

        # === 控制按钮区域 ===
        control_section = ttk.Frame(container)
        control_section.pack(fill=tk.X, pady=(0, 15))

        self.start_btn = ttk.Button(
            control_section,
            text="启动服务",
            command=self.start_main,
            style="Primary.TButton",
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(
            control_section,
            text="停止服务",
            command=self.stop_main,
            style="Danger.TButton",
        )
        self.stop_btn.pack(side=tk.LEFT)
        self.stop_btn["state"] = "disabled"

        # === 日志显示区域 ===
        log_section = ttk.LabelFrame(
            container, text=" 运行日志 ", style="Card.TLabelframe", padding=15
        )
        log_section.pack(fill=tk.BOTH, expand=True, padx=5)

        self.log_view = scrolledtext.ScrolledText(
            log_section,
            wrap=tk.WORD,
            font=("Consolas", 10),
            background="#1e1e1e",
            foreground="#d4d4d4",
            insertbackground="#d4d4d4",
            selectbackground="#264f78",
            selectforeground="white",
            padx=10,
            pady=10,
            relief="flat",
            borderwidth=1,
        )
        self.log_view.pack(fill=tk.BOTH, expand=True)

    def reload_env(self):
        """重新加载环境变量"""
        load_dotenv(override=True)
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
        self.api_key_var.set(self.api_key)

    def open_key_url(self):
        """打开API Key获取页面"""
        webbrowser.open("https://cloud.siliconflow.cn/account/ak")

    def save_settings(self):
        """保存API Key到环境变量文件"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            self.log_view.insert(tk.END, "API Key不能为空\n")
            return

        try:
            env_lines = []
            if os.path.exists(".env"):
                with open(".env", "r", encoding="utf-8") as f:
                    env_lines = f.readlines()

            found = False
            with open(".env", "w", encoding="utf-8") as f:
                for line in env_lines:
                    if line.startswith("SILICONFLOW_API_KEY="):
                        f.write(f"SILICONFLOW_API_KEY={api_key}\n")
                        found = True
                    else:
                        f.write(line)
                if not found:
                    f.write(f"\nSILICONFLOW_API_KEY={api_key}\n")

            self.log_view.insert(tk.END, "设置保存成功\n")
            self.reload_env()
        except Exception as e:
            self.log_view.insert(tk.END, f"保存失败：{str(e)}\n")

    def start_main(self):
        """启动主程序"""
        if not os.path.exists(".env"):
            self.log_view.insert(tk.END, "警告：未找到.env文件\n")
            return

        if not self.api_key_var.get().strip():
            self.log_view.insert(tk.END, "请先输入SILICONFLOW API Key\n")
            return

        if self.process is None:
            logger.info("启动主程序")
            # 使用虚拟环境中的 Python
            venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
            if not os.path.exists(venv_python):
                self.log_view.insert(
                    tk.END, "错误：找不到虚拟环境，请确保已创建虚拟环境\n"
                )
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
