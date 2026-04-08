# --- ИМПОРТ БИБЛИОТЕК ---
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
import platform
import psutil
import wmi            
import ctypes
import threading
import subprocess 
import re         
import os         
import sys
import csv 
import json
import multiprocessing
import time
import uuid
import hashlib
import io
import base64
import webview  
from datetime import datetime

# ПРЕДОХРАНИТЕЛЬ ДЛЯ СКРЫТОЙ КОНСОЛИ (чтобы --windowed режим не падал с ошибкой NoneType)
if sys.stdout is None: sys.stdout = open(os.devnull, 'w')
if sys.stderr is None: sys.stderr = open(os.devnull, 'w')

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# Настройка корректного масштабирования (DPI) для Windows
try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except: pass

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config():
    config_path = resource_path("config.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            "app_settings": {
                "window_title": "Техническая проверка личного оборудования",
                "company_target_text": "удаленной работы",
                "color_success": "#27ae60",
                "color_error": "#FC5055"
            },
            "hardware_limits": {
                "cpu_rec_label": "Рекомендованный минимальный CPU",
                "cpu_rec_name": "Intel Core i5-6400", "cpu_rec_score": 4200,
                "cpu_min_label": "Минимально допустимый CPU",
                "cpu_min_name": "Celeron N4020", "cpu_min_score": 957,
                "ram_rec_gb": 8, "ram_min_gb": 4, "os_required": "Windows 10 или 11"
            },
            "network_limits": { "ping_max_ms": 50.0, "dl_min_mbps": 20.0, "ul_min_mbps": 20.0 },
            "web_form": {
                "form_url": "https://example.com/your-form",
                "labels": {
                    "cpu": "Центральный процессор", "ram": "Оперативная память",
                    "os": "Операционная система", "ping": "Пинг",
                    "dl": "Входящая скорость интернета", "ul": "Исходящая скорость интернета",
                    "verdict": "Результат анализа", "improvements": "Что необходимо улучшить",
                    "hwid": "HWID", "fio": "ФИО"
                }
            },
            "spam_protection": { "enable_local_lock": True, "lock_timeout_hours": 24.0, "enable_hwid": True, "admin_password_hash": "" }
        }

# ==============================================================
# ИЗОЛИРОВАННЫЙ ПРОЦЕСС ДЛЯ БРАУЗЕРА (pywebview)
# ==============================================================
def run_browser(form_url, sys_data, labels, b64_img):
    class JS_Api:
        def __init__(self):
            self._window = None
        def set_window(self, w):
            self._window = w
        def close_app(self):
            if self._window:
                self._window.destroy()

    api = JS_Api()

    js_code = f"""
    setTimeout(function() {{
        // Уменьшаем масштаб страницы до 80%, чтобы все элементы влезли в экран без прокрутки
        document.body.style.zoom = "0.8";

        let tasks = [
            {{ label: "{labels.get('cpu', 'Центральный процессор')}", text: "{sys_data['cpu_raw']}" }},
            {{ label: "{labels.get('ram', 'Оперативная память')}", text: "{sys_data['ram']}" }},
            {{ label: "{labels.get('os', 'Операционная система')}", text: "{sys_data['os']}" }},
            {{ label: "{labels.get('ping', 'Пинг')}", text: "{sys_data['ping']}" }},
            {{ label: "{labels.get('dl', 'Входящая скорость интернета')}", text: "{sys_data['dl']}" }},
            {{ label: "{labels.get('ul', 'Исходящая скорость интернета')}", text: "{sys_data['ul']}" }},
            {{ label: "{labels.get('verdict', 'Результат анализа')}", text: "{sys_data['verdict']}" }},
            {{ label: "{labels.get('improvements', 'Что необходимо улучшить')}", text: "{sys_data['improvements']}" }},
            {{ label: "{labels.get('hwid', 'HWID')}", text: "{sys_data['hwid']}" }}
        ];
        
        let base64Data = "{b64_img}";

        function forceInjectCorrectData() {{
            let currentWrappers = document.querySelectorAll('div[data-test-id="formFieldBaseWrapper"]');
            tasks.forEach(task => {{
                if (task.text !== "-" && task.text !== "") {{
                    for (let w = 0; w < currentWrappers.length; w++) {{
                        let titleWrap = currentWrappers[w].querySelector('div[class*="titleWrapper"]');
                        if (titleWrap && titleWrap.innerText.includes(task.label)) {{
                            let el = currentWrappers[w].querySelector('input:not([type="hidden"]), textarea, div[contenteditable="true"]');
                            if (el) {{
                                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {{
                                    el.value = task.text;
                                }} else {{
                                    el.innerText = task.text;
                                }}
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                            }}
                            break;
                        }}
                    }}
                }}
            }});
        }}

        let i = 0;
        function processNext() {{
            if (i >= tasks.length) {{
                let wrappers = document.querySelectorAll('div[data-test-id="formFieldBaseWrapper"]');
                let fioLabel = "{labels.get('fio', 'ФИО')}".toLowerCase();
                for (let w = 0; w < wrappers.length; w++) {{
                    let titleWrap = wrappers[w].querySelector('div[class*="titleWrapper"]');
                    if (titleWrap && titleWrap.innerText.toLowerCase().includes(fioLabel)) {{
                        let el = wrappers[w].querySelector('input');
                        if (el) el.focus();
                        break;
                    }}
                }}

                let fileInput = document.querySelector('input[type="file"]');
                if (fileInput && base64Data && !fileInput.dataset.imgAttached) {{
                    try {{
                        let bstr = atob(base64Data);
                        let n = bstr.length;
                        let u8arr = new Uint8Array(n);
                        while(n--) {{ u8arr[n] = bstr.charCodeAt(n); }}
                        
                        let hwidName = "{sys_data['hwid']}";
                        let finalFileName = hwidName !== "-" ? hwidName + "_PC_Audit_Result.png" : "PC_Audit_Result.png";
                        
                        let file = new File([u8arr], finalFileName, {{type: 'image/png'}});
                        
                        let dt = new DataTransfer();
                        dt.items.add(file);
                        fileInput.files = dt.files;
                        fileInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        fileInput.dataset.imgAttached = "true";
                    }} catch(e) {{ console.log("File Attach Error", e); }}
                }}

                setInterval(() => {{
                    let saveBtn = document.querySelector('.pyrusExternalWebForm__saveButton');
                    if (saveBtn && !saveBtn.dataset.honeypotAttached) {{
                        saveBtn.addEventListener('mouseenter', forceInjectCorrectData, true);
                        saveBtn.addEventListener('mousedown', forceInjectCorrectData, true);
                        
                        saveBtn.addEventListener('click', () => {{
                            setTimeout(() => {{
                                let successCheck = setInterval(() => {{
                                    if (window.isClosing) return;
                                    let currentBtn = document.querySelector('.pyrusExternalWebForm__saveButton');
                                    if (!currentBtn || currentBtn.offsetParent === null) {{
                                        clearInterval(successCheck);
                                        window.isClosing = true;
                                        setTimeout(() => {{ 
                                            if (window.pywebview && window.pywebview.api) {{
                                                window.pywebview.api.close_app(); 
                                            }}
                                        }}, 2000);
                                    }}
                                }}, 1000);
                            }}, 1000);
                        }});
                        saveBtn.dataset.honeypotAttached = "true";
                    }}
                }}, 1000);

                return;
            }}

            let task = tasks[i];
            if (task.text !== "-" && task.text !== "") {{
                let wrappers = document.querySelectorAll('div[data-test-id="formFieldBaseWrapper"]');
                for (let w = 0; w < wrappers.length; w++) {{
                    let titleWrap = wrappers[w].querySelector('div[class*="titleWrapper"]');
                    if (titleWrap && titleWrap.innerText.includes(task.label)) {{
                        let el = wrappers[w].querySelector('input:not([type="hidden"]), textarea, div[contenteditable="true"]');
                        if (el) {{
                            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {{
                                el.value = task.text;
                            }} else {{
                                el.innerText = task.text;
                            }}
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        }}
                        break;
                    }}
                }}
            }}
            i++;
            setTimeout(processNext, 200); 
        }}
        
        processNext();
    }}, 3000);
    """

    # maximized=True заставит окно открываться сразу на весь экран
    window = webview.create_window("Отправка отчета", form_url, js_api=api, width=1024, height=768, maximized=True)
    api.set_window(window)
    
    def on_loaded(w):
        w.evaluate_js(js_code)
        
    webview.start(on_loaded, window)

