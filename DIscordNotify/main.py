# sourcery skip: use-contextlib-suppress
import tkinter as tk
from tkinter import ttk
import pyautogui
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import hashlib
import mss
from dataclasses import dataclass
import json
import os

# Carica variabili d'ambiente da file .env se presente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Se python-dotenv non è installato, ignora
    pass

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
        
    def start_selection(self):  # sourcery skip: use-contextlib-suppress, use-next
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
            time.sleep(1.0)  # Attendi che la finestra sia nascosta
        
        self._main_root_ref = main_root  # Save reference for later restoration

        # Cattura screenshot SENZA la finestra dell'app usando la funzione statica
        screenshot = self.clean_screenshot()

        # Ora mostra l'overlay per la selezione
        self.root = tk.Tk()
        self.root.geometry(f"{screenshot.width}x{screenshot.height}+0+0")
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.3)  # Trasparenza
        self.root.overrideredirect(True)      # Nessun bordo/finestra
        self.root.configure(bg='black')

        # Canvas per la selezione
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # Converti screenshot per Tkinter (dopo aver creato root e canvas)
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
        print("Mouse clicked at:", event.x, event.y)
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
            # Ripristina la finestra principale se era stata nascosta
            if hasattr(self, '_main_root_ref') and self._main_root_ref:
                self._main_root_ref.deiconify()
            self.callback((x1, y1, width, height))
    
    def cancel_selection(self):
        self.root.destroy()
        # Ripristina la finestra principale se era stata nascosta
        if hasattr(self, '_main_root_ref') and self._main_root_ref:
            self._main_root_ref.deiconify()
        self.callback(None)

