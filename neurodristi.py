import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import pyttsx3
import time
import threading
import pyautogui
import os
import sys
import urllib.request
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import winsound
import json

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Configuration & Storage ---
MODEL_PATH = resource_path('face_landmarker.task')
EAR_THRESHOLD = 0.20
CLICK_COOLDOWN = 1.2
MIN_ALPHA = 0.05
MAX_ALPHA = 0.25

PHRASES_FILE = resource_path("phrases.json")
DEFAULT_PHRASES = ["I need help", "Yes", "No", "Thank you", "Water please", "Food please", "Toilet"]

COMMON_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", 
    "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", 
    "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", 
    "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", 
    "make", "can", "like", "time", "no", "just", "him", "know", "take", "people", "into", 
    "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", "now", 
    "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", 
    "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", 
    "these", "give", "day", "most", "us", "water", "food", "help", "please", "need", "toilet", 
    "thank", "hello", "goodbye", "hungry", "thirsty", "pain", "sleep", "cold", "hot", "tired"
]

def load_phrases():
    if os.path.exists(PHRASES_FILE):
        try:
            with open(PHRASES_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_PHRASES.copy()

def save_phrases(phrases):
    try:
        with open(PHRASES_FILE, 'w') as f:
            json.dump(phrases, f, indent=4)
    except Exception as e:
        print(f"Error saving phrases: {e}")

def check_and_download_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading face_landmarker.task model. Please wait...")
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        try:
            urllib.request.urlretrieve(url, MODEL_PATH)
            print("Download completed successfully!")
        except Exception as e:
            print(f"Error downloading model: {e}")
            sys.exit(1)

class HoverButton(tk.Button):
    """ Custom Button with smooth hover effect and active styling """
    def __init__(self, master, **kw):
        activebackground = kw.pop("activebackground", "#00b4ff")
        activeforeground = kw.pop("activeforeground", "white")
        background = kw.get("background", "#1e293b")
        foreground = kw.get("foreground", "#ffffff")
        
        super().__init__(master, relief="flat", borderwidth=0, cursor="hand2", **kw)
        self.bind("<Enter>", lambda e: self.config(background=activebackground, foreground=activeforeground) if self['state'] != 'disabled' else None)
        self.bind("<Leave>", lambda e: self.config(background=background, foreground=foreground) if self['state'] != 'disabled' else None)

class PhraseRow(tk.Frame):
    """ Modern Speech phrases row with speaker action """
    def __init__(self, master, text, click_callback, **kw):
        super().__init__(master, bg="#0f172a", height=50, cursor="hand2", **kw)
        self.pack_propagate(False)
        self.click_callback = click_callback

        self.label = tk.Label(self, text=text, font=("Helvetica", 11, "bold"), fg="#e2e8f0", bg="#0f172a", anchor="w")
        self.label.pack(side="left", fill="both", expand=True, padx=15)

        self.speaker = tk.Label(self, text="🔊", font=("Helvetica", 12), fg="#38bdf8", bg="#0f172a")
        self.speaker.pack(side="right", padx=15)

        # Hover effects
        for widget in (self, self.label, self.speaker):
            widget.bind("<Enter>", lambda e: self.set_hover(True))
            widget.bind("<Leave>", lambda e: self.set_hover(False))
            widget.bind("<Button-1>", lambda e: self.click_callback())

    def set_hover(self, is_hovered):
        bg_col = "#1e293b" if is_hovered else "#0f172a"
        fg_col = "#00b4ff" if is_hovered else "#e2e8f0"
        self.config(bg=bg_col)
        self.label.config(bg=bg_col, fg=fg_col)
        self.speaker.config(bg=bg_col)

class Dashboard:
    def __init__(self, root, start_callback):
        self.root = root
        self.root.title("Neuro Dristi Dashboard")
        self.root.geometry("650x570")
        self.root.configure(bg="#020617")
        self.root.resizable(False, False)

        try:
            self.root.iconbitmap(resource_path("app_icon.ico"))
        except:
            pass

        self.card = tk.Frame(root, bg="#0f172a", padx=30, pady=30, bd=1, relief="solid")
        self.card.pack(expand=True, fill="both", padx=40, pady=40)

        self.title_label = tk.Label(self.card, text="NEURO DRISTI", 
                                    font=("Helvetica", 36, "bold"), fg="#00b4ff", bg="#0f172a")
        self.title_label.pack(pady=(20, 10))

        self.subtitle_label = tk.Label(self.card, text="Eye-Controlled Speech & Keyboard System", 
                                       font=("Helvetica", 14, "italic"), fg="#94a3b8", bg="#0f172a")
        self.subtitle_label.pack(pady=(0, 30))

        btn_frame = tk.Frame(self.card, bg="#0f172a")
        btn_frame.pack(pady=10)

        self.start_btn = HoverButton(btn_frame, text="START SYSTEM", 
                                     command=start_callback,
                                     font=("Helvetica", 16, "bold"),
                                     bg="#00b4ff", fg="white",
                                     activebackground="#0088cc", activeforeground="white",
                                     padx=40, pady=15)
        self.start_btn.pack(pady=10)

        self.help_btn = HoverButton(btn_frame, text="How to Use", 
                                    command=self.show_instructions,
                                    font=("Helvetica", 12),
                                    bg="#1e293b", fg="#cbd5e1",
                                    activebackground="#334155", activeforeground="white",
                                    padx=20, pady=8)
        self.help_btn.pack(pady=5)

        self.info_label = tk.Label(self.card, 
                                   text="Controls:\nHead Movement = Move Mouse | Eye Blink = Click\nPress ESC in the application to force quit", 
                                   font=("Helvetica", 10), fg="#64748b", bg="#0f172a", justify="center")
        self.info_label.pack(side="bottom", pady=10)

    def show_instructions(self):
        InstructionsDialog(self.root)

class InstructionsDialog:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("How to Use Neuro Dristi")
        self.win.geometry("520x460")
        self.win.configure(bg="#0f172a")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        x = parent.winfo_x() + (parent.winfo_width() - 520) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 460) // 2
        self.win.geometry(f"+{x}+{y}")

        title = tk.Label(self.win, text="How to Use the System", font=("Helvetica", 18, "bold"), fg="#00b4ff", bg="#0f172a")
        title.pack(pady=20)

        instructions = (
            "1. Head Movement Controls Cursor:\n"
            "   Slightly move your head up, down, left, or right.\n"
            "   The cursor on screen will trace your movements.\n\n"
            "2. Clicking Options:\n"
            "   - Eye Blink: Blink/wink firmly to click.\n"
            "   - Dwell Click: Enable in Control Panel to click by holding cursor still.\n\n"
            "3. Keyboard Floating Dot:\n"
            "   Click the blue circle button in the bottom right corner\n"
            "   to display the full-screen keyboard.\n"
            "   Click the close button on the keyboard to minimize it again.\n\n"
            "4. Mouse Actions & Custom Phrases:\n"
            "   - Choose Left, Right, Double click, or Scroll from the Control Panel.\n"
            "   - Manage custom phrases via the Phrase Manager."
        )

        txt = tk.Label(self.win, text=instructions, font=("Helvetica", 11), fg="#cbd5e1", bg="#0f172a", justify="left", wraplength=480)
        txt.pack(padx=20, pady=10)

        close_btn = HoverButton(self.win, text="Got it", command=self.win.destroy,
                                font=("Helvetica", 12, "bold"), bg="#00b4ff", fg="white",
                                activebackground="#0088cc", padx=30, pady=8)
        close_btn.pack(pady=20)

