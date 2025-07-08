import tkinter as tk
from tkinter import ttk
import pyautogui
import cv2
import numpy as np
from PIL import Image, ImageTk
import time
import mss
from dataclasses import dataclass

class AreaSelector:
    def __init__(self, callback):
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.current_x = None
        self.current_y = None
        self.selection_active = False
        
    @staticmethod
    def clean_screenshot():
        """Minimizza tutte le finestre Tkinter, attende e cattura uno screenshot pulito con mss."""
        # Minimizza tutte le finestre Tkinter
        if tk._default_root:
            for widget in tk._default_root.children.values():
                if isinstance(widget, tk.Tk):
                    widget.iconify()
                    widget.update_idletasks()
                    widget.update()
        time.sleep(1.0)
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)
            img = img[..., :3]
            screenshot = Image.fromarray(img)
        return screenshot
        
    def start_selection(self):
        """Avvia la selezione dell'area con overlay trasparente"""
        # Nascondi la finestra principale (se esiste)
        main_root = None
        for widget in tk._default_root.children.values():
            if isinstance(widget, tk.Tk):
                main_root = widget
                break
        if main_root:
            main_root.iconify()
            main_root.update_idletasks()
            main_root.update()
            time.sleep(1.0)
        
        self._main_root_ref = main_root

        # Cattura screenshot SENZA la finestra dell'app
        screenshot = self.clean_screenshot()

        # Ora mostra l'overlay per la selezione
        self.root = tk.Tk()
        self.root.geometry(f"{screenshot.width}x{screenshot.height}+0+0")
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.3)
        self.root.overrideredirect(True)
        self.root.configure(bg='black')

        # Canvas per la selezione
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # Converti screenshot per Tkinter
        self.photo = ImageTk.PhotoImage(screenshot, master=self.root)
        self.canvas.create_image(0, 0, anchor='nw', image=self.photo)

        # Bind eventi mouse
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

        # Istruzioni
        self.canvas.create_text(
            400, 50, 
            text="Trascina per selezionare l'area da monitorare - ESC per annullare",
            fill='white', 
            font=('Arial', 16, 'bold')
        )

        # Bind ESC per annullare
        self.root.bind('<Escape>', lambda e: self.cancel_selection())

        self.root.mainloop()
    
    def on_click(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.selection_active = True
    
    def on_drag(self, event):
        if self.selection_active:
            self.current_x = event.x
            self.current_y = event.y
            
            # Cancella rettangolo precedente
            self.canvas.delete('selection')
            
            # Disegna nuovo rettangolo
            self.canvas.create_rectangle(
                self.start_x, self.start_y,
                self.current_x, self.current_y,
                outline='red', width=3, tags='selection'
            )
    
    def on_release(self, event):
        if self.selection_active:
            self.selection_active = False
            
            # Calcola coordinate finali
            x1 = min(self.start_x, self.current_x)
            y1 = min(self.start_y, self.current_y)
            x2 = max(self.start_x, self.current_x)
            y2 = max(self.start_y, self.current_y)
            
            width = x2 - x1
            height = y2 - y1
            
            # Chiudi finestra e ritorna coordinate
            self.root.destroy()
            if hasattr(self, '_main_root_ref') and self._main_root_ref:
                self._main_root_ref.deiconify()
            self.callback((x1, y1, width, height))
    
    def cancel_selection(self):
        self.root.destroy()
        if hasattr(self, '_main_root_ref') and self._main_root_ref:
            self._main_root_ref.deiconify()
        self.callback(None)

class ScreenshotManager:
    def __init__(self, monitor_area=None):
        self.monitor_area = monitor_area
    
    def set_monitor_area(self, area):
        """Imposta l'area di monitoraggio"""
        self.monitor_area = area
    
    def capture_screenshot(self):
        """Cattura uno screenshot dell'area monitorata"""
        if not self.monitor_area:
            raise ValueError("Area di monitoraggio non impostata")
        
        x, y, w, h = self.monitor_area
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        return screenshot
    
    def capture_and_preprocess(self):
        """Cattura screenshot e preprocessa per OCR"""
        screenshot = self.capture_screenshot()
        
        # Converti per OpenCV
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # 1. Grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # 2. Slight upscale (1.5x)
        scale_percent = 150
        width = int(gray.shape[1] * scale_percent / 100)
        height = int(gray.shape[0] * scale_percent / 100)
        gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

        # 3. Sharpen
        kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
        sharp = cv2.filter2D(gray, -1, kernel)

        # 4. Invert (white text on black -> black text on white)
        inverted = cv2.bitwise_not(sharp)
        
        return inverted
    
    def show_preprocessed_image(self, img, window_title="Preprocessed Image", filename="preprocessed_debug.png"):
        """Mostra e salva l'immagine preprocessata per debug"""
        cv2.imshow(window_title, img)
        cv2.imwrite(filename, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows() 