# --- ИМПОРТ БИБЛИОТЕК ---
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import json
import csv
import os
import hashlib

class ConfigConstructorApp:
    """
    Главный класс приложения-конструктора.
    Предоставляет графический интерфейс (GUI) для удобного создания 
    и редактирования конфигурационного файла config.json.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Конструктор конфигурации TechCheck4PyrusWebForm")
        self.root.geometry("650x700")
        
        # Словари и списки для автодополнения названий процессоров
        self.cpu_data = {}
        self.cpu_names = []
        self.load_cpu_database()

        # Инициализация всех переменных, привязанных к полям ввода
        self.init_vars()
        # Построение графического интерфейса
        self.build_ui()
        # Попытка загрузить данные из существующего config.json
        self.load_existing_config()

    def load_cpu_database(self):
        """Чтение локальной базы процессоров (csv) для функции умного поиска"""
        if os.path.exists("cpu_data.csv"):
            try:
                with open("cpu_data.csv", mode='r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            name = row[0].strip()
                            try:
                                score = int(float(row[1]))
                                self.cpu_data[name] = score
                            except: pass
                self.cpu_names = list(self.cpu_data.keys())
            except Exception as e:
                print(f"Ошибка загрузки базы CPU: {e}")

    def init_vars(self):
        """Создание переменных Tkinter (StringVar, BooleanVar) со значениями по умолчанию"""
        # 1. Общие настройки программы (тексты и цвета)
        self.var_win_title = tk.StringVar(value="Техническая проверка личного оборудования для удаленной работы")
        self.var_target_text = tk.StringVar(value="удаленной работы")
        self.var_color_ok = tk.StringVar(value="#27ae60")
        self.var_color_err = tk.StringVar(value="#FC5055")
        
        # 2. Аппаратные лимиты (CPU, RAM, ОС)
        self.var_cpu_rec_lbl = tk.StringVar(value="Рекомендованный минимальный CPU")
        self.var_cpu_rec_name = tk.StringVar(value="Intel Core i5-6400")
        self.var_cpu_rec_score = tk.StringVar(value="4200")
        
        self.var_cpu_min_lbl = tk.StringVar(value="Минимально допустимый CPU")
        self.var_cpu_min_name = tk.StringVar(value="Celeron N4020")
        self.var_cpu_min_score = tk.StringVar(value="957")
        
        self.var_ram_rec = tk.StringVar(value="8")
        self.var_ram_min = tk.StringVar(value="4")
        self.var_os = tk.StringVar(value="Windows 10 или 11")
        
        # 3. Сетевые лимиты (Пинг, скорость скачивания и загрузки)
        self.var_ping = tk.StringVar(value="50")
        self.var_dl = tk.StringVar(value="20")
        self.var_ul = tk.StringVar(value="20")
        
        # 4. Настройки веб-формы (URL и маппинг полей)
        self.var_url = tk.StringVar(value="https://example.com/your-form")
        self.var_lbl_cpu = tk.StringVar(value="Центральный процессор")
        self.var_lbl_ram = tk.StringVar(value="Оперативная память")
        self.var_lbl_os = tk.StringVar(value="Операционная система")
        self.var_lbl_ping = tk.StringVar(value="Пинг")
        self.var_lbl_dl = tk.StringVar(value="Входящая скорость интернета")
        self.var_lbl_ul = tk.StringVar(value="Исходящая скорость интернета")
        self.var_lbl_verdict = tk.StringVar(value="Результат анализа")
        self.var_lbl_improv = tk.StringVar(value="Что необходимо улучшить")
        self.var_lbl_hwid = tk.StringVar(value="HWID")
        self.var_lbl_fio = tk.StringVar(value="ФИО")

        # 5. Настройки модуля Антиспам
        self.var_spam_lock = tk.BooleanVar(value=True)
        self.var_spam_timeout = tk.StringVar(value="24")
        self.var_spam_hwid = tk.BooleanVar(value=True)
        self.var_admin_pass = tk.StringVar()
        self.loaded_admin_hash = "" # Хранит хэш пароля из загруженного конфига

    def build_ui(self):
        """Отрисовка всех вкладок, полей ввода и кнопок конструктора"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # --- Вкладка 1: Общие ---
        f_general = ttk.Frame(notebook, padding=10)
        notebook.add(f_general, text="Общие настройки")
        ttk.Label(f_general, text="Заголовок окна:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(f_general, textvariable=self.var_win_title, width=60).grid(row=0, column=1, pady=5)
        ttk.Label(f_general, text="Цель проверки:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(f_general, textvariable=self.var_target_text, width=60).grid(row=1, column=1, pady=5)
        ttk.Label(f_general, text="Цвет успеха:").grid(row=2, column=0, sticky="w", pady=5)
        btn_ok = tk.Button(f_general, text="Выбрать", bg=self.var_color_ok.get(), fg="white", command=lambda: self.choose_color(self.var_color_ok, btn_ok))
        btn_ok.grid(row=2, column=1, sticky="w", pady=5)
        ttk.Label(f_general, text="Цвет ошибки:").grid(row=3, column=0, sticky="w", pady=5)
        btn_err = tk.Button(f_general, text="Выбрать", bg=self.var_color_err.get(), fg="white", command=lambda: self.choose_color(self.var_color_err, btn_err))
        btn_err.grid(row=3, column=1, sticky="w", pady=5)

        # --- Вкладка 2: Железо ---
        f_hw = ttk.Frame(notebook, padding=10)
        notebook.add(f_hw, text="Железо")
        
        ttk.Label(f_hw, text="=== Рекомендуемый CPU ===").grid(row=0, column=0, columnspan=2, pady=(5,5), sticky="w")
        ttk.Label(f_hw, text="Подпись:").grid(row=1, column=0, sticky="w")
        ttk.Entry(f_hw, textvariable=self.var_cpu_rec_lbl, width=40).grid(row=1, column=1, sticky="w")
        ttk.Label(f_hw, text="Название:").grid(row=2, column=0, sticky="w")
        cb_r = ttk.Combobox(f_hw, textvariable=self.var_cpu_rec_name, values=self.cpu_names, width=37)
        cb_r.grid(row=2, column=1, sticky="w")
        cb_r.bind('<KeyRelease>', lambda e: self.filter_cpu(e, cb_r))
        cb_r.bind('<<ComboboxSelected>>', lambda e: self.auto_fill_score(self.var_cpu_rec_name, self.var_cpu_rec_score))
        ttk.Label(f_hw, text="Очки:").grid(row=3, column=0, sticky="w")
        ttk.Entry(f_hw, textvariable=self.var_cpu_rec_score, width=15).grid(row=3, column=1, sticky="w")

        ttk.Label(f_hw, text="=== Минимальный CPU ===").grid(row=4, column=0, columnspan=2, pady=(10,5), sticky="w")
        ttk.Label(f_hw, text="Подпись:").grid(row=5, column=0, sticky="w")
        ttk.Entry(f_hw, textvariable=self.var_cpu_min_lbl, width=40).grid(row=5, column=1, sticky="w")
        ttk.Label(f_hw, text="Название:").grid(row=6, column=0, sticky="w")
        cb_m = ttk.Combobox(f_hw, textvariable=self.var_cpu_min_name, values=self.cpu_names, width=37)
        cb_m.grid(row=6, column=1, sticky="w")
        cb_m.bind('<KeyRelease>', lambda e: self.filter_cpu(e, cb_m))
        cb_m.bind('<<ComboboxSelected>>', lambda e: self.auto_fill_score(self.var_cpu_min_name, self.var_cpu_min_score))
        ttk.Label(f_hw, text="Очки:").grid(row=7, column=0, sticky="w")
        ttk.Entry(f_hw, textvariable=self.var_cpu_min_score, width=15).grid(row=7, column=1, sticky="w")

        ttk.Label(f_hw, text="=== Память и ОС ===").grid(row=8, column=0, columnspan=2, pady=(10,5), sticky="w")
        ttk.Label(f_hw, text="Рек. ОЗУ (Гб):").grid(row=9, column=0, sticky="w")
        ttk.Entry(f_hw, textvariable=self.var_ram_rec, width=15).grid(row=9, column=1, sticky="w")
        ttk.Label(f_hw, text="Мин. ОЗУ (Гб):").grid(row=10, column=0, sticky="w")
        ttk.Entry(f_hw, textvariable=self.var_ram_min, width=15).grid(row=10, column=1, sticky="w")
        ttk.Label(f_hw, text="ОС:").grid(row=11, column=0, sticky="w")
        ttk.Combobox(f_hw, textvariable=self.var_os, values=["Windows 7", "Windows 8", "Windows 8.1", "Windows 10", "Windows 11", "Windows 10 или 11"], width=37).grid(row=11, column=1, sticky="w")

        # --- Вкладка 3: Сеть ---
        f_net = ttk.Frame(notebook, padding=10)
        notebook.add(f_net, text="Сеть")
        ttk.Label(f_net, text="Макс. Пинг (мс):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(f_net, textvariable=self.var_ping, width=15).grid(row=0, column=1, pady=5, sticky="w")
        ttk.Label(f_net, text="Мин. Входящая:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(f_net, textvariable=self.var_dl, width=15).grid(row=1, column=1, pady=5, sticky="w")
        ttk.Label(f_net, text="Мин. Исходящая:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(f_net, textvariable=self.var_ul, width=15).grid(row=2, column=1, pady=5, sticky="w")

        # --- Вкладка 4: Веб-форма ---
        f_form = ttk.Frame(notebook, padding=10)
        notebook.add(f_form, text="Веб-форма")
        ttk.Label(f_form, text="Ссылка на форму:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(f_form, textvariable=self.var_url, width=60).grid(row=0, column=1, pady=5)
        ttk.Label(f_form, text="Названия полей:").grid(row=1, column=0, columnspan=2, pady=(5,5), sticky="w")
        
        labels_map = [
            ("Процессор:", self.var_lbl_cpu), ("ОЗУ:", self.var_lbl_ram), ("ОС:", self.var_lbl_os),
            ("Пинг:", self.var_lbl_ping), ("Входящая:", self.var_lbl_dl), ("Исходящая:", self.var_lbl_ul),
            ("Результат:", self.var_lbl_verdict), ("Что улучшить:", self.var_lbl_improv),
            ("HWID:", self.var_lbl_hwid), ("ФИО:", self.var_lbl_fio)
        ]
        for i, (text, var) in enumerate(labels_map):
            ttk.Label(f_form, text=text).grid(row=i+2, column=0, sticky="w", pady=2)
            ttk.Entry(f_form, textvariable=var, width=40).grid(row=i+2, column=1, sticky="w", pady=2)

        # --- Вкладка 5: Антиспам ---
        f_spam = ttk.Frame(notebook, padding=10)
        notebook.add(f_spam, text="Антиспам")
        ttk.Checkbutton(f_spam, text="Блокировка повторной отправки", variable=self.var_spam_lock).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Label(f_spam, text="Таймаут (часов):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(f_spam, textvariable=self.var_spam_timeout, width=10).grid(row=1, column=1, sticky="w", pady=5)
        ttk.Checkbutton(f_spam, text="Передавать уникальный ID (HWID) в отдельное поле", variable=self.var_spam_hwid).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        ttk.Label(f_spam, text="Пароль для ПАСХАЛКИ (отключение антиспама):", font=("", 9, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", pady=(15,0))
        ttk.Entry(f_spam, textvariable=self.var_admin_pass, width=30).grid(row=4, column=0, sticky="w", pady=5)
        tk.Label(f_spam, text="* Если оставить пустым, сохранится старый пароль.\n* В config.json пароль сохраняется в зашифрованном виде (SHA-256).", fg="gray", justify="left").grid(row=5, column=0, columnspan=2, sticky="w")

        # --- Кнопка сохранения ---
        btn_save = tk.Button(self.root, text="СОХРАНИТЬ КОНФИГУРАЦИЮ", bg="#3498db", fg="white", font=("Segoe UI", 12, "bold"), command=self.save_config)
        btn_save.pack(fill="x", padx=10, pady=(0, 10))

    def choose_color(self, var, btn):
        """Открывает системную палитру для выбора цвета и обновляет кнопку"""
        color_code = colorchooser.askcolor(initialcolor=var.get())[1]
        if color_code:
            var.set(color_code)
            btn.config(bg=color_code)

    def filter_cpu(self, event, combobox):
        """Фильтрация выпадающего списка (Combobox) процессоров при вводе текста"""
        val = combobox.get().lower()
        combobox['values'] = self.cpu_names if val == '' else [c for c in self.cpu_names if val in c.lower()]

    def auto_fill_score(self, name_var, score_var):
        """Автоматическая подстановка очков (score) при выборе CPU из списка"""
        if name_var.get() in self.cpu_data: 
            score_var.set(str(self.cpu_data[name_var.get()]))

    def load_existing_config(self):
        """Парсинг существующего файла config.json (если он есть) для заполнения полей"""
        if not os.path.exists("config.json"): return
        try:
            with open("config.json", "r", encoding="utf-8") as f: 
                data = json.load(f)
            
            # Секция: Приложение
            self.var_win_title.set(data.get("app_settings", {}).get("window_title", self.var_win_title.get()))
            self.var_target_text.set(data.get("app_settings", {}).get("company_target_text", self.var_target_text.get()))
            self.var_color_ok.set(data.get("app_settings", {}).get("color_success", self.var_color_ok.get()))
            self.var_color_err.set(data.get("app_settings", {}).get("color_error", self.var_color_err.get()))
            
            # Секция: Железо
            hw = data.get("hardware_limits", {})
            self.var_cpu_rec_lbl.set(hw.get("cpu_rec_label", self.var_cpu_rec_lbl.get()))
            self.var_cpu_rec_name.set(hw.get("cpu_rec_name", self.var_cpu_rec_name.get()))
            self.var_cpu_rec_score.set(str(hw.get("cpu_rec_score", self.var_cpu_rec_score.get())))
            self.var_cpu_min_lbl.set(hw.get("cpu_min_label", self.var_cpu_min_lbl.get()))
            self.var_cpu_min_name.set(hw.get("cpu_min_name", self.var_cpu_min_name.get()))
            self.var_cpu_min_score.set(str(hw.get("cpu_min_score", self.var_cpu_min_score.get())))
            self.var_ram_rec.set(str(hw.get("ram_rec_gb", self.var_ram_rec.get())))
            self.var_ram_min.set(str(hw.get("ram_min_gb", self.var_ram_min.get())))
            self.var_os.set(hw.get("os_required", self.var_os.get()))
            
            # Секция: Сеть
            net = data.get("network_limits", {})
            self.var_ping.set(str(net.get("ping_max_ms", self.var_ping.get())))
            self.var_dl.set(str(net.get("dl_min_mbps", self.var_dl.get())))
            self.var_ul.set(str(net.get("ul_min_mbps", self.var_ul.get())))
            
            # Секция: Веб-форма
            wf = data.get("web_form", {})
            self.var_url.set(wf.get("form_url", self.var_url.get()))
            lbls = wf.get("labels", {})
            self.var_lbl_cpu.set(lbls.get("cpu", self.var_lbl_cpu.get()))
            self.var_lbl_ram.set(lbls.get("ram", self.var_lbl_ram.get()))
            self.var_lbl_os.set(lbls.get("os", self.var_lbl_os.get()))
            self.var_lbl_ping.set(lbls.get("ping", self.var_lbl_ping.get()))
            self.var_lbl_dl.set(lbls.get("dl", self.var_lbl_dl.get()))
            self.var_lbl_ul.set(lbls.get("ul", self.var_lbl_ul.get()))
            self.var_lbl_verdict.set(lbls.get("verdict", self.var_lbl_verdict.get()))
            self.var_lbl_improv.set(lbls.get("improvements", self.var_lbl_improv.get()))
            self.var_lbl_hwid.set(lbls.get("hwid", self.var_lbl_hwid.get()))
            self.var_lbl_fio.set(lbls.get("fio", self.var_lbl_fio.get()))
            
            # Секция: Антиспам
            spm = data.get("spam_protection", {})
            self.var_spam_lock.set(spm.get("enable_local_lock", True))
            self.var_spam_timeout.set(str(spm.get("lock_timeout_hours", 24)))
            self.var_spam_hwid.set(spm.get("enable_hwid", True))
            self.loaded_admin_hash = spm.get("admin_password_hash", "")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать config.json: {e}")

    def save_config(self):
        """Сбор данных из UI и сохранение их в файл config.json"""
        try:
            # Шифрование нового пароля (SHA-256) или сохранение старого хэша
            new_pass = self.var_admin_pass.get()
            if new_pass:
                final_hash = hashlib.sha256(new_pass.encode('utf-8')).hexdigest()
            else:
                final_hash = self.loaded_admin_hash

            # Формирование структуры JSON
            config_data = {
                "_comment_ОБЩЕЕ": "Конфигурационный файл программы TechCheck4PyrusWebForm.",
                "app_settings": {
                    "window_title": self.var_win_title.get(),
                    "company_target_text": self.var_target_text.get(),
                    "color_success": self.var_color_ok.get(),
                    "color_error": self.var_color_err.get()
                },
                "hardware_limits": {
                    "cpu_rec_label": self.var_cpu_rec_lbl.get(),
                    "cpu_rec_name": self.var_cpu_rec_name.get(),
                    "cpu_rec_score": int(self.var_cpu_rec_score.get() or 0),
                    "cpu_min_label": self.var_cpu_min_lbl.get(),
                    "cpu_min_name": self.var_cpu_min_name.get(),
                    "cpu_min_score": int(self.var_cpu_min_score.get() or 0),
                    "ram_rec_gb": int(self.var_ram_rec.get() or 0),
                    "ram_min_gb": int(self.var_ram_min.get() or 0),
                    "os_required": self.var_os.get()
                },
                "network_limits": {
                    "ping_max_ms": float(self.var_ping.get() or 0.0),
                    "dl_min_mbps": float(self.var_dl.get() or 0.0),
                    "ul_min_mbps": float(self.var_ul.get() or 0.0)
                },
                "web_form": {
                    "form_url": self.var_url.get(),
                    "labels": {
                        "cpu": self.var_lbl_cpu.get(),
                        "ram": self.var_lbl_ram.get(),
                        "os": self.var_lbl_os.get(),
                        "ping": self.var_lbl_ping.get(),
                        "dl": self.var_lbl_dl.get(),
                        "ul": self.var_lbl_ul.get(),
                        "verdict": self.var_lbl_verdict.get(),
                        "improvements": self.var_lbl_improv.get(),
                        "hwid": self.var_lbl_hwid.get(),
                        "fio": self.var_lbl_fio.get()
                    }
                },
                "spam_protection": {
                    "enable_local_lock": self.var_spam_lock.get(),
                    "lock_timeout_hours": float(self.var_spam_timeout.get() or 24.0),
                    "enable_hwid": self.var_spam_hwid.get(),
                    "admin_password_hash": final_hash
                }
            }

            # Запись в файл
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            self.loaded_admin_hash = final_hash
            messagebox.showinfo("Успех", "Конфигурация успешно сохранена!")
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте числовые поля!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigConstructorApp(root)
    root.mainloop()