class PhraseManagerDialog:
    def __init__(self, parent, phrases, save_callback):
        self.win = tk.Toplevel(parent)
        self.win.title("Manage Custom Phrases")
        self.win.geometry("450x500")
        self.win.configure(bg="#0f172a")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        self.phrases = phrases
        self.save_callback = save_callback

        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 500) // 2
        self.win.geometry(f"+{x}+{y}")

        title = tk.Label(self.win, text="Phrase Manager", font=("Helvetica", 16, "bold"), fg="#00b4ff", bg="#0f172a")
        title.pack(pady=15)

        self.listbox = tk.Listbox(self.win, bg="#020617", fg="white", selectbackground="#00b4ff", font=("Helvetica", 11), bd=0, highlightthickness=1, highlightcolor="#1e293b")
        self.listbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.refresh_listbox()

        entry_frame = tk.Frame(self.win, bg="#0f172a")
        entry_frame.pack(fill="x", padx=20, pady=10)

        self.new_phrase_entry = tk.Entry(entry_frame, font=("Helvetica", 12), bg="#020617", fg="white", insertbackground="white", bd=1, relief="solid")
        self.new_phrase_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        add_btn = HoverButton(entry_frame, text="Add", font=("Helvetica", 10, "bold"), bg="#00b4ff", fg="white", activebackground="#0088cc", command=self.add_phrase, padx=15)
        add_btn.pack(side="right")

        control_frame = tk.Frame(self.win, bg="#0f172a")
        control_frame.pack(fill="x", padx=20, pady=15)

        del_btn = HoverButton(control_frame, text="Delete Selected", font=("Helvetica", 11, "bold"), bg="#ff3b30", fg="white", activebackground="#cc2e24", command=self.delete_phrase)
        del_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        save_btn = HoverButton(control_frame, text="Save & Apply", font=("Helvetica", 11, "bold"), bg="#30d158", fg="white", activebackground="#249d42", command=self.save_and_close)
        save_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for p in self.phrases:
            self.listbox.insert(tk.END, p)

    def add_phrase(self):
        val = self.new_phrase_entry.get().strip()
        if val:
            self.phrases.append(val)
            self.new_phrase_entry.delete(0, tk.END)
            self.refresh_listbox()

    def delete_phrase(self):
        selected = self.listbox.curselection()
        if selected:
            idx = selected[0]
            del self.phrases[idx]
            self.refresh_listbox()

    def save_and_close(self):
        self.save_callback(self.phrases)
        self.win.destroy()

