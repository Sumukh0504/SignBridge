import os
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import json
from PIL import Image, ImageTk
from test import SignLanguageTranslator

# ------------------ THEME CONFIG ------------------ #
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLOR_BG = "#0F172A"       
COLOR_SIDEBAR = "#1E293B"  
COLOR_ACCENT = "#38BDF8"   
COLOR_TEXT_MAIN = "#F8FAFC"
COLOR_TEXT_MUTED = "#94A3B8"
COLOR_BTN_PRIMARY = "#0EA5E9"
COLOR_BTN_PRIMARY_HOVER = "#0284C7"
COLOR_BTN_DANGER = "#EF4444"
COLOR_CARD_BG = "#1E293B"

translator = None
translator_thread = None

class SignLanguageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SignBridge")
        self.root.geometry("1280x720")
        self.root.configure(fg_color=COLOR_BG)
        self.root.resizable(False, False)
        
        self.current_page = "dashboard"
        self.nav_buttons = {}
        
        # Status Var
        self.status_var = tk.StringVar(value="System Offline")
        
        # Settings State
        self.settings = {
            "gpu": True,
            "mirror": False,
            "dark_mode": True,
            "camera_access": False,
            "auto_input": True,
            "suggestion_mode": "inbuilt", # "off", "inbuilt", "custom"
            "stability_time": 1.0 # 1, 2, 3, 4, 5
        }
        
        self.custom_words = []
        self.history = []
        self.load_data()
        
        self.setup_main_app()
        self.switch_page("dashboard")

    def load_data(self):
        # Load History
        if os.path.exists("history.txt"):
            try:
                with open("history.txt", "r") as f:
                    self.history = [line.strip() for line in f.readlines()]
            except: self.history = []
        
        # Load Custom Dict
        if os.path.exists("custom_dict.json"):
            try:
                with open("custom_dict.json", "r") as f:
                    self.custom_words = json.load(f)
            except: self.custom_words = []

    def save_custom_dict(self):
        try:
            with open("custom_dict.json", "w") as f:
                json.dump(self.custom_words, f, indent=4)
        except: pass

    def rewrite_history_file(self):
        try:
            with open("history.txt", "w") as f:
                for item in self.history:
                    f.write(item + "\n")
        except: pass

    def save_history(self, text):
        if not text.strip(): return
        self.history.append(text)
        try:
            with open("history.txt", "a") as f:
                f.write(text + "\n")
        except: pass

    def get_image(self, path, size):
        try:
            if not os.path.exists(path): return None
            img = Image.open(path)
            img = img.resize(size, Image.LANCZOS)
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except: return None

    def setup_main_app(self):
        # SIDEBAR
        self.sidebar = ctk.CTkFrame(self.root, fg_color=COLOR_SIDEBAR, width=280, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.pack(pady=40, padx=20, anchor="w", fill="x")
        
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        self.sidebar_logo_img = self.get_image(logo_path, (40, 40))
        
        logo_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_row.pack(anchor="w")
        if self.sidebar_logo_img:
             ctk.CTkLabel(logo_row, text="", image=self.sidebar_logo_img).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(logo_row, text="SignBridge", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(header_frame, text="AI Translator Pro", font=("Segoe UI", 11, "bold"), text_color=COLOR_ACCENT).pack(anchor="w", pady=(2,0))
        
        # Navigation
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="x", pady=20)
        
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Controls", "controls"),
            ("Settings", "settings"),
            ("History", "history"),
            ("About Us", "about")
        ]
        
        for text, page_id in nav_items:
            btn = ctk.CTkButton(self.nav_frame, text=text, font=("Segoe UI", 12), 
                                fg_color="transparent", hover_color="#334155", 
                                anchor="w", height=45, corner_radius=8,
                                command=lambda p=page_id: self.switch_page(p))
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page_id] = btn
            
        ctk.CTkLabel(self.sidebar, text="Version 3.3.0", font=("Segoe UI", 10), text_color=COLOR_TEXT_MUTED).pack(side="bottom", anchor="w", padx=20, pady=20)

        # MAIN CONTENT
        self.main_content = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=30, pady=30)

        self.page_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.page_frame.pack(fill="both", expand=True)
    
    def switch_page(self, page_id):
        self.current_page = page_id
        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.configure(fg_color="#334155", font=("Segoe UI", 12, "bold"), text_color="white")
            else:
                btn.configure(fg_color="transparent", font=("Segoe UI", 12), text_color=COLOR_TEXT_MUTED)
        
        if hasattr(self, 'active_content_frame'):
            self.active_content_frame.destroy()
            
        self.active_content_frame = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        static_container = self.page_frame
        self.page_frame = self.active_content_frame
        
        if page_id == "dashboard": self.render_dashboard()
        elif page_id == "controls": self.render_controls()
        elif page_id == "settings": self.render_settings()
        elif page_id == "history": self.render_history()
        elif page_id == "about": self.render_about()
        
        self.page_frame = static_container
        self.animate_slide_up(self.active_content_frame)

    def animate_slide_up(self, widget):
        start_y = 0.05
        widget.place(relx=0, rely=start_y, relwidth=1, relheight=1)
        self.perform_animation_step(widget, start_y, 0.0)
        
    def perform_animation_step(self, widget, current_y, target_y):
        if not widget.winfo_exists(): return
        step = 0.01 
        if current_y > target_y:
            new_y = max(target_y, current_y - step)
            widget.place(relx=0, rely=new_y, relwidth=1, relheight=1)
            if new_y > target_y:
                self.root.after(10, lambda: self.perform_animation_step(widget, new_y, target_y))

    def render_dashboard(self):
        header = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(header, text="Dashboard", font=("Segoe UI", 32, "bold"), text_color="white").pack(anchor="w")
        
        # Left side column for Actions
        main_layout = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        main_layout.pack(fill="both", expand=True)

        left_col = ctk.CTkFrame(main_layout, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 20))

        # Launch Card
        card = ctk.CTkFrame(left_col, fg_color=COLOR_CARD_BG, corner_radius=20)
        card.pack(fill="x", pady=(0, 20))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=30, pady=30, fill="both")
        
        ctk.CTkLabel(inner, text="Advanced Translator", font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(inner, text=f"Auto-input delay: {self.settings['stability_time']}s", font=("Segoe UI", 12), text_color=COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 20))
        
        ctk.CTkButton(inner, text="▶  Launch System", font=("Segoe UI", 14, "bold"), 
                      fg_color=COLOR_BTN_PRIMARY, hover_color=COLOR_BTN_PRIMARY_HOVER, 
                      height=45, corner_radius=10, width=180, command=self.run_translator_action).pack(anchor="w")

        # Status Label below Launch
        status_row = ctk.CTkFrame(left_col, fg_color=COLOR_CARD_BG, corner_radius=15, height=60)
        status_row.pack(fill="x")
        status_row.pack_propagate(False)
        ctk.CTkLabel(status_row, text="System:", font=("Segoe UI", 12), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(20, 10))
        self.lbl_status = ctk.CTkLabel(status_row, textvariable=self.status_var, font=("Segoe UI", 14, "bold"), text_color="#EF4444")
        self.lbl_status.pack(side="left")

        # Right side column for Custom Suggestions management
        right_col = ctk.CTkFrame(main_layout, fg_color=COLOR_CARD_BG, corner_radius=20, width=350)
        right_col.pack(side="right", fill="both")
        right_col.pack_propagate(False)

        r_inner = ctk.CTkFrame(right_col, fg_color="transparent")
        r_inner.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(r_inner, text="Custom Suggestions", font=("Segoe UI", 18, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(r_inner, text="Add words for one-key typing", font=("Segoe UI", 11), text_color=COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 15))

        # Entry Row
        entry_row = ctk.CTkFrame(r_inner, fg_color="transparent")
        entry_row.pack(fill="x", pady=(0, 15))
        self.entry_custom = ctk.CTkEntry(entry_row, placeholder_text="Enter word...", height=35, font=("Segoe UI", 12))
        self.entry_custom.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(entry_row, text="+", width=35, height=35, fg_color=COLOR_ACCENT, hover_color=COLOR_BTN_PRIMARY, command=self.add_custom_word).pack(side="right")

        # Scroll List
        self.scroll_custom = ctk.CTkScrollableFrame(r_inner, fg_color="#0F172A", corner_radius=10, height=300)
        self.scroll_custom.pack(fill="both", expand=True)
        self.refresh_custom_list()

    def add_custom_word(self):
        word = self.entry_custom.get().strip().upper()
        if not word: return
        if word in self.custom_words:
            messagebox.showinfo("Info", "Word already in list.")
            return
        self.custom_words.append(word)
        self.save_custom_dict()
        self.entry_custom.delete(0, 'end')
        self.refresh_custom_list()

    def remove_custom_word(self, word):
        if word in self.custom_words:
            self.custom_words.remove(word)
            self.save_custom_dict()
            self.refresh_custom_list()

    def refresh_custom_list(self):
        for widget in self.scroll_custom.winfo_children():
            widget.destroy()
        
        for word in self.custom_words:
            item = ctk.CTkFrame(self.scroll_custom, fg_color="transparent")
            item.pack(fill="x", pady=2)
            ctk.CTkLabel(item, text=word, font=("Segoe UI", 12), text_color="white").pack(side="left", padx=5)
            ctk.CTkButton(item, text="x", width=20, height=20, fg_color="transparent", text_color="#EF4444", hover_color="#334155", command=lambda w=word: self.remove_custom_word(w)).pack(side="right")
            ctk.CTkFrame(self.scroll_custom, height=1, fg_color="#1E293B").pack(fill="x", padx=5)

    def render_settings(self):
        ctk.CTkLabel(self.page_frame, text="System Settings", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 25))
        container = ctk.CTkFrame(self.page_frame, fg_color=COLOR_CARD_BG, corner_radius=15)
        container.pack(fill="both", expand=True)
        p = ctk.CTkFrame(container, fg_color="transparent")
        p.pack(padx=30, pady=30, fill="both")
        
        # Stability Delay
        ctk.CTkLabel(p, text="Recognition Speed (Auto-Input Delay)", font=("Segoe UI", 14, "bold"), text_color="white").pack(anchor="w", pady=(0, 10))
        seg_stability = ctk.CTkSegmentedButton(p, values=["1s", "2s", "3s", "4s", "5s"], 
                                             selected_color=COLOR_ACCENT,
                                             command=self.update_stability)
        seg_stability.set(f"{int(self.settings['stability_time'])}s")
        seg_stability.pack(fill="x", pady=(0, 20))

        ctk.CTkFrame(p, height=1, fg_color="#334155").pack(fill="x", pady=15)

        ctk.CTkLabel(p, text="Suggestion Mode", font=("Segoe UI", 14, "bold"), text_color="white").pack(anchor="w", pady=(0, 10))
        seg_btn = ctk.CTkSegmentedButton(p, values=["Off", "Inbuilt", "Custom"], 
                                         selected_color=COLOR_ACCENT,
                                         command=self.update_suggestion_mode)
        seg_p = {"off": "Off", "inbuilt": "Inbuilt", "custom": "Custom"}
        seg_btn.set(seg_p[self.settings["suggestion_mode"]])
        seg_btn.pack(fill="x", pady=(0, 20))

        ctk.CTkFrame(p, height=1, fg_color="#334155").pack(fill="x", pady=15)
        self.add_switch(p, "Auto-Analyze Signs", "auto_input")
        self.add_switch(p, "Mirror Camera Feed", "mirror")
        self.add_switch(p, "Dark Mode Overlay", "dark_mode")

    def update_stability(self, value):
        self.settings["stability_time"] = float(value.replace("s", ""))

    def update_suggestion_mode(self, value):
        mapping = {"Off": "off", "Inbuilt": "inbuilt", "Custom": "custom"}
        self.settings["suggestion_mode"] = mapping[value]

    def add_switch(self, parent, text, key):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=text, font=("Segoe UI", 14), text_color="white").pack(side="left")
        var = ctk.BooleanVar(value=self.settings.get(key, False))
        def toggle(): self.settings[key] = var.get()
        ctk.CTkSwitch(row, text="", command=toggle, variable=var, progress_color=COLOR_ACCENT).pack(side="right")

    def render_controls(self):
        ctk.CTkLabel(self.page_frame, text="Application Controls", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 25))
        container = ctk.CTkFrame(self.page_frame, fg_color=COLOR_CARD_BG, corner_radius=15)
        container.pack(fill="both", expand=True)
        p = ctk.CTkFrame(container, fg_color="transparent")
        p.pack(padx=30, pady=30, fill="both")
        
        controls = [
            ("Spacebar", "Add current character (Manual)"),
            ("Number [1-3]", "Select Word Suggestion"),
            ("Key [Q]", "Exit Translator session"),
            ("Mouse Click", "Interact with on-screen buttons")
        ]
        for key, desc in controls:
            row = ctk.CTkFrame(p, fg_color="transparent")
            row.pack(fill="x", pady=10)
            ctk.CTkLabel(row, text=key, font=("Segoe UI", 13, "bold"), text_color=COLOR_ACCENT, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("Segoe UI", 13), text_color="white").pack(side="left")
            ctk.CTkFrame(p, height=1, fg_color="#334155").pack(fill="x")

    def render_history(self):
        ctk.CTkLabel(self.page_frame, text="Translation History", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 25))
        btn_bar = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(btn_bar, text="🗑 Clear All", fg_color=COLOR_BTN_DANGER, hover_color="#C2410C", width=100, command=self.clear_all_history).pack(side="right")
        container = ctk.CTkScrollableFrame(self.page_frame, fg_color=COLOR_CARD_BG, corner_radius=15)
        container.pack(fill="both", expand=True)
        if not self.history:
            ctk.CTkLabel(container, text="No recordings yet.", font=("Segoe UI", 13), text_color=COLOR_TEXT_MUTED).pack(pady=40)
        else:
            for i, item in enumerate(reversed(self.history)):
                idx = len(self.history) - 1 - i
                row = ctk.CTkFrame(container, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=5)
                ctk.CTkLabel(row, text=item, font=("Segoe UI", 13), text_color="white", justify="left", anchor="w").pack(side="left", fill="x", expand=True, padx=10)
                ctk.CTkButton(row, text="Delete", width=60, height=24, fg_color="#450a0a", hover_color="#7f1d1d", command=lambda x=idx: self.delete_history_item(x)).pack(side="right", padx=5)
                ctk.CTkFrame(container, height=1, fg_color="#334155").pack(fill="x", padx=10)

    def delete_history_item(self, index):
        if 0 <= index < len(self.history):
            self.history.pop(index); self.rewrite_history_file(); self.render_history()

    def clear_all_history(self):
        if messagebox.askyesno("Confirm", "Delete all translation history?"):
            self.history = []; self.rewrite_history_file(); self.render_history()

    def render_about(self):
        ctk.CTkLabel(self.page_frame, text="About SignBridge", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 25))
        container = ctk.CTkFrame(self.page_frame, fg_color=COLOR_CARD_BG, corner_radius=15)
        container.pack(fill="both", expand=True)
        
        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Contact info
        contact_frame = ctk.CTkFrame(scroll, fg_color="#334155", corner_radius=10)
        contact_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(contact_frame, text="📞 Contact Support: 8691322877", font=("Segoe UI", 14, "bold"), text_color=COLOR_ACCENT).pack(pady=(15, 5))
        ctk.CTkLabel(contact_frame, text="✉ Email: sumukhtrivedi59@gmail.com", font=("Segoe UI", 12), text_color="white").pack(pady=(0, 15))

        # About Development
        about_text = (
            "Building Bridges with Technology\n\n"
            "Project Origin:\n"
            "SignBridge was conceptualized and developed as a Third Year Black Book Project. "
            "The primary objective was to leverage modern Machine Learning and Computer Vision "
            "to create an accessible tool that assists in bridging the communication gap "
            "within the deaf and hard-of-hearing community.\n\n"
            "Our Vision:\n"
            "This project aims to provide a seamless, real-time sign-to-text translation "
            "experience. We believe that technology should be an equalizer, and SignBridge "
            "is our humble contribution toward a more inclusive society.\n\n"
            "The Developers:\n"
            "Developed by a team of enthusiastic third-year students focused on creating "
            "impactful AI-driven solutions for real-world accessibility challenges."
        )
        
        lbl = ctk.CTkLabel(scroll, text=about_text, font=("Segoe UI", 13), text_color="white", justify="left", wraplength=550)
        lbl.pack(anchor="w", padx=10)

    def toggle_camera_access(self):
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                self.settings["camera_access"] = True
                self.lbl_status.configure(text="Ready", text_color="#10B981")
                cap.release()
            else: messagebox.showerror("Error", "Camera not found.")
        except: messagebox.showerror("Error", "Camera verification failed.")

    def run_translator_action(self):
        global translator, translator_thread
        if translator is None: translator = SignLanguageTranslator()
        translator.configure(self.settings)
        if not translator.running:
            translator_thread = threading.Thread(target=translator.run, daemon=True)
            translator_thread.start()
            self.root.withdraw()
            self.monitor_translator()

    def monitor_translator(self):
        if translator is None or not translator.running:
            if translator and translator.final_text: 
                self.save_history(translator.final_text)
            
            # Ensure the window is restored, brought to front, and focused
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        else:
            self.root.after(500, self.monitor_translator)

if __name__ == "__main__":
    app = ctk.CTk()
    SignLanguageApp(app)
    app.mainloop()