# ==============================================================
# ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ
# ==============================================================
class TechCheckApp:
    def __init__(self, root):
        self.root = root
        
        self.config = load_config()
        self.cfg_app = self.config.get("app_settings", {})
        self.cfg_hw = self.config.get("hardware_limits", {})
        self.cfg_net = self.config.get("network_limits", {})
        self.cfg_spam = self.config.get("spam_protection", {})
        
        self.color_ok = self.cfg_app.get("color_success", "#27ae60")
        self.color_err = self.cfg_app.get("color_error", "#FC5055")
        self.target_text = self.cfg_app.get("company_target_text", "удаленной работы")
        
        self.spam_bypassed = False
        
        self.root.title(self.cfg_app.get("window_title", "Техническая проверка оборудования"))
        try: self.root.iconbitmap(resource_path("icon.ico"))
        except: pass 
        
        self.width = 800; self.height = 700
        self.center_window()
        
        self.cpu_db = {}
        self.load_cpu_database()
        
        try: self.w = wmi.WMI()
        except: self.w = None
            
        self.lbl_ping = None; self.lbl_dl = None; self.lbl_ul = None
        self.stage1_completed = False; self.stage2_completed = False
        self.pause_vpn_loop = False
        
        self.report_data = {
            'cpu_raw': '', 'cpu_score': '', 'cpu_color': 'black', 'cpu_bar': '', 
            'ram_user': '', 'ram_color': 'black', 'ram_bar': '', 
            'os_name': '', 'os_color': 'black',
            'kb_ic': '', 'kb_col': 'black', 'ms_ic': '', 'ms_col': 'black', 'au_ic': '', 'au_col': 'black',
            'gpu_name': '', 'resolution': '', 'c_drive': '', 'c_color': 'black', 
            'ping': 'Нет данных', 'ping_color': 'black', 'dl': 'Нет данных', 'dl_color': 'black', 'ul': 'Нет данных', 'ul_color': 'black',
            
            'cpu_raw_full': '', 'ram_raw_full': '', 'os_raw_full': ''
        }
        
        self.show_license()

    def center_window(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{self.width}x{self.height}+{(sw // 2) - (self.width // 2)}+{(sh // 2) - (self.height // 2)}")

    def show_license(self):
        self.lic_frame = tk.Frame(self.root)
        self.lic_frame.pack(expand=True, fill="both", padx=20, pady=20)
        tk.Label(self.lic_frame, text="ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ (EULA)", font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))
        
        eula_text = "Текст лицензионного соглашения не найден."
        eula_path = resource_path("eula.txt")
        if os.path.exists(eula_path):
            with open(eula_path, "r", encoding="utf-8") as f: eula_text = f.read()

        text_area = scrolledtext.ScrolledText(self.lic_frame, wrap=tk.WORD, font=("Segoe UI", 9))
        text_area.insert(tk.INSERT, eula_text)
        text_area.config(state=tk.DISABLED) 
        text_area.pack(expand=True, fill="both", pady=(0, 10))
        
        self.eula_accepted = tk.BooleanVar()
        tk.Checkbutton(self.lic_frame, text="Я подтверждаю, что ознакомлен с условиями обработки ПД", variable=self.eula_accepted, command=self.toggle_accept_btn, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 15))

        btn_frame = tk.Frame(self.lic_frame); btn_frame.pack(fill="x")
        self.btn_accept = tk.Button(btn_frame, text="ПРИНЯТЬ", bg=self.color_ok, fg="white", command=self.start_main_ui, font=("Segoe UI", 10, "bold"), pady=8, state="disabled")
        self.btn_accept.pack(side="left", expand=True, fill="x", padx=(0, 5))
        tk.Button(btn_frame, text="ОТКАЗАТЬСЯ", bg=self.color_err, fg="white", command=self.root.destroy, font=("Segoe UI", 10, "bold"), pady=8).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def toggle_accept_btn(self):
        self.btn_accept.config(state="normal" if self.eula_accepted.get() else "disabled")

    def start_main_ui(self):
        self.lic_frame.destroy()
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill="both", padx=15, pady=10)
        
        self.btn_frame = tk.Frame(self.main_frame); self.btn_frame.pack(fill="x", pady=2)
        self.btn_scan = tk.Button(self.btn_frame, text="1 этап - Проверка характеристик ПК", command=self.run_scan, font=("Segoe UI", 10, "bold"), bg=self.color_ok, fg="white", pady=5)
        self.btn_scan.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.btn_net = tk.Button(self.btn_frame, text="2 этап - Проверка скорости интернета", state="disabled", command=self.start_net_test_thread, font=("Segoe UI", 10, "bold"), bg="#3498db", fg="white", pady=5)
        self.btn_net.pack(side="right", fill="x", expand=True, padx=(2, 0))

        self.vpn_frame = tk.Frame(self.main_frame, relief="raised", bd=2, bg=self.root.cget("bg"))
        self.vpn_frame.pack(fill="x", pady=2)
        self.vpn_lbl1 = tk.Label(self.vpn_frame, text="", font=("Segoe UI", 9, "bold"), bg=self.root.cget("bg"))
        self.vpn_lbl1.pack()
        self.vpn_lbl2 = tk.Label(self.vpn_frame, text="", font=("Segoe UI", 8), bg=self.root.cget("bg"))
        self.vpn_lbl2.pack()

        self.text_frame = tk.Frame(self.main_frame); self.text_frame.pack(pady=2, fill="both", expand=True)
        self.scrollbar = tk.Scrollbar(self.text_frame); self.scrollbar.pack(side="right", fill="y")
        self.result_box = tk.Text(self.text_frame, wrap=tk.WORD, font=("Consolas", 9), bg="#f2f2f2", padx=5, pady=5, yscrollcommand=self.scrollbar.set)
        self.result_box.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.result_box.yview); self.result_box.config(state="disabled") 
        
        self.btn_submit_main = tk.Button(self.main_frame, text="3 этап - ПРОВЕСТИ АНАЛИЗ СОБРАННЫХ ДАННЫХ", command=self.open_verdict_window, state="disabled", font=("Segoe UI", 10, "bold"), bg=self.color_err, fg="white", pady=5)
        self.btn_submit_main.pack(fill="x", pady=2)
        
        self.result_box.tag_config("red", foreground=self.color_err)
        self.result_box.tag_config("green", foreground=self.color_ok)
        self.result_box.tag_config("orange", foreground="#f39c12")
        self.result_box.tag_config("bold", font=("Consolas", 9, "bold"))
        self.result_box.tag_config("center_header", font=("Consolas", 11, "bold"), justify="center")
        self.result_box.tag_config("warning_red", font=("Consolas", 10, "bold"), foreground=self.color_err, justify="center")
        self.result_box.tag_config("center_table", justify="center")
        self.result_box.tag_config("dark_blue_center", foreground="#000080", justify="center", font=("Consolas", 9, "bold"))
        
        self.check_vpn_loop()

    # --- БЛОК ПРОКРУТКИ МЫШЬЮ ---
    def _on_mousewheel(self, event):
        """Перехватывает колесико мыши и крутит главный ползунок Text-виджета"""
        self.result_box.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_tree(self, widget):
        """Рекурсивно привязывает скролл ко всем вложенным элементам (таблицам и тексту)"""
        for child in widget.winfo_children():
            child.bind("<MouseWheel>", self._on_mousewheel)
            self.bind_tree(child)
    # -----------------------------

    def check_submit_state(self):
        if self.stage1_completed and self.stage2_completed: self.btn_submit_main.config(state="normal")

    def check_vpn_loop(self):
        if self.pause_vpn_loop:
            self.root.after(1000, self.check_vpn_loop); return
        vpn_found = False; vpn_name = ""
        for iface, stats in psutil.net_if_stats().items():
            if stats.isup and any(x in iface.lower() for x in ["vpn", "tap", "tun", "adguard", "zerotier"]):
                vpn_found = True; vpn_name = iface; break
                
        if vpn_found:
            self.vpn_lbl1.config(text=f"ВНИМАНИЕ: АКТИВЕН VPN ({vpn_name})", fg=self.color_err)
            self.vpn_lbl2.config(text="Для точного теста отключите VPN (кнопка разблокируется автоматически)", fg="black")
            self.btn_net.config(state="disabled")
        else:
            self.vpn_lbl1.config(text="Активный VPN не обнаружен.", fg="black")
            self.vpn_lbl2.config(text="После проверки характеристик ПК нажмите кнопку проверки скорости интернета", fg="black")
            self.btn_net.config(state="normal" if self.stage1_completed else "disabled")
        self.root.after(1000, self.check_vpn_loop)

    def log(self, text, tag=None):
        is_disabled = self.result_box.cget("state") == "disabled"
        if is_disabled: self.result_box.config(state="normal")
        self.result_box.insert(tk.END, text + "\n", tag)
        self.result_box.see(tk.END)
        if is_disabled: self.result_box.config(state="disabled")

    def clean_cpu_string(self, name):
        name = str(name).upper()
        for tm in ['(R)', '(TM)', ' CPU', ' APU', ' PROCESSOR']: name = name.replace(tm, '')
        name = re.sub(r'\d+-CORE', '', name); name = re.sub(r'[A-Z]+-CORE', '', name) 
        name = re.sub(r'\s*@\s*\d+(\.\d+)?\s*[GgMm][Hh][Zz]', '', name); name = re.sub(r'\s*WITH\s+.*', '', name)
        return re.sub(r'\s+', ' ', name).strip()

    def load_cpu_database(self):
        db_path = resource_path("cpu_data.csv")
        if os.path.exists(db_path):
            try:
                with open(db_path, mode='r', encoding='utf-8', errors='ignore') as f:
                    for row in csv.reader(f):
                        if len(row) >= 2:
                            try: self.cpu_db[self.clean_cpu_string(row[0])] = float(row[1])
                            except: pass
            except: pass

    def create_table_frame(self, parent=None):
        return tk.Frame(parent or self.result_box, bg="#A6A6A6")

    def create_cell(self, frame, row, col, text, fg_color="black", font_weight="bold", align="w", font_family="Segoe UI", colspan=1):
        lbl = tk.Label(frame, text=text, fg=fg_color, bg="white", font=(font_family, 9, font_weight), anchor=align, padx=5, pady=2)
        lbl.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=1, pady=1) 
        return lbl

    # ==============================================================
    # 1 ЭТАП: ПРОВЕРКА АППАРАТНЫХ ХАРАКТЕРИСТИК (ЖЕЛЕЗА)
    # ==============================================================
    def run_scan(self):
        self.result_box.config(state="normal"); self.result_box.delete('1.0', tk.END); self.log("")
        
        # --- CPU ---
        try:
            cpu_obj = self.w.Win32_Processor()[0]; raw_cpu_name = cpu_obj.Name.strip()
            cores = psutil.cpu_count(logical=False); clock_mhz = int(cpu_obj.MaxClockSpeed) if cpu_obj.MaxClockSpeed else 0
            search_name = self.clean_cpu_string(raw_cpu_name)
            min_score_int = self.cfg_hw.get("cpu_min_score", 957); rec_score_int = self.cfg_hw.get("cpu_rec_score", 4200)
            
            user_score_int = int(self.cpu_db.get(search_name, 0))
            if user_score_int == 0:
                best_match = ""
                for db_name, score in self.cpu_db.items():
                    if db_name in search_name and len(db_name) > len(best_match):
                        best_match = db_name; user_score_int = int(score)
            
            color_tag = self.color_ok if user_score_int >= min_score_int else (self.color_err if user_score_int > 0 else "#f39c12")
            BAR_WIDTH = 25; max_val = max(user_score_int, rec_score_int, min_score_int)
            user_bar_text = "█" * max(1, int((user_score_int / max_val) * BAR_WIDTH)) if user_score_int > 0 else "?" * BAR_WIDTH
            
            cpu_full_hdr = f"{raw_cpu_name} ({cores} ядер) {clock_mhz} Mhz"
            self.report_data.update({'cpu_raw': raw_cpu_name, 'cpu_score': str(user_score_int) if user_score_int > 0 else "Нет в базе", 'cpu_color': color_tag, 'cpu_bar': user_bar_text, 'cpu_raw_full': cpu_full_hdr})
            self.result_box.insert(tk.END, f"Ваш процессор (CPU): {cpu_full_hdr}\n", "dark_blue_center")

            t_cpu = self.create_table_frame()
            self.create_cell(t_cpu, 0, 0, f"Ваш CPU - {raw_cpu_name}", align="e")
            self.create_cell(t_cpu, 0, 1, self.report_data['cpu_score'], fg_color=color_tag, align="center")
            self.create_cell(t_cpu, 0, 2, user_bar_text, fg_color=color_tag, align="w", font_family="Consolas")
            self.create_cell(t_cpu, 1, 0, f"{self.cfg_hw.get('cpu_rec_label', 'Рекомендуемый CPU')} ≥ {self.cfg_hw.get('cpu_rec_name', '')}", align="e")
            self.create_cell(t_cpu, 1, 1, str(rec_score_int), fg_color=self.color_ok, align="center")
            self.create_cell(t_cpu, 1, 2, "█" * max(1, int((rec_score_int / max_val) * BAR_WIDTH)), fg_color=self.color_ok, align="w", font_family="Consolas")
            self.create_cell(t_cpu, 2, 0, f"{self.cfg_hw.get('cpu_min_label', 'Минимальный CPU')} - {self.cfg_hw.get('cpu_min_name', '')}", align="e")
            self.create_cell(t_cpu, 2, 1, str(min_score_int), fg_color="#f39c12", align="center")
            self.create_cell(t_cpu, 2, 2, "█" * max(1, int((min_score_int / max_val) * BAR_WIDTH)), fg_color="#f39c12", align="w", font_family="Consolas")
            tk.Frame(t_cpu, width=740, height=0, bg="#A6A6A6").grid(row=3, column=0, columnspan=3); t_cpu.columnconfigure(0, weight=1) 
            self.result_box.window_create(tk.END, window=t_cpu); self.result_box.tag_add("center_table", self.result_box.index("end-1c"), "end")
            self.result_box.insert(tk.END, "\n\n") 
        except: pass

        # --- RAM ---
        try:
            ram_gb = round(psutil.virtual_memory().total / (1024**3))
            sticks = self.w.Win32_PhysicalMemory()
            m_type = {20:"DDR", 21:"DDR2", 24:"DDR3", 26:"DDR4", 30:"DDR5"}.get(int(sticks[0].SMBIOSMemoryType), "RAM") if sticks else "RAM"
            m_speed = f"{sticks[0].Speed} MHz" if sticks else ""
            
            rec_ram, min_ram = self.cfg_hw.get("ram_rec_gb", 8), self.cfg_hw.get("ram_min_gb", 4)
            ram_col = self.color_err if ram_gb < min_ram else ("#f39c12" if ram_gb < rec_ram else self.color_ok)
            max_ram_val = max(ram_gb, rec_ram, min_ram)
            
            ram_full_hdr = f"{ram_gb} Гб {m_type} ({m_speed})"
            self.report_data.update({'ram_user': f"{ram_gb} Гб", 'ram_color': ram_col, 'ram_raw_full': ram_full_hdr})
            self.result_box.insert(tk.END, f"Оперативная память: {ram_full_hdr}\n", "dark_blue_center")
            
            t_ram = self.create_table_frame()
            self.create_cell(t_ram, 0, 0, "Ваше кол-во ОЗУ", align="e")
            self.create_cell(t_ram, 0, 1, f"{ram_gb} Гб", fg_color=ram_col, align="center")
            self.create_cell(t_ram, 0, 2, "█" * max(1, int((ram_gb / max_ram_val) * BAR_WIDTH)), fg_color=ram_col, align="w", font_family="Consolas")
            self.create_cell(t_ram, 1, 0, "Рекомендуемое минимальное кол-во ОЗУ", align="e")
            self.create_cell(t_ram, 1, 1, f"{rec_ram} Гб", fg_color=self.color_ok, align="center")
            self.create_cell(t_ram, 1, 2, "█" * max(1, int((rec_ram / max_ram_val) * BAR_WIDTH)), fg_color=self.color_ok, align="w", font_family="Consolas")
            self.create_cell(t_ram, 2, 0, "Минимально допустимое кол-во ОЗУ", align="e")
            self.create_cell(t_ram, 2, 1, f"{min_ram} Гб", fg_color="#f39c12", align="center")
            self.create_cell(t_ram, 2, 2, "█" * max(1, int((min_ram / max_ram_val) * BAR_WIDTH)), fg_color="#f39c12", align="w", font_family="Consolas")
            tk.Frame(t_ram, width=740, height=0, bg="#A6A6A6").grid(row=3, column=0, columnspan=3); t_ram.columnconfigure(0, weight=1) 
            self.result_box.window_create(tk.END, window=t_ram); self.result_box.tag_add("center_table", self.result_box.index("end-1c"), "end")
            self.result_box.insert(tk.END, "\n\n")
        except: pass

        # --- OS ---
        try:
            os_wmi = self.w.Win32_OperatingSystem()[0]
            clean_os_name = os_wmi.Caption.replace("Microsoft ", "").replace("Майкрософт ", "").strip()
            req_os = self.cfg_hw.get("os_required", "Windows 10 или 11")
            allowed = re.findall(r'\d+(?:\.\d+)?', req_os)
            os_ok = any(ver in clean_os_name for ver in allowed) if allowed else ("10" in clean_os_name or "11" in clean_os_name)
            os_col = self.color_ok if os_ok else self.color_err

            os_full_hdr = f"Microsoft {clean_os_name} ({'64' if '64' in os_wmi.OSArchitecture else '32'} разрядная) сборка: {os_wmi.Version}"
            self.report_data.update({'os_name': clean_os_name, 'os_color': os_col, 'os_raw_full': os_full_hdr})
            self.result_box.insert(tk.END, f"ОС: {os_full_hdr}\n", "dark_blue_center")

            t_os = self.create_table_frame()
            self.create_cell(t_os, 0, 0, "Ваша ОС:", align="e")
            self.create_cell(t_os, 0, 1, clean_os_name, fg_color=os_col, align="center")
            self.create_cell(t_os, 0, 2, "✔" if os_ok else "✖", fg_color=os_col, align="center", font_family="Consolas")
            self.create_cell(t_os, 1, 0, "Обязательная ОС:", align="e")
            self.create_cell(t_os, 1, 1, req_os, fg_color=self.color_ok, align="center")
            self.create_cell(t_os, 1, 2, "✔", fg_color=self.color_ok, align="center", font_family="Consolas")
            tk.Frame(t_os, width=740, height=0, bg="#A6A6A6").grid(row=2, column=0, columnspan=3); t_os.columnconfigure(0, weight=1); t_os.columnconfigure(2, minsize=40) 
            self.result_box.window_create(tk.END, window=t_os); self.result_box.tag_add("center_table", self.result_box.index("end-1c"), "end")
            self.result_box.insert(tk.END, "\n\n")
        except: pass

        # --- Peripherals ---
        try:
            get_ic = lambda state: ("✔", self.color_ok) if state else ("✖", self.color_err)
            kb_ic, kb_col = get_ic(len(self.w.Win32_Keyboard()) > 0)
            ms_ic, ms_col = get_ic(len(self.w.Win32_PointingDevice()) > 0)
            au_ic, au_col = get_ic(len(self.w.Win32_SoundDevice()) > 0)
            
            self.report_data.update({'kb_ic': kb_ic, 'kb_col': kb_col, 'ms_ic': ms_ic, 'ms_col': ms_col, 'au_ic': au_ic, 'au_col': au_col})

            t_periph = self.create_table_frame()
            self.create_cell(t_periph, 0, 0, "Клавиатура:", align="e")
            self.create_cell(t_periph, 0, 1, kb_ic, fg_color=kb_col, align="center", font_family="Consolas")
            self.create_cell(t_periph, 1, 0, "Мышь:", align="e")
            self.create_cell(t_periph, 1, 1, ms_ic, fg_color=ms_col, align="center", font_family="Consolas")
            self.create_cell(t_periph, 2, 0, "Аудиоустройство:", align="e")
            self.create_cell(t_periph, 2, 1, au_ic, fg_color=au_col, align="center", font_family="Consolas")
            tk.Label(t_periph, text="АУДИОГАРНИТУРА НЕОБХОДИМА ТОЛЬКО ПРОВОДНАЯ. BLUETOOTH ГАРНИТУРА НЕ ПОДДЕРЖИВАЕТСЯ", fg=self.color_err, bg="white", font=("Segoe UI", 8, "bold"), pady=2).grid(row=3, column=0, columnspan=2, sticky="nsew", padx=1, pady=1)

            tk.Frame(t_periph, width=740, height=0, bg="#A6A6A6").grid(row=4, column=0, columnspan=2); t_periph.columnconfigure(0, weight=1); t_periph.columnconfigure(1, minsize=60) 
            self.result_box.window_create(tk.END, window=t_periph); self.result_box.tag_add("center_table", self.result_box.index("end-1c"), "end")
            self.result_box.insert(tk.END, "\n\n")
        except: pass

        # --- GPU & Disk (УМНАЯ ПРОВЕРКА SSD) ---
        try:
            gpu_name = "Не найдена"
            try:
                gpus = self.w.Win32_VideoController()
                if gpus:
                    gpu_name = gpus[0].Caption
                    for g in gpus:
                        if any(x in g.Caption.lower() for x in ["nvidia", "amd", "radeon", "geforce", "rtx", "gtx", "rx"]):
                            gpu_name = g.Caption; break
            except: pass

            res_w, res_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            c_drive_str = "Не найден"; c_is_low = False
            try:
                c_model = "Неизвестный диск"; c_media = "HDD"
                
                # 1. Узнаем логическое имя диска
                for p in self.w.Win32_DiskPartition():
                    for l in p.associators("Win32_LogicalDiskToPartition"):
                        if l.DeviceID == "C:":
                            for d in p.associators("Win32_DiskDriveToDiskPartition"):
                                c_model = d.Model
                                break
                                
                # 2. Продвинутая проверка через родной Storage API Windows
                try:
                    wmi_storage = wmi.WMI(namespace=r"root\Microsoft\Windows\Storage")
                    for pd in wmi_storage.MSFT_PhysicalDisk():
                        if pd.Model and str(pd.Model).strip() in c_model:
                            if pd.MediaType == 4:
                                c_media = "SSD"
                            elif pd.MediaType == 3:
                                c_media = "HDD"
                            break
                except: pass
                
                # 3. Резервная проверка по словарю
                if c_media == "HDD":
                    ssd_kws = ["ssd", "nvme", "legend", "evo", "pro", "adata", "xpg", "apacer", "kingston", "samsung", "crucial", "wd", "corsair", "m.2", "silicon power", "netac", "gigabyte", "solid state"]
                    if any(k in c_model.lower() for k in ssd_kws):
                        c_media = "SSD"

                usage = psutil.disk_usage("C:\\")
                c_drive_str = f"{c_model} [{c_media}] ({round(usage.total / (1024**3))}Гб | свободно {round(usage.free / (1024**3), 1)} Гб)"
                c_is_low = (usage.free / usage.total) * 100 < 20
            except: pass

            c_disk_color = self.color_err if c_is_low else "black"
            self.report_data.update({'gpu_name': gpu_name, 'resolution': f"{res_w}x{res_h}", 'c_drive': c_drive_str, 'c_color': c_disk_color})

            t_m = self.create_table_frame()
            self.create_cell(t_m, 0, 0, "Видеокарта:", align="e")
            self.create_cell(t_m, 0, 1, gpu_name, align="w")
            self.create_cell(t_m, 1, 0, "Разрешение экрана:", align="e")
            self.create_cell(t_m, 1, 1, f"{res_w}x{res_h}", align="w")
            self.create_cell(t_m, 2, 0, "Диск C:", align="e")
            self.create_cell(t_m, 2, 1, c_drive_str, fg_color=c_disk_color, align="w")

            tk.Frame(t_m, width=740, height=0, bg="#A6A6A6").grid(row=3, column=0, columnspan=2); t_m.columnconfigure(0, weight=1); t_m.columnconfigure(1, weight=1) 
            self.result_box.window_create(tk.END, window=t_m); self.result_box.tag_add("center_table", self.result_box.index("end-1c"), "end"); self.result_box.insert(tk.END, "\n")
            if c_is_low: self.result_box.insert(tk.END, "ОБНАРУЖЕНО МАЛО СВОБОДНОГО МЕСТА НА ДИСКЕ C:\nРЕКОМЕНДОВАНО БОЛЬШЕ 20%\n", "warning_red")
            self.result_box.insert(tk.END, "\n")
        except: pass

        t_net = self.create_table_frame()
        self.create_cell(t_net, 0, 0, "Пинг:", align="e"); self.lbl_ping = self.create_cell(t_net, 0, 1, "Ожидание...", align="w", fg_color="gray")
        self.create_cell(t_net, 1, 0, "Входящая скорость:", align="e"); self.lbl_dl = self.create_cell(t_net, 1, 1, "Ожидание...", align="w", fg_color="gray")
        self.create_cell(t_net, 2, 0, "Исходящая скорость:", align="e"); self.lbl_ul = self.create_cell(t_net, 2, 1, "Ожидание...", align="w", fg_color="gray")
        tk.Frame(t_net, width=740, height=0, bg="#A6A6A6").grid(row=3, column=0, columnspan=2); t_net.columnconfigure(0, weight=1); t_net.columnconfigure(1, weight=1) 
        self.result_box.window_create(tk.END, window=t_net); self.result_box.tag_add("center_table", self.result_box.index("end-1c"), "end"); self.result_box.insert(tk.END, "\n")
        
        # --- ФИКС ПРОКРУТКИ: ПРИВЯЗЫВАЕМ КОЛЕСИКО МЫШИ КО ВСЕМ ТАБЛИЦАМ ---
        self.bind_tree(self.result_box)
        # ------------------------------------------------------------------

        self.stage1_completed = True
        self.check_submit_state()
        self.result_box.config(state="disabled")

    # ==============================================================
    # 2 ЭТАП: ПРОВЕРКА ИНТЕРНЕТА
    # ==============================================================
    def start_net_test_thread(self):
        self.btn_net.config(state="disabled", text="Тестирование через QMS...")
        if self.lbl_ping: self.lbl_ping.config(text="Тестирование...", fg="orange")
        if self.lbl_dl: self.lbl_dl.config(text="Тестирование...", fg="orange")
        if self.lbl_ul: self.lbl_ul.config(text="Тестирование...", fg="orange")
        threading.Thread(target=self.run_internet_test, daemon=True).start()

    def run_internet_test(self):
        qms_path = resource_path("qms_lib.exe")
        if not os.path.exists(qms_path):
            if self.lbl_ping: self.lbl_ping.config(text="Ошибка: Нет файла qms_lib.exe", fg=self.color_err)
            self.btn_net.config(state="normal", text="2 этап - Проверка скорости интернета")
            self.stage2_completed = True; self.check_submit_state(); return

        try:
            proc = subprocess.run([qms_path, "-P"], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=120, creationflags=0x08000000)
            out = proc.stdout + proc.stderr
            m_ping = re.search(r"Idle Latency:\s*([\d.]+)\s*ms", out, re.IGNORECASE)
            m_dl = re.search(r"Download:\s*([\d.]+)\s*Mbit/s", out, re.IGNORECASE)
            m_ul = re.search(r"Upload:\s*([\d.]+)\s*Mbit/s", out, re.IGNORECASE)

            if m_ping and m_dl and m_ul:
                p, d, u = float(m_ping.group(1)), float(m_dl.group(1)), float(m_ul.group(1))
                l_p, l_d, l_u = self.cfg_net.get("ping_max_ms", 50.0), self.cfg_net.get("dl_min_mbps", 20.0), self.cfg_net.get("ul_min_mbps", 20.0)
                
                col_p = self.color_ok if p <= l_p else self.color_err
                col_d = self.color_ok if d >= l_d else self.color_err
                col_u = self.color_ok if u >= l_u else self.color_err
                
                self.report_data.update({'ping': f"{p} мс", 'dl': f"{d} Мбит/сек", 'ul': f"{u} Мбит/сек", 'ping_color': col_p, 'dl_color': col_d, 'ul_color': col_u})
                if self.lbl_ping: self.lbl_ping.config(text=self.report_data['ping'], fg=col_p)
                if self.lbl_dl: self.lbl_dl.config(text=self.report_data['dl'], fg=col_d)
                if self.lbl_ul: self.lbl_ul.config(text=self.report_data['ul'], fg=col_u)
            else:
                self.report_data['ping'] = "Ошибка парсинга"
                if self.lbl_ping: self.lbl_ping.config(text="Ошибка парсинга", fg=self.color_err)
        except Exception as e:
            self.report_data['ping'] = f"Сбой: {e}"
            if self.lbl_ping: self.lbl_ping.config(text=f"Сбой", fg=self.color_err)

        self.btn_net.config(state="normal", text="2 этап - Проверка скорости интернета")
        self.stage2_completed = True; self.check_submit_state()

    # ==============================================================
    # 3 ЭТАП: ФИНАЛЬНЫЙ ВЕРДИКТ
    # ==============================================================
    def open_verdict_window(self):
        self.pause_vpn_loop = True
        self.root.attributes('-disabled', True) 
        
        self.verdict_win = tk.Toplevel(self.root)
        self.verdict_win.transient(self.root); self.verdict_win.title("Вердикт тестирования")
        self.verdict_win.protocol("WM_DELETE_WINDOW", lambda: self.close_window(self.verdict_win))
        
        rw, rh = 800, 700; sw, sh = self.verdict_win.winfo_screenwidth(), self.verdict_win.winfo_screenheight()
        self.verdict_win.geometry(f"{rw}x{rh}+{(sw // 2) - (rw // 2)}+{(sh // 2) - (rh // 2)}")
        self.verdict_win.grab_set(); self.verdict_win.focus_set()
        try: self.verdict_win.iconbitmap(resource_path("icon.ico"))
        except: pass 
        
        d = self.report_data; improvements = []

        try: cpu_score = int(d.get('cpu_score', 0))
        except: cpu_score = 0
        cpu_ok = cpu_score >= self.cfg_hw.get("cpu_min_score", 957)
        if not cpu_ok: improvements.append("Процессор (CPU)")

        try: ram_val = float(re.search(r'\d+', d.get('ram_user', '0')).group())
        except: ram_val = 0
        ram_ok = ram_val >= self.cfg_hw.get("ram_min_gb", 4)
        if not ram_ok: improvements.append("Оперативная память (RAM)")

        os_name = d.get('os_name', '')
        req_os = self.cfg_hw.get("os_required", "Windows 10 или 11")
        allowed = re.findall(r'\d+(?:\.\d+)?', req_os)
        os_ok = any(ver in os_name for ver in allowed) if allowed else ("10" in os_name or "11" in os_name)
        if not os_ok: improvements.append(f"Операционная система (нужна {req_os})")

        ping_limit = self.cfg_net.get("ping_max_ms", 50.0)
        try: ping_val = float(re.search(r'[\d.]+', d.get('ping', '999')).group())
        except: ping_val = 999
        ping_ok = ping_val <= ping_limit
        if not ping_ok: improvements.append("Пинг сети (задержка)")

        dl_limit = self.cfg_net.get("dl_min_mbps", 20.0)
        try: dl_val = float(re.search(r'[\d.]+', d.get('dl', '0')).group())
        except: dl_val = 0
        dl_ok = dl_val >= dl_limit
        if not dl_ok: improvements.append("Входящая скорость интернета")

        ul_limit = self.cfg_net.get("ul_min_mbps", 20.0)
        try: ul_val = float(re.search(r'[\d.]+', d.get('ul', '0')).group())
        except: ul_val = 0
        ul_ok = ul_val >= ul_limit
        if not ul_ok: improvements.append("Исходящая скорость интернета")

        container = tk.Frame(self.verdict_win, padx=20, pady=20); container.pack(fill="both", expand=True)
        t_f = tk.Frame(container, bg="#A6A6A6"); t_f.pack(fill="x", expand=False)
        t_f.columnconfigure(0, weight=1, uniform="col"); t_f.columnconfigure(1, weight=1, uniform="col")

        def add_row(r, lbl, val, ok, err_msg):
            tk.Label(t_f, text=lbl, font=("Segoe UI", 10, "bold"), bg="white", anchor="e", justify="right", padx=5).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)
            tk.Label(t_f, text=val, font=("Segoe UI", 10, "bold"), bg="white", anchor="w", justify="left", padx=5).grid(row=r, column=1, sticky="nsew", padx=1, pady=1)
            msg = f"подходит для {self.target_text}" if ok else err_msg
            tk.Label(t_f, text=msg, fg=self.color_ok if ok else self.color_err, font=("Segoe UI", 10, "bold"), bg="white", anchor="center").grid(row=r+1, column=0, columnspan=2, sticky="nsew", padx=1, pady=1)
            return r + 2

        r = 0
        tk.Label(t_f, text="АНАЛИЗ ХАРАКТЕРИСТИК ВАШЕГО КОМПЬЮТЕРА", font=("Segoe UI", 11, "bold"), bg="white").grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1); r+=1
        r = add_row(r, "Ваш процессор:", d.get('cpu_raw', 'Неизвестно'), cpu_ok, f"не подходит для {self.target_text}")
        r = add_row(r, "Ваше кол-во ОЗУ:", d.get('ram_user', 'Неизвестно'), ram_ok, f"меньше необходимого для {self.target_text}")
        r = add_row(r, "Ваша ОС:", os_name, os_ok, f"не подходит для {self.target_text}")
        tk.Label(t_f, text="", bg="white").grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1); r+=1

        tk.Label(t_f, text="АНАЛИЗ ХАРАКТЕРИСТИК ВАШЕЙ СЕТИ ИНТЕРНЕТ", font=("Segoe UI", 11, "bold"), bg="white").grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1); r+=1
        r = add_row(r, "Ваш пинг:", d.get('ping', 'Неизвестно'), ping_ok, f"выше требуемого, необходим {ping_limit} и менее")
        r = add_row(r, "Входящая скорость:", d.get('dl', 'Неизвестно'), dl_ok, f"ниже требуемой, необходима {dl_limit} или выше")
        r = add_row(r, "Исходящая скорость:", d.get('ul', 'Неизвестно'), ul_ok, f"ниже требуемой, необходима {ul_limit} или выше")
        tk.Label(t_f, text="", bg="white").grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1); r+=1

        tk.Label(t_f, text="РЕЗУЛЬТАТ ТЕСТОВ", font=("Segoe UI", 11, "bold"), bg="white").grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1); r+=1

        all_ok = all([cpu_ok, ram_ok, os_ok, ping_ok, dl_ok, ul_ok])
        
        if all_ok:
            self.verdict_msg = "ОБОРУДОВАНИЕ ПОДХОДИТ"
            tk.Label(t_f, text=f"ВАШЕ ОБОРУДОВАНИЕ ПОЛНОСТЬЮ ПОДХОДИТ ДЛЯ {self.target_text.upper()}", fg="white", bg=self.color_ok, font=("Segoe UI", 13, "bold"), pady=10).grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1)
        else:
            self.verdict_msg = "ТРЕБУЕТ УЛУЧШЕНИЯ"
            tk.Label(t_f, text="ВАШЕ ОБОРУДОВАНИЕ ИЛИ ИНТЕРНЕТ ТРЕБУЕТ УЛУЧШЕНИЯ", fg="white", bg=self.color_err, font=("Segoe UI", 13, "bold"), pady=10).grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1); r+=1
            tk.Label(t_f, text=f"Требует улучшения: {', '.join(improvements)}", fg=self.color_err, font=("Segoe UI", 10, "bold"), bg="white", pady=5, wraplength=750, justify="center").grid(row=r, column=0, columnspan=2, sticky="nsew", padx=1, pady=1)

        btn_send = tk.Button(container, text="ОТПРАВИТЬ ОТЧЁТ", command=lambda: self.launch_browser(improvements), font=("Segoe UI", 11, "bold"), bg=self.color_err, fg="white", pady=10)
        btn_send.pack(fill="x", pady=(20, 5))

        self.info_label = tk.Label(container, text="- При отправке отчёта откроется окно формы, где БЕЗ ОШИБОК заполните ФИО, после чего нажмите Отправить.", font=("Segoe UI", 9, "bold"), fg=self.color_err, wraplength=750)
        self.info_label.pack(fill="x", pady=(0, 10))

        self.animate_info_label()

        try:
            fly_path = resource_path("fly.png")
            if HAS_PILLOW and os.path.exists(fly_path):
                fly_img = Image.open(fly_path).resize((30, 30), Image.LANCZOS)
                self.fly_photo = ImageTk.PhotoImage(fly_img)
                self.fly_lbl = tk.Label(self.verdict_win, image=self.fly_photo, cursor="hand2")
                self.fly_lbl.place(x=10, y=rh-40) 
                
                self.fly_lbl.bind("<Button-1>", self.on_fly_single_click)
                self.fly_lbl.bind("<Triple-Button-1>", self.prompt_password)
        except Exception as e:
            pass 

    def on_fly_single_click(self, event):
        if getattr(self, 'spam_bypassed', False):
            self.spam_bypassed = False
            messagebox.showinfo("Антиспам", "Антиспам защита СНОВА ВКЛЮЧЕНА.")

    def prompt_password(self, event):
        if getattr(self, 'spam_bypassed', False): return 
        pwd_win = tk.Toplevel(self.verdict_win)
        pwd_win.title("Доступ")
        pwd_win.geometry("250x120")
        pwd_win.transient(self.verdict_win); pwd_win.grab_set()
        sw, sh = pwd_win.winfo_screenwidth(), pwd_win.winfo_screenheight()
        pwd_win.geometry(f"+{(sw // 2) - 125}+{(sh // 2) - 60}")
        
        tk.Label(pwd_win, text="Введите пароль:").pack(pady=10)
        ent = tk.Entry(pwd_win, show="*", width=20); ent.pack(pady=5); ent.focus()
        
        def check_pwd(e=None):
            pwd = ent.get()
            h = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
            saved_hash = self.cfg_spam.get("admin_password_hash", "")
            
            if saved_hash and h == saved_hash:
                self.spam_bypassed = True
                messagebox.showinfo("Антиспам", "Пароль верный.\nАнтиспам защита ОТКЛЮЧЕНА для этого сеанса.")
                pwd_win.destroy()
            else:
                messagebox.showerror("Ошибка", "Неверный пароль!")
                pwd_win.destroy()
                
        pwd_win.bind("<Return>", check_pwd)
        tk.Button(pwd_win, text="ОК", command=check_pwd, width=10).pack(pady=5)

    def animate_info_label(self):
        if not hasattr(self, 'verdict_win') or not self.verdict_win.winfo_exists(): return
        self.info_label.config(fg="#A6A6A6" if self.info_label.cget("fg") == self.color_err else self.color_err)
        self.verdict_win.after(800, self.animate_info_label)

    def close_window(self, win):
        self.pause_vpn_loop = False
        self.root.attributes('-disabled', False)
        win.destroy()

    def generate_hwid(self):
        mac = str(uuid.getnode())
        raw_str = f"{self.report_data.get('cpu_raw','')}_{self.report_data.get('ram_user','')}_{mac}"
        return hashlib.md5(raw_str.encode()).hexdigest()[:8].upper()

    def check_and_set_spam_lock(self):
        if getattr(self, 'spam_bypassed', False): return True 
        if not self.cfg_spam.get("enable_local_lock", True): return True

        timeout_hours = float(self.cfg_spam.get("lock_timeout_hours", 24.0))
        temp_dir = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', '.'))
        lock_file = os.path.join(temp_dir, 'techcheck_lock.dat')

        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f: last_time = float(f.read().strip())
                if time.time() - last_time < timeout_hours * 3600: return False
            except: pass
            
        try:
            with open(lock_file, 'w') as f: f.write(str(time.time()))
        except: pass
        return True

    # --- ФУНКЦИЯ-РЕНДЕРЕР: РИСУЕТ ИДЕАЛЬНУЮ ТАБЛИЦУ ДЛЯ ПАЙРУСА ---
    def create_replica_image(self, d, verdict_text, hwid_text):
        # Делаем холст огромным с запасом (1000px), чтобы в конце обрезать без черных полос
        W, H = 760, 1000 
        img = Image.new('RGB', (W, H), color='#f2f2f2')
        draw = ImageDraw.Draw(img)

        try:
            f_norm = ImageFont.truetype("segoeui.ttf", 12)
            f_bold = ImageFont.truetype("segoeuib.ttf", 12)
            f_blue = ImageFont.truetype("consola.ttf", 13)
        except:
            f_norm = f_bold = f_blue = ImageFont.load_default()

        y = 10
        margin = 10

        def center_text(text, font, y_pos, fill):
            bbox = draw.textbbox((0,0), text, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2, y_pos), text, fill=fill, font=font)
            return y_pos + 22

        def draw_grid_row(x, y, widths, texts, fonts, colors, aligns, row_h=24, bg="white", bar_pct=None):
            curr_x = x
            for i in range(len(widths)):
                w = widths[i]
                draw.rectangle([curr_x, y, curr_x + w, y + row_h], fill=bg, outline="#A6A6A6")
                text = str(texts[i])
                
                # Векторная отрисовка галочек и крестиков
                if text == "✔":
                    cx, cy = curr_x + w//2, y + row_h//2
                    draw.line([(cx-4, cy), (cx-1, cy+4), (cx+5, cy-5)], fill=colors[i], width=2)
                elif text == "✖":
                    cx, cy = curr_x + w//2, y + row_h//2
                    draw.line([(cx-4, cy-4), (cx+4, cy+4)], fill=colors[i], width=2)
                    draw.line([(cx-4, cy+4), (cx+4, cy-4)], fill=colors[i], width=2)
                # Рисование монолитного бара (без пробелов)
                elif bar_pct is not None and i == 2:
                    bar_w = int((w - 10) * min(1.0, bar_pct))
                    if bar_w > 0:
                        draw.rectangle([curr_x + 5, y + 6, curr_x + 5 + bar_w, y + row_h - 6], fill=colors[i])
                else:
                    font = fonts[i]
                    bbox = draw.textbbox((0,0), text, font=font)
                    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
                    ty = y + (row_h - th) // 2 - 2
                    
                    if aligns[i] == "left": tx = curr_x + 5
                    elif aligns[i] == "right": tx = curr_x + w - tw - 5
                    else: tx = curr_x + (w - tw) // 2
                    
                    draw.text((tx, ty), text, fill=colors[i], font=font)
                curr_x += w
            return y + row_h

        # --- CPU ---
        y = center_text(f"Ваш процессор (CPU): {d.get('cpu_raw_full', '')}", f_blue, y, "#000080")
        rec_c = self.cfg_hw.get("cpu_rec_score", 4200)
        min_c = self.cfg_hw.get("cpu_min_score", 957)
        try: usr_c = int(d.get('cpu_score', 0))
        except: usr_c = 0
        max_c = max(usr_c, rec_c, min_c)
        if max_c == 0: max_c = 1

        c1, c2, c3 = 450, 60, 230
        y = draw_grid_row(margin, y, [c1, c2, c3], [f"Ваш CPU - {d.get('cpu_raw', '')}", d.get('cpu_score', ''), ""], [f_bold, f_bold, f_norm], ["black", d.get('cpu_color', 'black'), d.get('cpu_color', 'black')], ["right", "center", "left"], bar_pct=(usr_c/max_c))
        y = draw_grid_row(margin, y, [c1, c2, c3], [f"Рекомендованный минимальный CPU ≥ {self.cfg_hw.get('cpu_rec_name', '')}", str(rec_c), ""], [f_bold, f_bold, f_norm], ["black", self.color_ok, self.color_ok], ["right", "center", "left"], bar_pct=(rec_c/max_c))
        y = draw_grid_row(margin, y, [c1, c2, c3], [f"Минимально допустимый CPU - {self.cfg_hw.get('cpu_min_name', '')}", str(min_c), ""], [f_bold, f_bold, f_norm], ["black", "#f39c12", "#f39c12"], ["right", "center", "left"], bar_pct=(min_c/max_c))
        y += 10

        # --- RAM ---
        y = center_text(f"Оперативная память: {d.get('ram_raw_full', '')}", f_blue, y, "#000080")
        ram_str = d.get('ram_user', '0 Гб')
        try: usr_r = float(re.search(r'\d+', ram_str).group())
        except: usr_r = 0
        rec_r = self.cfg_hw.get("ram_rec_gb", 8)
        min_r = self.cfg_hw.get("ram_min_gb", 4)
        max_r = max(usr_r, rec_r, min_r)
        if max_r == 0: max_r = 1

        y = draw_grid_row(margin, y, [c1, c2, c3], ["Ваше кол-во ОЗУ", ram_str, ""], [f_bold, f_bold, f_norm], ["black", d.get('ram_color', 'black'), d.get('ram_color', 'black')], ["right", "center", "left"], bar_pct=(usr_r/max_r))
        y = draw_grid_row(margin, y, [c1, c2, c3], ["Рекомендуемое минимальное кол-во ОЗУ", f"{rec_r} Гб", ""], [f_bold, f_bold, f_norm], ["black", self.color_ok, self.color_ok], ["right", "center", "left"], bar_pct=(rec_r/max_r))
        y = draw_grid_row(margin, y, [c1, c2, c3], ["Минимально допустимое кол-во ОЗУ", f"{min_r} Гб", ""], [f_bold, f_bold, f_norm], ["black", "#f39c12", "#f39c12"], ["right", "center", "left"], bar_pct=(min_r/max_r))
        y += 10

        # --- OS ---
        os_ok = d.get('os_color') == self.color_ok
        y = center_text(f"ОС: {d.get('os_raw_full', '')}", f_blue, y, "#000080")
        c1_os, c2_os, c3_os = 450, 230, 60
        y = draw_grid_row(margin, y, [c1_os, c2_os, c3_os], ["Ваша ОС:", d.get('os_name', ''), "✔" if os_ok else "✖"], [f_bold, f_norm, f_norm], ["black", d.get('os_color', 'black'), d.get('os_color', 'black')], ["right", "center", "center"])
        y = draw_grid_row(margin, y, [c1_os, c2_os, c3_os], ["Обязательная ОС:", self.cfg_hw.get("os_required", "Windows 10 или 11"), "✔"], [f_bold, f_norm, f_norm], ["black", self.color_ok, self.color_ok], ["right", "center", "center"])
        y += 10

        # --- Peripherals ---
        c1_p, c2_p = 600, 140
        y = draw_grid_row(margin, y, [c1_p, c2_p], ["Клавиатура:", d.get('kb_ic', '✔')], [f_bold, f_norm], ["black", d.get('kb_col', 'green')], ["right", "center"])
        y = draw_grid_row(margin, y, [c1_p, c2_p], ["Мышь:", d.get('ms_ic', '✔')], [f_bold, f_norm], ["black", d.get('ms_col', 'green')], ["right", "center"])
        y = draw_grid_row(margin, y, [c1_p, c2_p], ["Аудиоустройство:", d.get('au_ic', '✔')], [f_bold, f_norm], ["black", d.get('au_col', 'green')], ["right", "center"])
        y += 10

        # --- GPU & Disk ---
        c1_m, c2_m = 200, 540
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["Видеокарта:", d.get('gpu_name', '')], [f_bold, f_norm], ["black", "black"], ["right", "left"])
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["Разрешение экрана:", d.get('resolution', '')], [f_bold, f_norm], ["black", "black"], ["right", "left"])
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["Диск C:", d.get('c_drive', '')], [f_bold, f_norm], ["black", d.get('c_color', 'black')], ["right", "left"])
        y += 10

        # --- Network ---
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["Пинг:", d.get('ping', '')], [f_bold, f_norm], ["black", d.get('ping_color', 'black')], ["right", "left"])
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["Входящая скорость:", d.get('dl', '')], [f_bold, f_norm], ["black", d.get('dl_color', 'black')], ["right", "left"])
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["Исходящая скорость:", d.get('ul', '')], [f_bold, f_norm], ["black", d.get('ul_color', 'black')], ["right", "left"])
        y += 10
        
        # --- System Footer ---
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["ВЕРДИКТ АНАЛИЗА:", verdict_text], [f_bold, f_bold], ["black", self.color_ok if verdict_text == "ОБОРУДОВАНИЕ ПОДХОДИТ" else self.color_err], ["right", "left"])
        y = draw_grid_row(margin, y, [c1_m, c2_m], ["HWID (Уник. код):", hwid_text], [f_bold, f_bold], ["black", "black"], ["right", "left"])

        # Обрезаем лишнее по факту (никаких черных полос!)
        img = img.crop((0, 0, W, y + 10))

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def launch_browser(self, improvements):
        if not self.check_and_set_spam_lock():
            timeout_hours = self.cfg_spam.get("lock_timeout_hours", 24.0)
            messagebox.showerror("Отправка заблокирована", f"Отчёт с этого компьютера уже был отправлен.\nПовторная отправка возможна через {timeout_hours} ч.")
            return

        form_url = self.config.get("web_form", {}).get("form_url", "https://example.com/your-form")
        labels = self.config.get("web_form", {}).get("labels", {})
        d = self.report_data
        
        verdict_text = self.verdict_msg
        improvements_text = "-" if verdict_text == "ОБОРУДОВАНИЕ ПОДХОДИТ" else ", ".join(improvements)
        hwid_text = self.generate_hwid() if self.cfg_spam.get("enable_hwid", True) else "-"
        
        data_to_pass = {
            'cpu_raw': d.get('cpu_raw', '').replace('"', "'").replace('\n', ' '),
            'ram': d.get('ram_user', '').replace('"', "'").replace('\n', ' '),
            'os': d.get('os_name', '').replace('"', "'").replace('\n', ' '),
            'ping': d.get('ping', '').replace('"', "'").replace('\n', ' '),
            'dl': d.get('dl', '').replace('"', "'").replace('\n', ' '),
            'ul': d.get('ul', '').replace('"', "'").replace('\n', ' '),
            'verdict': verdict_text.replace('"', "'").replace('\n', ' '),
            'improvements': improvements_text.replace('"', "'").replace('\n', ' '),
            'hwid': hwid_text.replace('"', "'").replace('\n', ' ')
        }

        b64_img = ""
        if HAS_PILLOW:
            try: b64_img = self.create_replica_image(d, verdict_text, hwid_text)
            except Exception as e: pass 
        
        p = multiprocessing.Process(target=run_browser, args=(form_url, data_to_pass, labels, b64_img))
        p.start()
        
        self.close_window(self.verdict_win)

if __name__ == "__main__":
    multiprocessing.freeze_support() 
    root = tk.Tk()
    app = TechCheckApp(root)
    root.mainloop()