class CalibrationDialog:
    def __init__(self, parent, on_complete_callback):
        self.win = tk.Toplevel(parent)
        self.win.attributes("-fullscreen", True)
        self.win.configure(bg="#020617")
        self.win.attributes("-topmost", True)
        
        self.on_complete_callback = on_complete_callback
        self.points = ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right", "Center"]
        self.current_point_idx = 0
        self.collected_coords = []
        
        self.canvas = tk.Canvas(self.win, bg="#020617", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.w = self.win.winfo_screenwidth()
        self.h = self.win.winfo_screenheight()

        self.draw_step()

    def draw_step(self):
        self.canvas.delete("all")
        if self.current_point_idx >= len(self.points):
            self.finish_calibration()
            return
            
        pt = self.points[self.current_point_idx]
        
        margin = 100
        if pt == "Top-Left":
            cx, cy = margin, margin
        elif pt == "Top-Right":
            cx, cy = self.w - margin, margin
        elif pt == "Bottom-Left":
            cx, cy = margin, self.h - margin
        elif pt == "Bottom-Right":
            cx, cy = self.w - margin, self.h - margin
        else: 
            cx, cy = self.w // 2, self.h // 2
            
        self.canvas.create_oval(cx - 25, cy - 25, cx + 25, cy + 25, fill="#00b4ff", outline="white", width=3)
        self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="white")
        
        instr = f"STEP {self.current_point_idx + 1}/5: Look at the target and BLINK to calibrate {pt}"
        self.canvas.create_text(self.w // 2, self.h // 2 + 80 if pt == "Center" else self.h // 2, 
                                 text=instr, fill="white", font=("Helvetica", 20, "bold"), justify="center")

    def capture_point(self, nose_x, nose_y):
        self.collected_coords.append((nose_x, nose_y))
        self.current_point_idx += 1
        self.win.after(0, self.draw_step)

    def finish_calibration(self):
        tl, tr, bl, br, c = self.collected_coords
        min_x = min(tl[0], bl[0])
        max_x = max(tr[0], br[0])
        min_y = min(tl[1], tr[1])
        max_y = max(bl[1], br[1])
        self.win.after(0, self.safe_exit_calibration, min_x, max_x, min_y, max_y)

    def safe_exit_calibration(self, min_x, max_x, min_y, max_y):
        self.canvas.delete("all")
        self.canvas.create_text(self.w // 2, self.h // 2 - 50, 
                                 text="Calibration Successful! ✅", 
                                 fill="#30d158", font=("Helvetica", 28, "bold"), justify="center")
        self.canvas.create_text(self.w // 2, self.h // 2 + 10, 
                                 text="Eye-tracking limits have been calculated and saved.", 
                                 fill="#cbd5e1", font=("Helvetica", 14), justify="center")
        
        self.on_complete_callback(min_x, max_x, min_y, max_y)

        exit_btn = HoverButton(self.win, text="EXIT CALIBRATION", font=("Helvetica", 14, "bold"),
                               bg="#00b4ff", fg="white", activebackground="#0088cc",
                               command=self.win.destroy, padx=40, pady=15)
        self.canvas.create_window(self.w // 2, self.h // 2 + 100, window=exit_btn)

class NeuroDristi:
    def __init__(self):
        # MediaPipe Setup
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            num_faces=1)
        self.detector = vision.FaceLandmarker.create_from_options(options)
        
        # State variables
        self.tts_busy = False
        self.keyboard_text = ""
        self.alarm_active = False
        
        # Tracking config
        self.screen_w, self.screen_h = pyautogui.size()
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        
        self.last_x, self.last_y = None, None
        self.range_x = [0.38, 0.62]
        self.range_y = [0.38, 0.62]
        self.last_click_time = 0

        self.latest_frame = None
        self.running = True

        # Custom phrases config
        self.phrases = load_phrases()

        # Dwell click tracking variables
        self.dwell_enabled = False
        self.dwell_x, self.dwell_y = 0, 0
        self.dwell_start_time = time.time()
        self.dwell_duration = 1.2

        # Mouse click types
        self.active_click_type = "left"

        # Calibration state
        self.active_calibration = None

        # Keyboard structure
        self.esp_connected = False
        self.iot_buttons = []
        self.kb_rows = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'BS'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '.', ',', 'CLR'],
            ['SPACE', 'ENTER']
        ]

    def speak(self, text):
        if not self.tts_busy and text.strip():
            self.tts_busy = True
            def _speak_thread():
                try:
                    engine = pyttsx3.init()
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                except Exception as e:
                    print(f"TTS Error: {e}")
                finally:
                    self.tts_busy = False
            threading.Thread(target=_speak_thread, daemon=True).start()

    def get_ear(self, landmarks):
        p2, p6, p1, p4 = landmarks[159], landmarks[145], landmarks[33], landmarks[133]
        dist_v = np.sqrt((p2.x - p6.x)**2 + (p2.y - p6.y)**2)
        dist_h = np.sqrt((p1.x - p4.x)**2 + (p1.y - p4.y)**2)
        return dist_v / dist_h if dist_h != 0 else 0

    def dynamic_smoothing(self, target, last):
        if last is None: return target
        dist = np.abs(target - last)
        alpha = np.clip(dist * 2.0, MIN_ALPHA, MAX_ALPHA)
        return last + alpha * (target - last)

    def trigger_emergency_alarm(self):
        if self.alarm_active:
            self.alarm_active = False
            if hasattr(self, 'alarm_btn'):
                self.alarm_btn.config(text="🚨 EMERGENCY ALARM", bg="#ff3b30", activebackground="#cc2e24")
        else:
            self.alarm_active = True
            if hasattr(self, 'alarm_btn'):
                self.alarm_btn.config(text="🔊 STOP ALARM", bg="#ff9500", activebackground="#e08200")
            
            def _alarm_thread():
                while self.alarm_active and self.running:
                    winsound.Beep(1300, 250)
                    if not self.alarm_active: break
                    winsound.Beep(900, 250)
            threading.Thread(target=_alarm_thread, daemon=True).start()

    def set_click_type(self, click_type):
        self.active_click_type = click_type
        for ct, btn in self.click_type_btns.items():
            if ct == click_type:
                btn.config(bg="#00b4ff", activebackground="#0088cc")
            else:
                btn.config(bg="#1a2035", activebackground="#334155")

    def execute_mouse_action(self):
        if (time.time() - self.last_click_time) < CLICK_COOLDOWN:
            return
        self.last_click_time = time.time()
        
        if self.active_click_type == "left":
            pyautogui.click()
        elif self.active_click_type == "right":
            pyautogui.rightClick()
            self.set_click_type("left") 
        elif self.active_click_type == "double":
            pyautogui.doubleClick()
            self.set_click_type("left") 
        elif self.active_click_type == "scroll":
            pyautogui.scroll(-300)
            self.set_click_type("left") 

    def tracking_worker(self):
        # On Windows, CAP_DSHOW is often much faster and more reliable to initialize webcams.
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
            
        consecutive_failures = 0
        while self.running:
            if not cap.isOpened():
                print("Camera failed to open. Retrying...")
                time.sleep(1.0)
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(0)
                continue

            try:
                success, frame = cap.read()
                if not success:
                    consecutive_failures += 1
                    if consecutive_failures > 30:
                        print("Camera read failed repeatedly. Re-initializing camera...")
                        cap.release()
                        time.sleep(1.0)
                        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                        if not cap.isOpened():
                            cap = cv2.VideoCapture(0)
                        consecutive_failures = 0
                    else:
                        time.sleep(0.01)
                    continue
                
                consecutive_failures = 0
                frame = cv2.flip(frame, 1)
                self.latest_frame = frame
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = self.detector.detect(mp_image)

                if detection_result.face_landmarks:
                    landmarks = detection_result.face_landmarks[0]
                    nose = landmarks[1]
                    
                    tx = np.interp(nose.x, (self.range_x[0], self.range_x[1]), (0, self.screen_w))
                    ty = np.interp(nose.y, (self.range_y[0], self.range_y[1]), (0, self.screen_h))
                    self.last_x = self.dynamic_smoothing(tx, self.last_x)
                    self.last_y = self.dynamic_smoothing(ty, self.last_y)
                    
                    px, py = int(np.clip(self.last_x, 0, self.screen_w - 1)), int(np.clip(self.last_y, 0, self.screen_h - 1))
                    pyautogui.moveTo(px, py, _pause=False)
                    
                    is_blink = self.get_ear(landmarks) < EAR_THRESHOLD
                    if is_blink and (time.time() - self.last_click_time) > CLICK_COOLDOWN:
                        if self.active_calibration:
                            self.last_click_time = time.time()
                            self.active_calibration.capture_point(nose.x, nose.y)
                        else:
                            self.execute_mouse_action()

                    if self.dwell_enabled and not self.active_calibration:
                        dist = np.sqrt((px - self.dwell_x)**2 + (py - self.dwell_y)**2)
                        if dist < 20:
                            if (time.time() - self.dwell_start_time) > self.dwell_duration:
                                self.execute_mouse_action()
                                self.dwell_start_time = time.time() + 1.0 
                        else:
                            self.dwell_x, self.dwell_y = px, py
                            self.dwell_start_time = time.time()

            except Exception as e:
                print(f"Error in tracking worker: {e}")
                time.sleep(0.1)

            time.sleep(0.01)
        cap.release()

    def send_esp_cmd(self, path):
        def _request_thread():
            url = f"http://192.168.4.1{path}"
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=1.5) as response:
                    response.read()
            except Exception as e:
                print(f"ESP Command Error on {path}: {e}")
        threading.Thread(target=_request_thread, daemon=True).start()

    def connection_checker(self):
        while self.running:
            connected = False
            fire_alert_status = False
            edge_alert_status = False
            
            # Step 1: Check basic connection to root page (available on all firmware versions)
            try:
                req = urllib.request.Request("http://192.168.4.1/", method="GET")
                with urllib.request.urlopen(req, timeout=0.8) as response:
                    if response.status == 200:
                        connected = True
            except Exception:
                pass
            
            # Step 2: Try to get status if connected (might fail/404 if older firmware is still running)
            if connected:
                try:
                    req_status = urllib.request.Request("http://192.168.4.1/status", method="GET")
                    with urllib.request.urlopen(req_status, timeout=0.8) as response_status:
                        if response_status.status == 200:
                            data = json.loads(response_status.read().decode('utf-8'))
                            if data.get("fireAlarm") == 1:
                                fire_alert_status = True
                            if data.get("edgeDetected") == 1:
                                edge_alert_status = True
                except Exception:
                    pass
            
            self.esp_connected = connected
            
            if fire_alert_status and not self.alarm_active:
                try:
                    self.root_ui.after(0, self.trigger_emergency_alarm)
                except Exception:
                    pass
                    
            try:
                self.root_ui.after(0, self.update_connection_ui)
            except Exception:
                pass
            time.sleep(3.0)

    def update_connection_ui(self):
        if not hasattr(self, 'conn_label') or not self.conn_label.winfo_exists():
            return
        if self.esp_connected:
            self.conn_label.config(text="ESP32 Status: Connected •", fg="#30d158")
            self.sig_label.config(text="Signal: Strong 📶", fg="#30d158")
            for btn in self.iot_buttons:
                btn.config(state="normal", bg="#0a192f")
            self.stop_btn.config(state="normal", bg="#4a0e17")
            self.sw_light_on.config(bg="#30d158")
            self.sw_light_off.config(bg="#ff9500")
            self.sw_fan_on.config(bg="#30d158")
            self.sw_fan_off.config(bg="#ff9500")
        else:
            self.conn_label.config(text="ESP32 Status: Disconnected •", fg="#ff3b30")
            self.sig_label.config(text="Signal: None 📶", fg="#64748b")
            for btn in self.iot_buttons:
                btn.config(state="disabled", bg="#0f172a")
            self.sw_light_on.config(bg="#1e293b")
            self.sw_light_off.config(bg="#1e293b")
            self.sw_fan_on.config(bg="#1e293b")
            self.sw_fan_off.config(bg="#1e293b")

    def refresh_phrase_panel(self):
        for widget in self.phrases_frame.winfo_children():
            widget.destroy()

        for p in self.phrases:
            row = PhraseRow(self.phrases_frame, text=p, click_callback=lambda phrase=p: self.speak(phrase))
            row.pack(fill="x", pady=4, padx=5)

    def on_phrases_saved(self, new_phrases):
        self.phrases = new_phrases
        save_phrases(new_phrases)
        self.refresh_phrase_panel()

    def start_calibration(self):
        self.active_calibration = CalibrationDialog(self.root_ui, self.complete_calibration)

    def complete_calibration(self, min_x, max_x, min_y, max_y):
        self.range_x = [min_x, max_x]
        self.range_y = [min_y, max_y]
        self.active_calibration = None

    def toggle_dwell_click(self):
        self.dwell_enabled = self.dwell_var.get()

    def build_ui(self, root):
        self.root_ui = root
        self.root_ui.title("Neuro Dristi Main Panel")
        w, h = 1250, 830
        pos_x = (self.screen_w - w) // 2
        pos_y = (self.screen_h - h) // 2
        self.root_ui.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
        self.root_ui.configure(bg="#020617")
        self.root_ui.resizable(False, False)
        
        self.root_ui.protocol("WM_DELETE_WINDOW", self.close_application)
        self.root_ui.attributes("-topmost", True)

        # Three-Column Card Layout
        self.col_left = tk.Frame(self.root_ui, bg="#0f172a", bd=1, relief="solid", padx=15, pady=15)
        self.col_left.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=(20, 80))

        self.col_mid = tk.Frame(self.root_ui, bg="#0f172a", bd=1, relief="solid", padx=15, pady=15)
        self.col_mid.pack(side="left", fill="both", expand=True, padx=10, pady=(20, 80))

        self.col_right = tk.Frame(self.root_ui, bg="#0f172a", bd=1, relief="solid", padx=15, pady=15)
        self.col_right.pack(side="right", fill="both", expand=True, padx=(10, 20), pady=(20, 80))

        # ================= COLUMN 1: Brand & Control settings =================
        # Brand container
        brand_frame = tk.Frame(self.col_left, bg="#0f172a")
        brand_frame.pack(fill="x", pady=(0, 10))
        
        eye_logo = tk.Label(brand_frame, text="👁", font=("Helvetica", 32), fg="#00b4ff", bg="#0f172a")
        eye_logo.pack(side="left", padx=(5, 10))
        
        brand_text_frame = tk.Frame(brand_frame, bg="#0f172a")
        brand_text_frame.pack(side="left", fill="both", expand=True)
        
        title_label = tk.Label(brand_text_frame, text="NEURO DRISTI", font=("Helvetica", 18, "bold"), fg="#ffffff", bg="#0f172a", anchor="w")
        title_label.pack(fill="x")
        
        sub_label = tk.Label(brand_text_frame, text="AI Vision • Voice • Control", font=("Helvetica", 10), fg="#64748b", bg="#0f172a", anchor="w")
        sub_label.pack(fill="x")

        # Camera Display Frame
        self.cam_frame = tk.Frame(self.col_left, width=320, height=200, bg="#020617", highlightbackground="#00b4ff", highlightthickness=1)
        self.cam_frame.pack(pady=5)
        self.cam_frame.pack_propagate(False)
        self.cam_label = tk.Label(self.cam_frame, bg="#020617")
        self.cam_label.pack(fill="both", expand=True)

        # Calibration & Phrase config buttons
        top_row_frame = tk.Frame(self.col_left, bg="#0f172a")
        top_row_frame.pack(fill="x", pady=5)

        self.calib_btn = HoverButton(top_row_frame, text="🎯 Calibrate System", font=("Helvetica", 10, "bold"),
                                     bg="#0056b3", fg="white", activebackground="#00b4ff",
                                     command=self.start_calibration, height=2)
        self.calib_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.phrases_mgr_btn = HoverButton(top_row_frame, text="💬 Phrase Manager", font=("Helvetica", 10, "bold"),
                                           bg="#1e293b", fg="white", activebackground="#334155",
                                           command=lambda: PhraseManagerDialog(self.root_ui, self.phrases.copy(), self.on_phrases_saved), height=2)
        self.phrases_mgr_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))



        # Open Keyboard Action Button
        self.keyboard_btn = HoverButton(self.col_left, text="⌨   OPEN KEYBOARD", font=("Helvetica", 11, "bold"),
                                        bg="#020617", fg="#00b4ff", activebackground="#00b4ff", activeforeground="white",
                                        command=self.show_full_keyboard, height=2, bd=1, highlightbackground="#00b4ff")
        self.keyboard_btn.pack(fill="x", pady=10)

        # EMERGENCY ALARM Button (Full width)
        self.alarm_btn = HoverButton(self.col_left, text="🚨   EMERGENCY ALARM", font=("Helvetica", 11, "bold"),
                                     bg="#ff3b30", fg="white", activebackground="#cc2e24",
                                     command=self.trigger_emergency_alarm, height=2)
        self.alarm_btn.pack(fill="x", pady=10)

        # Exit application button
        exit_btn = HoverButton(self.col_left, text="⏻   EXIT SYSTEM", font=("Helvetica", 12, "bold"),
                               bg="#1a2035", fg="white", activebackground="#ff3b30", activeforeground="white",
                               command=self.close_application, height=2)
        exit_btn.pack(fill="x", pady=10)

        # ================= COLUMN 2: Wheelchair & IoT Controls =================
        iot_hdr_frame = tk.Frame(self.col_mid, bg="#0f172a")
        iot_hdr_frame.pack(fill="x", pady=(0, 10))
        
        wc_logo = tk.Label(iot_hdr_frame, text="♿", font=("Helvetica", 28), fg="#00b4ff", bg="#0f172a")
        wc_logo.pack(side="left", padx=(5, 10))
        
        wc_hdr_text = tk.Frame(iot_hdr_frame, bg="#0f172a")
        wc_hdr_text.pack(side="left", fill="both", expand=True)
        
        iot_title = tk.Label(wc_hdr_text, text="WHEELCHAIR & HOME CONTROL", font=("Helvetica", 14, "bold"), fg="#00b4ff", bg="#0f172a", anchor="w")
        iot_title.pack(fill="x")
        
        iot_subtitle = tk.Label(wc_hdr_text, text="Movement & Home Automation", font=("Helvetica", 10), fg="#64748b", bg="#0f172a", anchor="w")
        iot_subtitle.pack(fill="x")

        # Wheelchair movement controller box
        m_frame = tk.LabelFrame(self.col_mid, text="♿  Wheelchair Movement Control", font=("Helvetica", 11, "bold"), fg="#00b4ff", bg="#0f172a", padx=10, pady=15, bd=1)
        m_frame.pack(fill="x", pady=5)

        # Helper method to bind hover events to start working on hover immediately
        def bind_hover_cmd(btn, path):
            def on_enter(e):
                if btn['state'] != 'disabled':
                    # Highlight colors
                    btn.config(bg="#00b4ff", fg="white")
                    # Send command immediately without click
                    self.send_esp_cmd(path)
            btn.bind("<Enter>", on_enter)

            # Safety stop on leave
            if path != "/S":
                def on_leave(e):
                    if btn['state'] != 'disabled':
                        # Restore default colors
                        btn.config(bg="#0a192f", fg="white")
                        # Send stop command immediately
                        self.send_esp_cmd("/S")
                btn.bind("<Leave>", on_leave)

        fwd_btn = HoverButton(m_frame, text="FWD ⬆", font=("Helvetica", 11, "bold"), bg="#0a192f", fg="white", activebackground="#00b4ff",
                              command=lambda: self.send_esp_cmd("/F"), width=10, height=3)
        fwd_btn.grid(row=0, column=1, pady=5, padx=5)
        bind_hover_cmd(fwd_btn, "/F")

        left_btn = HoverButton(m_frame, text="LEFT ⬅", font=("Helvetica", 11, "bold"), bg="#0a192f", fg="white", activebackground="#00b4ff",
                               command=lambda: self.send_esp_cmd("/L"), width=10, height=3)
        left_btn.grid(row=1, column=0, pady=5, padx=5)
        bind_hover_cmd(left_btn, "/L")

        self.stop_btn = HoverButton(m_frame, text="STOP ❌", font=("Helvetica", 11, "bold"), bg="#4a0e17", fg="white", activebackground="#cc2e24",
                               command=lambda: self.send_esp_cmd("/S"), width=10, height=3)
        self.stop_btn.grid(row=1, column=1, pady=5, padx=5)
        bind_hover_cmd(self.stop_btn, "/S")

        right_btn = HoverButton(m_frame, text="RIGHT ➡", font=("Helvetica", 11, "bold"), bg="#0a192f", fg="white", activebackground="#00b4ff",
                                command=lambda: self.send_esp_cmd("/R"), width=10, height=3)
        right_btn.grid(row=1, column=2, pady=5, padx=5)
        bind_hover_cmd(right_btn, "/R")

        rev_btn = HoverButton(m_frame, text="REV ⬇", font=("Helvetica", 11, "bold"), bg="#0a192f", fg="white", activebackground="#00b4ff",
                              command=lambda: self.send_esp_cmd("/B"), width=10, height=3)
        rev_btn.grid(row=2, column=1, pady=5, padx=5)
        bind_hover_cmd(rev_btn, "/B")

        m_frame.grid_columnconfigure(0, weight=1)
        m_frame.grid_columnconfigure(1, weight=1)
        m_frame.grid_columnconfigure(2, weight=1)

        self.iot_buttons.extend([fwd_btn, left_btn, self.stop_btn, right_btn, rev_btn])

        # Home automation frame (Two rows of big switches)
        h_frame = tk.LabelFrame(self.col_mid, text="🏠  Home Automation Control", font=("Helvetica", 11, "bold"), fg="#00b4ff", bg="#0f172a", padx=15, pady=15, bd=1)
        h_frame.pack(fill="both", expand=True, pady=5)

        # Row 0: Lights Control
        self.sw_light_on = HoverButton(h_frame, text="LIGHT ON 💡", font=("Helvetica", 11, "bold"), bg="#30d158", fg="white", activebackground="#249d42",
                                       command=lambda: self.send_esp_cmd("/home/light_on"), width=12, height=3)
        self.sw_light_on.grid(row=0, column=0, pady=10, padx=10, sticky="nsew")

        self.sw_light_off = HoverButton(h_frame, text="LIGHT OFF 🔌", font=("Helvetica", 11, "bold"), bg="#ff9500", fg="white", activebackground="#e08200",
                                        command=lambda: self.send_esp_cmd("/home/light_off"), width=12, height=3)
        self.sw_light_off.grid(row=0, column=1, pady=10, padx=10, sticky="nsew")

        # Row 1: Fan Control
        self.sw_fan_on = HoverButton(h_frame, text="FAN ON 🌀", font=("Helvetica", 11, "bold"), bg="#30d158", fg="white", activebackground="#249d42",
                                     command=lambda: self.send_esp_cmd("/home/fan_on"), width=12, height=3)
        self.sw_fan_on.grid(row=1, column=0, pady=10, padx=10, sticky="nsew")

        self.sw_fan_off = HoverButton(h_frame, text="FAN OFF 🛑", font=("Helvetica", 11, "bold"), bg="#ff9500", fg="white", activebackground="#e08200",
                                      command=lambda: self.send_esp_cmd("/home/fan_off"), width=12, height=3)
        self.sw_fan_off.grid(row=1, column=1, pady=10, padx=10, sticky="nsew")

        h_frame.grid_columnconfigure(0, weight=1)
        h_frame.grid_columnconfigure(1, weight=1)
        h_frame.grid_rowconfigure(0, weight=1)
        h_frame.grid_rowconfigure(1, weight=1)

        self.iot_buttons.extend([self.sw_light_on, self.sw_light_off, self.sw_fan_on, self.sw_fan_off])

        # ================= COLUMN 3: Speech Board & Status indicators =================
        phr_hdr_frame = tk.Frame(self.col_right, bg="#0f172a")
        phr_hdr_frame.pack(fill="x", pady=(0, 10))
        
        chat_logo = tk.Label(phr_hdr_frame, text="💬", font=("Helvetica", 28), fg="#00b4ff", bg="#0f172a")
        chat_logo.pack(side="left", padx=(5, 10))
        
        chat_hdr_text = tk.Frame(phr_hdr_frame, bg="#0f172a")
        chat_hdr_text.pack(side="left", fill="both", expand=True)
        
        phrases_title = tk.Label(chat_hdr_text, text="Quick Phrases (Click to Speak)", font=("Helvetica", 13, "bold"), fg="#ffffff", bg="#0f172a", anchor="w")
        phrases_title.pack(fill="x")
        
        self.phrases_frame = tk.Frame(self.col_right, bg="#0f172a")
        self.phrases_frame.pack(fill="both", expand=True, pady=5)
        self.refresh_phrase_panel()

        # Connection status dashboard box
        status_box = tk.LabelFrame(self.col_right, text="Network & Hardware Indicators", font=("Helvetica", 10, "bold"), fg="#00b4ff", bg="#0f172a", padx=15, pady=10, bd=1)
        status_box.pack(fill="x", pady=5)

        self.conn_label = tk.Label(status_box, text="ESP32 Status: Checking •", font=("Helvetica", 11, "bold"), fg="#ff9500", bg="#0f172a", anchor="w")
        self.conn_label.pack(fill="x", pady=2)

        ip_label = tk.Label(status_box, text="IP Address: 192.168.4.1", font=("Helvetica", 9), fg="#cbd5e1", bg="#0f172a", anchor="w")
        ip_label.pack(fill="x", pady=2)

        self.sig_label = tk.Label(status_box, text="Signal: None 📶", font=("Helvetica", 9), fg="#64748b", bg="#0f172a", anchor="w")
        self.sig_label.pack(fill="x", pady=2)

        # WiFi & Battery Status
        stat_row = tk.Frame(self.col_right, bg="#0f172a")
        stat_row.pack(fill="x", pady=10)
        
        wf_lbl = tk.Label(stat_row, text="📶  Wi-Fi: Connected", font=("Helvetica", 10), fg="#cbd5e1", bg="#0f172a")
        wf_lbl.pack(side="left", padx=10)
        
        bat_lbl = tk.Label(stat_row, text="🔋  Battery: 82%", font=("Helvetica", 10), fg="#30d158", bg="#0f172a")
        bat_lbl.pack(side="right", padx=10)

        # Bind Escape key to quit
        self.root_ui.bind("<Escape>", lambda e: self.close_application())

        # Build Keyboard Windows
        self.build_keyboard_dot()
        self.build_full_keyboard()

        # Start Camera frame updating
        self.update_camera_widget()

        # Start EKG custom logo canvas at the bottom center of screen
        self.build_ekg_banner()

        # Start Tracking thread
        self.tracking_thread = threading.Thread(target=self.tracking_worker, daemon=True)
        self.tracking_thread.start()

        # Start ESP32 Connection Checker thread
        self.conn_thread = threading.Thread(target=self.connection_checker, daemon=True)
        self.conn_thread.start()

        self.root_ui.mainloop()

    def build_ekg_banner(self):
        """ Draws the custom EKG pulse banner at the very bottom center of the dashboard """
        banner = tk.Frame(self.root_ui, bg="#020617", height=70)
        banner.pack(side="bottom", fill="x", pady=(0, 10))
        banner.pack_propagate(False)

        cv = tk.Canvas(banner, bg="#020617", height=70, highlightthickness=0)
        cv.pack(fill="both", expand=True)

        w = self.root_ui.winfo_screenwidth()
        
        # Draw central EKG wave on left and right sides
        # Left wave
        points_l = [(50, 35), (200, 35), (210, 20), (220, 50), (230, 10), (240, 60), (250, 35), (400, 35)]
        for i in range(len(points_l)-1):
            cv.create_line(points_l[i][0], points_l[i][1], points_l[i+1][0], points_l[i+1][1], fill="#0056b3", width=2)
            
        # Right wave
        points_r = [(800, 35), (950, 35), (960, 20), (970, 50), (980, 10), (990, 60), (1000, 35), (1150, 35)]
        for i in range(len(points_r)-1):
            cv.create_line(points_r[i][0], points_r[i][1], points_r[i+1][0], points_r[i+1][1], fill="#0056b3", width=2)

        # Central text
        cv.create_text(600, 25, text="NEURO     DRISTI", fill="#ffffff", font=("Helvetica", 18, "bold"))
        cv.create_text(600, 50, text="Empowering Lives with Vision & Intelligence", fill="#64748b", font=("Helvetica", 9, "bold"))

        # Draws central glowing brain glyph
        cv.create_text(600, 25, text="🧠", fill="#00b4ff", font=("Helvetica", 20))

    def update_camera_widget(self):
        if self.running and self.latest_frame is not None:
            try:
                frame_rgb = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (320, 200))
                im = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=im)
                self.cam_label.imgtk = imgtk
                self.cam_label.configure(image=imgtk)
            except Exception as e:
                print(f"Cam Widget update error: {e}")
        
        if self.running:
            self.root_ui.after(30, self.update_camera_widget)

    def build_keyboard_dot(self):
        self.dot_win = tk.Toplevel(self.root_ui)
        self.dot_win.overrideredirect(True)
        self.dot_win.protocol("WM_DELETE_WINDOW", self.close_application)
        
        dot_w, dot_h = 80, 80
        pos_x = self.screen_w - dot_w - 40
        pos_y = self.screen_h - dot_h - 100
        self.dot_win.geometry(f"{dot_w}x{dot_h}+{pos_x}+{pos_y}")
        self.dot_win.configure(bg="#020617")
        self.dot_win.wm_attributes("-transparentcolor", "#020617")
        self.dot_win.attributes("-topmost", True)

        self.dot_canvas = tk.Canvas(self.dot_win, width=dot_w, height=dot_h, bg="#020617", highlightthickness=0)
        self.dot_canvas.pack()

        self.dot_circle = self.dot_canvas.create_oval(5, 5, 75, 75, fill="#00b4ff", outline="#ffffff", width=2)
        self.dot_text = self.dot_canvas.create_text(40, 40, text="⌨", fill="white", font=("Helvetica", 24))

        self.dot_canvas.bind("<Button-1>", lambda e: self.show_full_keyboard())
        
        def on_enter(e):
            self.dot_canvas.itemconfig(self.dot_circle, fill="#00e5ff")
        def on_leave(e):
            self.dot_canvas.itemconfig(self.dot_circle, fill="#00b4ff")

        self.dot_canvas.bind("<Enter>", on_enter)
        self.dot_canvas.bind("<Leave>", on_leave)

    def build_full_keyboard(self):
        self.kb_win = tk.Toplevel(self.root_ui)
        self.kb_win.overrideredirect(True)
        self.kb_win.protocol("WM_DELETE_WINDOW", self.close_application)
        self.kb_win.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.kb_win.configure(bg="#020617")
        self.kb_win.attributes("-topmost", True)
        self.kb_win.withdraw()

        container = tk.Frame(self.kb_win, bg="#0f172a", bd=1, relief="solid", padx=20, pady=20)
        container.place(relx=0.5, rely=0.5, anchor="center", width=1000, height=690)

        header_frame = tk.Frame(container, bg="#0f172a")
        header_frame.pack(fill="x", pady=(0, 10))

        title = tk.Label(header_frame, text="TYPING STATION", font=("Helvetica", 16, "bold"), fg="#00b4ff", bg="#0f172a")
        title.pack(side="left")

        close_btn = HoverButton(header_frame, text="❌ CLOSE KEYBOARD", font=("Helvetica", 11, "bold"),
                                bg="#1e293b", fg="#ff453a", activebackground="#ff453a", activeforeground="white",
                                command=self.hide_full_keyboard, padx=15, pady=5)
        close_btn.pack(side="right")

        self.text_display = tk.Label(container, text="|", font=("Helvetica", 24, "bold"), fg="white", bg="#020617",
                                     height=2, anchor="w", padx=20, relief="solid", bd=1)
        self.text_display.pack(fill="x", pady=5)

        self.preds_frame = tk.Frame(container, bg="#0f172a")
        self.preds_frame.pack(fill="x", pady=5)
        
        self.pred_btns = []
        for i in range(4):
            btn = HoverButton(self.preds_frame, text="", font=("Helvetica", 12, "italic"),
                              bg="#1e293b", fg="#94a3b8", activebackground="#00b4ff", height=1)
            btn.pack(side="left", fill="x", expand=True, padx=4)
            self.pred_btns.append(btn)
        
        self.update_autocomplete_predictions()

        grid_frame = tk.Frame(container, bg="#0f172a")
        grid_frame.pack(fill="both", expand=True, pady=5)

        for r, row in enumerate(self.kb_rows):
            row_frame = tk.Frame(grid_frame, bg="#0f172a")
            row_frame.pack(pady=4)

            for val in row:
                btn_w = 6
                btn_h = 2
                btn_bg = "#1a2035"
                active_bg = "#00b4ff"

                if val == 'SPACE':
                    btn_w = 30
                    btn_bg = "#1e293b"
                elif val == 'ENTER':
                    btn_w = 15
                    btn_bg = "#30d158"
                    active_bg = "#249d42"
                elif val in ['BS', 'CLR']:
                    btn_bg = "#ff9500"
                    active_bg = "#e08200"

                btn = HoverButton(row_frame, text=val, font=("Helvetica", 14, "bold"), width=btn_w, height=btn_h,
                                  bg=btn_bg, fg="white", activebackground=active_bg,
                                  command=lambda v=val: self.key_press(v))
                btn.pack(side="left", padx=4)

    def update_autocomplete_predictions(self):
        words = self.keyboard_text.strip().split(" ")
        current_word = words[-1].lower() if words else ""
        
        predictions = []
        if current_word:
            predictions = [w for w in COMMON_WORDS if w.startswith(current_word)]
            predictions = predictions[:4]
            
        for i in range(4):
            if i < len(predictions):
                pred_word = predictions[i]
                self.pred_btns[i].config(text=pred_word, state="normal", bg="#1e293b",
                                         command=lambda w=pred_word: self.select_prediction(w))
            else:
                self.pred_btns[i].config(text="", state="disabled", bg="#0f172a")

    def select_prediction(self, word):
        words = self.keyboard_text.strip().split(" ")
        if words:
            words[-1] = word
            self.keyboard_text = " ".join(words) + " "
        else:
            self.keyboard_text = word + " "
            
        self.text_display.config(text=self.keyboard_text + "|")
        self.update_autocomplete_predictions()

    def show_full_keyboard(self):
        self.dot_win.withdraw()
        self.kb_win.deiconify()

    def hide_full_keyboard(self):
        self.kb_win.withdraw()
        self.dot_win.deiconify()

    def key_press(self, val):
        if val == 'BS':
            self.keyboard_text = self.keyboard_text[:-1]
        elif val == 'CLR':
            self.keyboard_text = ""
        elif val == 'SPACE':
            self.keyboard_text += " "
        elif val == 'ENTER':
            self.speak(self.keyboard_text)
        else:
            self.keyboard_text += val
        
        self.text_display.config(text=self.keyboard_text + "|")
        self.update_autocomplete_predictions()

    def close_application(self):
        self.running = False
        self.alarm_active = False
        try:
            self.detector.close()
        except:
            pass
        os._exit(0)

def main():
    check_and_download_model()
    
    root = tk.Tk()
    app_engine = NeuroDristi()
    
    def start_tracking():
        for widget in root.winfo_children():
            widget.destroy()
        app_engine.build_ui(root)

    Dashboard(root, start_tracking)
    root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))
    root.mainloop()

if __name__ == "__main__":
    main()