class AdvancedDiscordMonitor:
    def __init__(self):
        self.setup_gui()
        
    def setup_gui(self):  # sourcery skip: extract-duplicate-method
        self.root = tk.Tk()
        self.root.title("Discord Advanced Screen Monitor")
        self.root.geometry("600x800")
        
        # Configurazione
        config_frame = ttk.LabelFrame(self.root, text="Configurazione")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # Token Telegram
        ttk.Label(config_frame, text="Token Bot Telegram:").pack(anchor="w")
        self.telegram_token_entry = ttk.Entry(config_frame, width=60)
        self.telegram_token_entry.pack(fill="x", padx=5, pady=2)
        # Carica da variabile d'ambiente o lascia vuoto
        telegram_token = os.getenv('TELEGRAM_TOKEN', '')
        self.telegram_token_entry.insert(0, telegram_token)
        
        # Chat ID
        ttk.Label(config_frame, text="Chat ID Telegram:").pack(anchor="w")
        self.telegram_chat_entry = ttk.Entry(config_frame, width=60)
        self.telegram_chat_entry.pack(fill="x", padx=5, pady=2)
        # Carica da variabile d'ambiente o lascia vuoto
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.telegram_chat_entry.insert(0, telegram_chat_id)
        
        # Impostazioni monitoraggio
        settings_frame = ttk.LabelFrame(self.root, text="Impostazioni Monitoraggio")
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        # Intervallo controllo
        ttk.Label(settings_frame, text="Intervallo controllo (secondi):").pack(anchor="w")
        self.interval_var = tk.StringVar(value="2")
        interval_spin = ttk.Spinbox(settings_frame, from_=1, to=60, textvariable=self.interval_var)
        interval_spin.pack(anchor="w", padx=5)
        
        # Sensibilità cambiamento
        ttk.Label(settings_frame, text="Sensibilità cambiamento (%):").pack(anchor="w")
        self.sensitivity_var = tk.StringVar(value="5")
        sensitivity_spin = ttk.Spinbox(settings_frame, from_=1, to=50, textvariable=self.sensitivity_var)
        sensitivity_spin.pack(anchor="w", padx=5)
        
        #Filtro selezione sorgente
        ttk.Label(settings_frame, text="Filtro sorgente copiata:").pack(anchor="w")
        self.source_filter = ttk.Combobox(settings_frame, values=["@Eliz Challenge","Altri WWG"])
        self.source_filter.set("@Eliz Challenge")
        self.source_filter.pack(anchor="w", padx=5)
        
        # Filtri testo generici
        ttk.Label(settings_frame, text="Parole chiave generiche (separate da virgola):").pack(anchor="ne")
        self.keywords_entry = ttk.Entry(settings_frame, width=60)
        self.keywords_entry.pack(fill="x", padx=2, pady=2)
        self.keywords_entry.insert(0, "long,short,@")
        
        # Filtri testo specifici @eliz
        ttk.Label(settings_frame, text="Parole chiave @Eliz (separate da virgola):").pack(anchor="ne")
        self.keywords_entry_eliz = ttk.Entry(settings_frame, width=60)
        self.keywords_entry_eliz.pack(fill="x", padx=2, pady=2)
        self.keywords_entry_eliz.insert(0, "current trade")
        
        
        # Area selezionata
        area_frame = ttk.LabelFrame(self.root, text="Area Monitoraggio")
        area_frame.pack(fill="x", padx=10, pady=5)
        
        self.area_label = ttk.Label(area_frame, text="Nessuna area selezionata")
        self.area_label.pack(anchor="w", padx=5, pady=5)
        
        # Bottoni
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Seleziona Area", command=self.select_area).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Test OCR", command=self.test_ocr).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Avvia Monitor", command=self.start_monitor).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Ferma Monitor", command=self.stop_monitor).pack(side="left", padx=5)
        
        # Log con filtri
        log_frame = ttk.LabelFrame(self.root, text="Log Attività")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Filtri log
        filter_frame = ttk.Frame(log_frame)
        filter_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(filter_frame, text="Filtro:").pack(side="left")
        self.log_filter = ttk.Combobox(filter_frame, values=["Tutti", "Info", "Warning", "Error"])
        self.log_filter.set("Tutti")
        self.log_filter.pack(side="left", padx=5)
        
        ttk.Button(filter_frame, text="Pulisci Log", command=self.clear_log).pack(side="right")
        
        # Area log
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_text_frame, wrap=tk.WORD, height=10)
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Variabili
        self.monitor_area = None
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_screenshot = None
        
        # Carica messaggi precedenti all'avvio
        self.last_messages = self.load_last_messages()
        
        # Bind evento di chiusura per salvare i messaggi
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    @dataclass
    class eliz_data_trade:
        limit_order: bool
        token_name: str
        bought_token_amount: int
        balance: int       
        entry_price: float
        stop_loss: any
        take_profit: any
        e_retest: bool
        
    def select_area(self):
        """Avvia la selezione dell'area con interfaccia grafica"""
        self.root.withdraw()  # Nascondi finestra principale
        
        selector = AreaSelector(self.on_area_selected)
        selector.start_selection()
    
    def on_area_selected(self, area):
        """Callback quando un'area è selezionata"""
        self.root.deiconify()  # Mostra finestra principale
        
        if area:
            self.monitor_area = area
            x, y, w, h = area
            self.area_label.config(text=f"Area: {x},{y} - {w}x{h}")
            self.log("INFO", f"Area selezionata: {x},{y} - {w}x{h}")
        else:
            self.log("WARNING", "Selezione area annullata")
    
    def show_preprocessed_image(self, img, window_title="Preprocessed Image", filename="preprocessed_debug.png"):
        """Mostra e salva l'immagine preprocessata per debug"""
        import cv2
        cv2.imshow(window_title, img)
        cv2.imwrite(filename, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def test_ocr(self):  # sourcery skip: extract-method
        """Testa l'OCR sull'area selezionata"""
        if not self.monitor_area:
            self.log("ERROR", "Seleziona prima un'area")
            return
        
        try:
            # Cattura area
            x, y, w, h = self.monitor_area
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            
            # Converti per OpenCV
            img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # 1. Grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            # 2. Upscale (200%)
            gray_up = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            # 3. Inversione (bianco su nero -> nero su bianco)
            inverted = cv2.bitwise_not(gray_up)

            # Mostra e salva immagine preprocessata (dopo inversione)
            self.show_preprocessed_image(inverted, window_title="Test OCR - Inverted", filename="test_ocr_inverted.png")
            
            # OCR (su immagine invertita)
            import pytesseract
            custom_config = r'--oem 3 --psm 6 -l eng'
            text = pytesseract.image_to_string(inverted, config=custom_config)
            
            self.log("INFO", f"Test OCR completato. Testo rilevato: {len(text)} caratteri")
            
            # Mostra risultati in finestra popup
            self.show_ocr_results(text)
            
        except Exception as e:
            self.log("ERROR", f"Errore test OCR: {e}")
    
    def show_ocr_results(self, text):
        """Mostra i risultati dell'OCR in una finestra popup"""
        popup = tk.Toplevel(self.root)
        popup.title("Risultati Test OCR")
        popup.geometry("500x400")
        
        text_widget = tk.Text(popup, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(popup, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        text_widget.insert(tk.END, text)
        text_widget.config(state=tk.DISABLED)
    
    def start_monitor(self):
        """Avvia il monitoraggio"""
        if not self.monitor_area:
            self.log("ERROR", "Seleziona prima un'area da monitorare")
            return
        
        if not self.telegram_token_entry.get() or not self.telegram_chat_entry.get():
            self.log("ERROR", "Inserisci token e chat ID Telegram")
            return
        
        if self.is_monitoring:
            self.log("WARNING", "Monitoraggio già attivo")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        self.log("INFO", "Monitoraggio avviato")
    
    def stop_monitor(self):
        """Ferma il monitoraggio"""
        if not self.is_monitoring:
            self.log("WARNING", "Monitoraggio non attivo")
            return
        
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.log("INFO", "Monitoraggio fermato")
    
    def monitor_loop(self):  # sourcery skip: low-code-quality
        """Loop principale di monitoraggio"""
        import pytesseract
        import hashlib
        source_selection = self.source_filter.get()
        last_hash = None
        first_message_dropped = False
        
        while self.is_monitoring:
            try:
                # Cattura screenshot dell'area
                x, y, w, h = self.monitor_area
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
                
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

                # Mostra e salva immagine preprocessata (solo per debug, puoi commentare dopo il test)
                # self.show_preprocessed_image(inverted, window_title="Monitor - Preprocessed", filename="monitor_preprocessed.png")
                
                # Calcola hash per rilevare cambiamenti
                img_hash = hashlib.md5(inverted.tobytes()).hexdigest()
                
                if last_hash != img_hash:
                    last_hash = img_hash
                    
                    # OCR
                    custom_config = r'--oem 3 --psm 6 -l eng'
                    text = pytesseract.image_to_string(inverted, config=custom_config)
                    
                    if text.strip():
                        # Rileva nuovi messaggi
                        
                        if source_selection == "@Eliz Challenge":
                            new_messages = self.detect_new_messages_eliz(text, self.last_messages)
                        else:
                            new_messages = self.detect_new_messages(text, self.last_messages)
                        
                        for message in new_messages:
                            if first_message_dropped:
                                self.log("INFO", f"Nuovo messaggio rilevato: {message[:50]}...")
                                self.send_telegram_notification(message)
                                
                                # Aggiungi a storico
                                message_hash = hashlib.md5(message.encode()).hexdigest()
                                self.last_messages.append(message_hash)
                            
                            else:
                                first_message_dropped = True
                                continue
                            
                            # Mantieni solo ultimi 30 messaggi
                            if len(self.last_messages) > 30:
                                self.last_messages = self.last_messages[-30:]
                            
                            # Salva automaticamente dopo ogni nuovo messaggio
                            self.save_last_messages()
                
                # Aspetta prima del prossimo controllo
                interval = int(self.interval_var.get())
                time.sleep(interval)
                
            except Exception as e:
                self.log("ERROR", f"Errore nel monitoraggio: {e}")
                time.sleep(5)
    
    def detect_new_messages(self, text, last_messages):
        """Rileva nuovi messaggi nel testo"""
        new_messages = []
        
        # Ottieni parole chiave
        keywords = [kw.strip() for kw in self.keywords_entry.get().split(',')]
        
        # Dividi in righe
        lines = text.split('\n')
        
        # Trova messaggi con parole chiave
        current_message = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Controlla se contiene parole chiave
            has_keyword = any(kw in line.lower() for kw in keywords if kw)
            
            if has_keyword:
                # Salva messaggio precedente
                if current_message:
                    message_text = '\n'.join(current_message)
                    message_hash = hashlib.md5(message_text.encode()).hexdigest()
                    
                    if message_hash not in last_messages:
                        new_messages.append(message_text)
                
                # Inizia nuovo messaggio
                current_message = [line]
            else:
                current_message.append(line)
        
        # Ultimo messaggio
        if current_message:
            message_text = '\n'.join(current_message)
            message_hash = hashlib.md5(message_text.encode()).hexdigest()
            
            if message_hash not in last_messages:
                new_messages.append(message_text)
        
        return new_messages
    
    def detect_new_messages_eliz(self, text, last_messages):
        """Rileva nuovi messaggi nel testo"""
        new_messages = []
        
        # Ottieni parole chiave
        keywords = [kw.strip() for kw in self.keywords_entry_eliz.get().split(',')]
        
        # Dividi in righe
        lines = text.split('\n')
        
        # Trova messaggi con parole chiave
        current_message = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Controlla se contiene parole chiave
            has_keyword = any(kw in line.lower() for kw in keywords if kw)
            
            if has_keyword:
                # Salva messaggio precedente
                if current_message:
                    message_text = '\n'.join(current_message)
                    message_hash = hashlib.md5(message_text.encode()).hexdigest()
                    
                    if message_hash not in last_messages:
                        new_messages.append(message_text)
                
                # Inizia nuovo messaggio
                current_message = [line]
            elif not line.startswith("(Edited"):
                    current_message.append(line)
        
        # Ultimo messaggio
        if current_message:
            message_text = '\n'.join(current_message)
            message_hash = hashlib.md5(message_text.encode()).hexdigest()
            
            if message_hash not in last_messages:
                new_messages.append(message_text)
        
        # for message in new_messages:
        #     if "Current Trade" in message:
        #         trade_data = self.parse_eliz_trade(message)
        #         self.log("INFO", f"Trade rilevato: {trade_data.token_name} - Entry: {trade_data.entry_price}")
        #         # Qui puoi aggiungere logica per gestire il trade
        
        return new_messages
    
    def send_telegram_notification(self, message):
        """Invia notifica a Telegram"""
        try:
            import requests
            from datetime import datetime
            
            url = f"https://api.telegram.org/bot{self.telegram_token_entry.get()}/sendMessage"
            
            telegram_message = f"""
🔔 **Nuovo messaggio Discord**
📱 Rilevato: {datetime.now().strftime('%H:%M:%S')}
📝 Contenuto:
{message}
"""
            
            data = {
                "chat_id": self.telegram_chat_entry.get(),
                "text": telegram_message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                self.log("INFO", "Notifica Telegram inviata")
            else:
                self.log("ERROR", f"Errore Telegram: {response.status_code}")
            
            
                
        except Exception as e:
            self.log("ERROR", f"Errore invio Telegram: {e}")
    
    def log(self, level, message):
        """Aggiunge messaggio al log"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {level}: {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # Colora in base al livello
        if level == "ERROR":
            self.log_text.tag_add("error", f"end-{len(log_message)}c", "end-1c")
            self.log_text.tag_config("error", foreground="red")
        elif level == "WARNING":
            self.log_text.tag_add("warning", f"end-{len(log_message)}c", "end-1c")
            self.log_text.tag_config("warning", foreground="orange")
        elif level == "INFO":
            self.log_text.tag_add("info", f"end-{len(log_message)}c", "end-1c")
            self.log_text.tag_config("info", foreground="blue")
    
    def clear_log(self):
        """Pulisce il log"""
        self.log_text.delete(1.0, tk.END)
    
    def run(self):
        """Avvia l'applicazione"""
        self.root.mainloop()

    def parse_eliz_trade(self, text: str) -> eliz_data_trade:
        # sourcery skip: low-code-quality
        """Parser per estrarre i dati del trade dalla stringa di Eliz"""
        try:
            # Inizializza variabili con valori di default
            limit_order = False
            token_name = ""
            bought_token_amount = 0
            balance = 0
            entry_price = 0.0
            stop_loss = ""
            take_profit = ""
            e_retest = False
            
            # Dividi il testo in righe
            lines = text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.endswith("LIMIT ORDER"):
                    limit_str = line.replace("LIMIT ORDER", "")
                    limit_order = True
                
                    
                # Token Name
                if line.startswith("Token Name:"):
                    token_name = line.replace("Token Name:", "").strip()
                    
                # Bought Token Amount
                elif line.startswith("Bought Token Amount:"):
                    amount_str = line.replace("Bought Token Amount:", "").strip()
                    try:
                        bought_token_amount = int(amount_str)
                    except ValueError:
                        bought_token_amount = 0
                        
                # Balance
                elif line.startswith("Balance:"):
                    balance_str = line.replace("Balance:", "").strip()
                    try:
                        balance = int(balance_str)
                    except ValueError:
                        balance = 0
                        
                # Entry Price
                elif line.startswith("Entry Price:"):
                    price_str = line.replace("Entry Price:", "").strip()
                    try:
                        entry_price = float(price_str)
                    except ValueError:
                        entry_price = 0.0
                        
                # Stop Loss - può essere numero o stringa
                elif line.startswith("Stop Loss:"):
                    sl_str = line.replace("Stop Loss:", "").strip()
                    try:
                        # Prova prima come float
                        stop_loss = float(sl_str)
                    except ValueError:
                        # Se non è un numero, mantieni come stringa
                        stop_loss = sl_str
                        
                # Take Profit - può essere numero o stringa
                elif line.startswith("Take Profit:"):
                    tp_str = line.replace("Take Profit:", "").strip()
                    try:
                        # Prova prima come float
                        take_profit = float(tp_str)
                    except ValueError:
                        # Se non è un numero, mantieni come stringa
                        take_profit = tp_str
                    
                # EP Retest
                elif line.startswith("EP Retest:"):
                    retest_str = line.replace("EP Retest:", "").strip()
                    e_retest = retest_str.lower() in ['true', 'yes', '1', 'si', 'sì']
                    
            

            
            # Crea e restituisci l'oggetto dataclass
            return self.eliz_data_trade(
                limit_order=limit_order,
                token_name=token_name,
                bought_token_amount=bought_token_amount,
                balance=balance,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                e_retest=e_retest
            )
            
        except Exception as e:
            self.log("ERROR", f"Errore nel parsing del trade: {e}")
            # Restituisci un oggetto con valori di default in caso di errore
            return self.eliz_data_trade(
                limit_order=False,
                token_name="",
                bought_token_amount=0,
                balance=0,
                entry_price=0.0,
                stop_loss="",
                take_profit="",
                e_retest=False
            )

    def format_eliz_trade(self, trade: eliz_data_trade) -> str:
        # sourcery skip: hoist-statement-from-if
        """Converte un oggetto eliz_data_trade in una stringa formattata"""
        try:
            lines = []
            
            # Aggiungi LIMIT ORDER se presente
            if trade.limit_order:
                lines.append("LIMIT ORDER")
            
            # Token Name
            if trade.token_name:
                lines.append(f"Token Name: {trade.token_name}")
            
            # Bought Token Amount
            if trade.bought_token_amount > 0:
                lines.append(f"Bought Token Amount: {trade.bought_token_amount}")
            
            # Balance
            if trade.balance > 0:
                lines.append(f"Balance: {trade.balance}")
            
            # Entry Price
            if trade.entry_price > 0:
                lines.append(f"Entry Price: {trade.entry_price}")
            
            # Stop Loss
            if trade.stop_loss:
                if isinstance(trade.stop_loss, (int, float)):
                    lines.append(f"Stop Loss: {trade.stop_loss}")
                else:
                    lines.append(f"Stop Loss: {trade.stop_loss}")
            
            # Take Profit
            if trade.take_profit:
                if isinstance(trade.take_profit, (int, float)):
                    lines.append(f"Take Profit: {trade.take_profit}")
                else:
                    lines.append(f"Take Profit: {trade.take_profit}")
            
            # EP Retest
            if trade.e_retest:
                lines.append("EP Retest: true")
            else:
                lines.append("EP Retest: false")
            
            # Unisci tutte le righe
            return "\n".join(lines)
            
        except Exception as e:
            self.log("ERROR", f"Errore nella formattazione del trade: {e}")
            return "Errore nella formattazione del trade"

    def save_last_messages(self):
        """Salva last_messages in un file JSON"""
        try:
            with open('last_messages.json', 'w', encoding='utf-8') as f:
                json.dump(self.last_messages, f, ensure_ascii=False, indent=2)
            self.log("INFO", f"Salvati {len(self.last_messages)} messaggi in last_messages.json")
        except Exception as e:
            self.log("ERROR", f"Errore nel salvataggio dei messaggi: {e}")
    
    def load_last_messages(self):
        """Carica last_messages da un file JSON"""
        try:
            if os.path.exists('last_messages.json'):
                with open('last_messages.json', 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                self.log("INFO", f"Caricati {len(messages)} messaggi da last_messages.json")
                return messages
            else:
                self.log("INFO", "Nessun file di messaggi precedenti trovato, partendo da zero")
                return []
        except Exception as e:
            self.log("ERROR", f"Errore nel caricamento dei messaggi: {e}")
            return []
    
    def on_closing(self):
        """Gestisce la chiusura del programma"""
        try:
            # Salva i messaggi prima di chiudere
            self.save_last_messages()
            
            # Ferma il monitoraggio se attivo
            if self.is_monitoring:
                self.stop_monitor()
            
            # Chiudi la finestra
            self.root.destroy()
        except Exception as e:
            print(f"Errore durante la chiusura: {e}")
            self.root.destroy()

# Script di avvio semplificato
class SimpleDiscordMonitor:
    def __init__(self, telegram_token, telegram_chat_id):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.monitor_area = None
        self.is_monitoring = False
        
    def set_area(self, x, y, width, height):
        """Imposta l'area di monitoraggio manualmente"""
        self.monitor_area = (x, y, width, height)
        print(f"Area impostata: {x},{y} - {width}x{height}")
    
    def start_simple_monitor(self):
        """Avvia monitoraggio semplificato"""
        if not self.monitor_area:
            print("Errore: Imposta prima l'area di monitoraggio")
            return
        
        import pytesseract
        import hashlib
        
        print("Avvio monitoraggio semplificato...")
        self.is_monitoring = True
        last_hash = None
        
        try:
            while self.is_monitoring:
                # Cattura screenshot
                x, y, w, h = self.monitor_area
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
                
                # Converti per OpenCV
                img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                # Verifica cambiamenti
                img_hash = hashlib.md5(img_cv.tobytes()).hexdigest()
                
                if last_hash != img_hash:
                    last_hash = img_hash
                    
                    # OCR
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                    text = pytesseract.image_to_string(gray, config='--psm 6 -l ita+eng')
                    
                    if text.strip():
                        print(f"Testo rilevato: {text[:100]}...")
                        
                        # Controlla se contiene indicatori di nuovo messaggio
                        time_indicators = ['ora fa', 'minuto fa', 'oggi alle']
                        if any(indicator in text.lower() for indicator in time_indicators):
                            self.send_notification(text)
                
                time.sleep(3)  # Controllo ogni 3 secondi
                
        except KeyboardInterrupt:
            print("Monitoraggio interrotto")
        except Exception as e:
            print(f"Errore: {e}")
    
    def send_notification(self, message):
        """Invia notifica semplificata"""
        import requests
        from datetime import datetime
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            notification = f"""
🔔 Nuovo messaggio Discord rilevato!
⏰ {datetime.now().strftime('%H:%M:%S')}

📝 Contenuto:
{message[:500]}...
"""
            
            data = {
                "chat_id": self.telegram_chat_id,
                "text": notification
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                print("✅ Notifica inviata su Telegram")
            else:
                print(f"❌ Errore invio: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Errore notifica: {e}")

# Esempio di utilizzo semplificato
def esempio_utilizzo():
    """Esempio di come usare il monitor in modalità semplificata"""
    
    # Configurazione da variabili d'ambiente
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Imposta le variabili d'ambiente TELEGRAM_TOKEN e TELEGRAM_CHAT_ID")
        print("Crea un file .env nella cartella del progetto con:")
        print("TELEGRAM_TOKEN=il_tuo_token")
        print("TELEGRAM_CHAT_ID=il_tuo_chat_id")
        return
    
    # Crea monitor
    monitor = SimpleDiscordMonitor(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    # Imposta area manualmente (dovrai personalizzare questi valori)
    # Questi sono coordinate di esempio per un monitor 1920x1080
    monitor.set_area(x=600, y=200, width=1000, height=600)
    
    # Avvia monitoraggio
    print("Premi Ctrl+C per fermare")
    monitor.start_simple_monitor()

if __name__ == "__main__":
    # Scegli modalità
    print("Modalità disponibili:")
    print("1. GUI Avanzata")
    print("2. Modalità Semplificata")
    
    #choice = input("Scegli (1 o 2): ")
    choice = "1"
    if choice == "1":
        try:
            app = AdvancedDiscordMonitor()
            app.run()
        except Exception as e:
            print(f"Errore GUI: {e}")
    elif choice == "2":
        print("Modifica le variabili TELEGRAM_TOKEN e TELEGRAM_CHAT_ID nel codice")
        print("Poi esegui la funzione esempio_utilizzo()")
    else:
        print("Scelta non valida")
