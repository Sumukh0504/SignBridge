import cv2
from cvzone.HandTrackingModule import HandDetector
from cvzone.ClassificationModule import Classifier
import numpy as np
import math
import os
import time
import threading
import json
from spellchecker import SpellChecker

class SignLanguageTranslator:
    def __init__(self):
        self.cap = None
        self.running = False
        
        # Paths
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(self.BASE_DIR, "Model", "keras_model.h5")
        self.labels_path = os.path.join(self.BASE_DIR, "Model", "labels.txt")
        self.custom_dict_path = os.path.join(self.BASE_DIR, "custom_dict.json")
        
        # Modules
        self.detector = HandDetector(maxHands=1)
        try:
            self.classifier = Classifier(self.model_path, self.labels_path)
        except Exception as e:
            print(f"Error loading classifier: {e}")
            self.classifier = None
            
        # Spell Checker
        self.spell = SpellChecker()
        self.suggestions = []
        self.custom_dict = []
        self.load_custom_dict()
        
        # Constants
        self.offset = 20
        self.imgSize = 300
        self.labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I" , "J", "K", "L" , "M", "N", "O" , "P", "Q", "R" , "S", "T", "U" , "V", "W", "X" , "Y", "Z"]
        
        # Text State
        self.final_text = ""
        self.current_letter = ""
        
        # Auto-Input Logic
        self.last_detected_letter = ""
        self.stable_counter = 0
        self.auto_input_delay = 1.0 
        self.last_frame_time = time.time()
        
        # Settings Defaults
        self.mirror_mode = False
        self.dark_mode_enabled = True
        self.auto_input_enabled = True
        self.suggestion_mode = "inbuilt" # "off", "inbuilt", "custom"
        
        # UI Metrics
        self.WINDOW_W = 1280
        self.WINDOW_H = 720
        
        # Colors
        self.CLR_BAR_BG     = (32, 33, 36)
        self.CLR_BTN_NORMAL = (60, 64, 67)
        self.CLR_BTN_HOVER  = (80, 84, 87)
        self.CLR_RED        = (59, 64, 234)
        self.CLR_WHITE      = (255, 255, 255)
        self.CLR_ACCENT     = (248, 189, 56)
        
        self.mouse_x, self.mouse_y = 0, 0
        self.mouse_click = False

    def load_custom_dict(self):
        if os.path.exists(self.custom_dict_path):
            try:
                with open(self.custom_dict_path, 'r') as f:
                    self.custom_dict = json.load(f)
            except: self.custom_dict = []

    def configure(self, settings):
        self.mirror_mode = settings.get("mirror", False)
        self.dark_mode_enabled = settings.get("dark_mode", True)
        self.auto_input_enabled = settings.get("auto_input", True)
        self.suggestion_mode = settings.get("suggestion_mode", "inbuilt")
        self.auto_input_delay = settings.get("stability_time", 1.0)

    def update_suggestions(self):
        if self.suggestion_mode == "off":
            self.suggestions = []
            return

        words = self.final_text.split()
        if not words: 
            self.suggestions = []
            return
        
        current_word = words[-1].upper()
        if len(current_word) < 1:
            self.suggestions = []
            return
            
        if self.suggestion_mode == "custom":
            # Match start of word in custom dict
            matches = [w for w in self.custom_dict if w.upper().startswith(current_word)]
            self.suggestions = matches[:3]
        else: # inbuilt
            if len(current_word) < 2:
                self.suggestions = []
                return
            try:
                candidates_set = self.spell.candidates(current_word.lower())
                candidates = [c.upper() for c in candidates_set] if candidates_set is not None else []
                self.suggestions = candidates[:3]
            except:
                self.suggestions = []

    def mouse_event(self, event, x, y, flags, param):
        self.mouse_x, self.mouse_y = x, y
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_click = True

    def draw_circle_btn(self, img, center, radius, color, icon_type, is_hovered):
        cx, cy = center
        draw_color = self.CLR_BTN_HOVER if is_hovered else color
        if icon_type == "hangup" and is_hovered:
            draw_color = (70, 70, 255)
            
        cv2.circle(img, center, radius, draw_color, -1, cv2.LINE_AA)
        white = self.CLR_WHITE
        thick = 2
        
        if icon_type == "hangup":
            w2 = 14
            cv2.rectangle(img, (cx - w2, cy - 4), (cx + w2, cy + 4), white, -1, cv2.LINE_AA)
        elif icon_type == "clear":
            r = 10
            cv2.line(img, (cx-r, cy-r), (cx+r, cy+r), white, thick, cv2.LINE_AA)
            cv2.line(img, (cx-r, cy+r), (cx+r, cy-r), white, thick, cv2.LINE_AA)
        elif icon_type == "back":
            cv2.line(img, (cx+8, cy), (cx-8, cy), white, thick, cv2.LINE_AA)
            cv2.line(img, (cx-8, cy), (cx-2, cy-6), white, thick, cv2.LINE_AA)
            cv2.line(img, (cx-8, cy), (cx-2, cy+6), white, thick, cv2.LINE_AA)
        elif icon_type == "space":
            cv2.line(img, (cx-10, cy+5), (cx+10, cy+5), white, thick, cv2.LINE_AA)
            cv2.line(img, (cx-10, cy+5), (cx-10, cy), white, thick, cv2.LINE_AA)
            cv2.line(img, (cx+10, cy+5), (cx+10, cy), white, thick, cv2.LINE_AA)

    def run(self):
        self.running = True
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.WINDOW_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.WINDOW_H)
        
        window_name = "SignBridge Translator"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.mouse_event)
        
        while self.running:
            success, img = self.cap.read()
            if not success: break
            if self.mirror_mode: img = cv2.flip(img, 1)

            imgOutput = img.copy()
            h, w, _ = img.shape
            # 1. Detection (Run on a copy to keep 'img' clean for cropping)
            imgDetection_for_bbox = img.copy()
            hands, _ = self.detector.findHands(imgDetection_for_bbox, draw=True)
            self.current_letter = ""

            if hands:
                hand = hands[0]
                x, y, bw, bh = hand['bbox']
                
                # Accuracy Fix: ALWAYS crop from the CLEAN image (no skeleton)
                x1, y1 = max(0, x - self.offset), max(0, y - self.offset)
                x2, y2 = min(w, x + bw + self.offset), min(h, y + bh + self.offset)
                imgCrop = img[y1:y2, x1:x2]

                if imgCrop.size != 0:
                    imgWhite = np.ones((self.imgSize, self.imgSize, 3), np.uint8) * 255
                    aspectRatio = bh / bw
                    try:
                        if aspectRatio > 1:
                            k = self.imgSize / bh
                            wCal = math.ceil(k * bw)
                            imgResize = cv2.resize(imgCrop, (wCal, self.imgSize))
                            wGap = (self.imgSize - wCal) // 2
                            imgWhite[:, wGap:wGap + wCal] = imgResize
                        else:
                            k = self.imgSize / bw
                            hCal = math.ceil(k * bh)
                            imgResize = cv2.resize(imgCrop, (self.imgSize, hCal))
                            hGap = (self.imgSize - hCal) // 2
                            imgWhite[hGap:hGap + hCal, :] = imgResize

                        if self.classifier:
                            prediction, index = self.classifier.getPrediction(imgWhite, draw=False)
                            if index < len(self.labels):
                                self.current_letter = self.labels[index]
                    except: pass
            
            # 2. Auto-Input Logic
            if self.auto_input_enabled:
                if self.current_letter and self.current_letter == self.last_detected_letter:
                    self.stable_counter += (time.time() - self.last_frame_time)
                    if self.stable_counter >= self.auto_input_delay:
                        self.final_text += self.current_letter
                        self.stable_counter = 0
                        self.update_suggestions()
                else:
                    self.last_detected_letter = self.current_letter
                    self.stable_counter = 0
            
            self.last_frame_time = time.time()

            # --- UI DRAWING ---
            sidebar_w = 320
            sidebar_x = w - sidebar_w
            bg_color = (15, 15, 20) if self.dark_mode_enabled else (255, 255, 255)
            txt_color = (255, 255, 255) if self.dark_mode_enabled else (20, 20, 20)

            overlay = imgOutput.copy()
            cv2.rectangle(overlay, (sidebar_x, 0), (w, h), bg_color, -1)
            cv2.addWeighted(overlay, 0.9, imgOutput, 0.1, 0, imgOutput)
            
            cv2.putText(imgOutput, "TRANSLATION", (sidebar_x + 20, 40), cv2.FONT_HERSHEY_DUPLEX, 0.6, (56, 189, 248), 1)
            cv2.line(imgOutput, (sidebar_x + 20, 55), (w - 20, 55), (80, 80, 80), 1)
            
            # Suggestions List (Visual UI)
            if self.suggestions:
                cv2.putText(imgOutput, f"SUGGESTIONS ({self.suggestion_mode.upper()}):", (sidebar_x + 20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                for i, sugg in enumerate(self.suggestions):
                    cv2.putText(imgOutput, f"[{i+1}] {sugg}", (sidebar_x + 20, 105 + (i * 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (56, 189, 248), 1)

            # --- TRANSCRIPT RENDERING ---
            text_y = 210
            words = self.final_text.split()
            
            # Ghost Text Logic: Show the top suggestion at the end of the text
            render_text = self.final_text
            ghost_sugg = ""
            if self.suggestion_mode != "off" and self.suggestions and len(words) > 0:
                current_word = words[-1]
                top_sugg = self.suggestions[0]
                # If suggestion is longer than current word, show the remainder
                if top_sugg.upper().startswith(current_word.upper()):
                    ghost_sugg = top_sugg[len(current_word):]

            # Wrapping & Rendering
            display_lines = []
            curr_line = ""
            # We process words normally
            for word in words:
                (tw, _), _ = cv2.getTextSize(curr_line + word + " ", cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                if tw > sidebar_w - 40:
                    display_lines.append(curr_line)
                    curr_line = word + " "
                else:
                    curr_line += word + " "
            
            # Handle the last line (with potential ghost text)
            display_lines.append(curr_line)
            
            for i, line in enumerate(display_lines[-15:]):
                is_last_line = (i == len(display_lines[-15:]) - 1)
                cv2.putText(imgOutput, line, (sidebar_x + 20, text_y + (i * 28)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, txt_color, 1, cv2.LINE_AA)
                
                # If it's the last line and we have a suggestion, draw it in Accent color
                if is_last_line and ghost_sugg:
                    (line_w, _), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    # Draw ghost text in a faded accent color
                    cv2.putText(imgOutput, ghost_sugg, (sidebar_x + 20 + line_w, text_y + (i * 28)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1, cv2.LINE_AA)

            if self.auto_input_enabled and self.current_letter:
                progress = min(self.stable_counter / self.auto_input_delay, 1.0)
                px, py = sidebar_x + 20, h - 140
                cv2.rectangle(imgOutput, (px, py), (px + 280, py + 8), (40, 40, 40), -1)
                cv2.rectangle(imgOutput, (px, py), (px + int(280 * progress), py + 8), (56, 189, 248), -1)
                cv2.putText(imgOutput, f"Auto-typing: {self.current_letter}", (px, py - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            if hands:
                hand = hands[0]
                bx, by, bbw, bbh = hand['bbox']
                cv2.rectangle(imgOutput, (bx, by), (bx + bbw, by + bbh), (56, 189, 248), 2)
                if self.current_letter:
                    cv2.rectangle(imgOutput, (bx, by - 35), (bx + 80, by), (56, 189, 248), -1)
                    cv2.putText(imgOutput, self.current_letter, (bx + 10, by - 10), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)

            video_area_w = w - sidebar_w
            v_center = video_area_w // 2
            bar_y = h - 100
            
            btn_defs = [
                {"name": "back",   "x": v_center - 110, "color": self.CLR_BTN_NORMAL, "icon": "back", "label": "Back"},
                {"name": "space",  "x": v_center - 35,  "color": self.CLR_BTN_NORMAL, "icon": "space", "label": "Space"},
                {"name": "hangup", "x": v_center + 35,  "color": self.CLR_RED,        "icon": "hangup", "label": "End"}, 
                {"name": "clear",  "x": v_center + 110, "color": self.CLR_BTN_NORMAL, "icon": "clear", "label": "Clear"},
            ]
            
            for b in btn_defs:
                dist = math.hypot(self.mouse_x - b["x"], self.mouse_y - (bar_y + 40))
                is_hover = dist < 28
                self.draw_circle_btn(imgOutput, (b["x"], bar_y + 40), 28, b["color"], b["icon"], is_hover)
                cv2.putText(imgOutput, b["label"], (b["x"] - 25, bar_y + 85), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                if self.mouse_click and is_hover:
                    if b["name"] == "back": self.final_text = self.final_text[:-1]
                    elif b["name"] == "space": self.final_text += " "; self.update_suggestions()
                    elif b["name"] == "clear": self.final_text = ""
                    elif b["name"] == "hangup": self.running = False
            
            self.mouse_click = False
            key = cv2.waitKey(1) & 0xFF
            if key == 32 and self.current_letter: 
                self.final_text += self.current_letter
                self.update_suggestions()
            elif key in [ord('1'), ord('2'), ord('3')] and self.suggestions:
                idx = key - ord('1')
                if idx < len(self.suggestions):
                    words = self.final_text.split()
                    if words:
                        words[-1] = self.suggestions[idx]
                        self.final_text = " ".join(words) + " "
                        self.suggestions = []
            elif key == ord('q'): self.running = False
            
            cv2.imshow(window_name, imgOutput)
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1: self.running = False

        self.cap.release()
        cv2.destroyAllWindows()
        self.running = False

    def stop(self): self.running = False

if __name__ == "__main__":
    SignLanguageTranslator().run()
