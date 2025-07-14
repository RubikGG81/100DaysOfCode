import hashlib
import tkinter as tk
from tkinter import ttk
import threading
import time
import configparser
import os

# Import dei moduli
from screenshot_module import AreaSelector, ScreenshotManager
from ocr_module import OCRProcessor
from analysis_module import MessageAnalyzer
from notification_module import TelegramNotifier
from logging_module import LogManager, LogWidget
from logicheapiexchange import BybitTrader

# Carica variabili d'ambiente da file .env se presente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class AdvancedDiscordMonitor:
    def __init__(self):
        # Inizializza i moduli
        self.screenshot_manager = ScreenshotManager()
        self.ocr_processor = OCRProcessor()
        self.message_analyzer = MessageAnalyzer()
        self.telegram_notifier = TelegramNotifier()
        self.bybit_trader = BybitTrader() # BybitTrader ora carica le credenziali da config.ini al suo interno

        # Variabili per le credenziali API (gestite dalla finestra di configurazione)
        self.telegram_token = ""
        self.telegram_chat_id = ""
        self.bybit_api_key = ""
        self.bybit_api_secret = ""

        # Inizializza il logger
        self.log_manager = LogManager()

        # Setup GUI
        self.setup_gui()

        # Carica configurazione iniziale (incluse le credenziali API)
        self.load_config()

        # Variabili di stato
        self.is_monitoring = False
        self.monitor_thread = None

    def setup_gui(self):
        """Setup dell'interfaccia grafica"""
        self.root = tk.Tk()
        self.root.title("Partial Screen Monitor Capture")
        self.root.geometry("350x800")

        # Definisci stili per i pulsanti
        style = ttk.Style()
        style.configure("Bold.TButton", font=('Arial', 10, 'bold'))
        style.configure("Active.TButton", background="lightgreen", foreground="black", font=('Arial', 10, 'bold'))
        style.map("Active.TButton",
            background=[('disabled', '#90EE90'), ('!disabled', '#90EE90')], # lightgreen
            foreground=[('disabled', 'black'), ('!disabled', 'black')]
        )

        # Pulsante Configurazione API (nuovo e in cima)
        api_config_frame = ttk.Frame(self.root) # Nuovo frame per il pulsante API
        api_config_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(api_config_frame, text="Configurazione API", command=self.show_api_config_window, style="Bold.TButton").pack(fill="x", pady=2)

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

        # Filtro selezione sorgente
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
        # Frame principale per i pulsanti
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)

        # Gruppo Seleziona Area / Test OCR
        selection_frame = ttk.LabelFrame(button_frame, text="Strumenti Area")
        selection_frame.pack(fill="x", padx=5, pady=5, anchor="nw")
        ttk.Button(selection_frame, text="Seleziona Area", command=self.select_area).pack(fill="x", pady=2)
        ttk.Button(selection_frame, text="Test OCR", command=self.test_ocr).pack(fill="x", pady=2)

        # Gruppo Avvia Monitor / Ferma Monitor
        monitor_frame = ttk.LabelFrame(button_frame, text="Controllo Monitor")
        monitor_frame.pack(fill="x", padx=5, pady=5, anchor="nw")
        self.start_monitor_button = ttk.Button(monitor_frame, text="Avvia Monitor", command=self.start_monitor, style="Bold.TButton")
        self.start_monitor_button.pack(fill="x", pady=2)
        self.stop_monitor_button = ttk.Button(monitor_frame, text="Ferma Monitor", command=self.stop_monitor, style="Bold.TButton")
        self.stop_monitor_button.pack(fill="x", pady=2)
        self.stop_monitor_button.config(state=tk.DISABLED)

        # Pulsante Salva Configurazione (separato)
        save_button_frame = ttk.Frame(self.root)
        save_button_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(save_button_frame, text="Salva Configurazione", command=self.save_config).pack(fill="x", padx=5, pady=2)

        # Log con filtri
        log_frame = ttk.LabelFrame(self.root, text="Log Attività")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Usa il widget di log personalizzato
        self.log_widget = LogWidget(log_frame)
        self.log_widget.frame.pack(fill="both", expand=True)

        # Collega il logger al widget
        self.log_manager.set_log_widget(self.log_widget.get_widget())

        # Bind evento di chiusura
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_api_config_window(self):
        """Mostra la finestra di configurazione delle API."""
        api_window = tk.Toplevel(self.root)
        api_window.title("Configurazione API")
        api_window.geometry("400x300")
        api_window.transient(self.root) # Rendi la finestra modale rispetto alla principale
        api_window.grab_set() # Blocca l'interazione con la finestra principale

        # Frame per Telegram API
        telegram_frame = ttk.LabelFrame(api_window, text="Telegram API")
        telegram_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(telegram_frame, text="Token Bot Telegram:").pack(anchor="w")
        self.telegram_token_entry_api = ttk.Entry(telegram_frame, width=50)
        self.telegram_token_entry_api.pack(fill="x", padx=5, pady=2)

        ttk.Label(telegram_frame, text="Chat ID Telegram:").pack(anchor="w")
        self.telegram_chat_entry_api = ttk.Entry(telegram_frame, width=50)
        self.telegram_chat_entry_api.pack(fill="x", padx=5, pady=2)

        # Frame per Bybit API
        bybit_frame = ttk.LabelFrame(api_window, text="Bybit API")
        bybit_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(bybit_frame, text="Bybit API Key:").pack(anchor="w")
        self.bybit_api_key_entry = ttk.Entry(bybit_frame, width=50)
        self.bybit_api_key_entry.pack(fill="x", padx=5, pady=2)

        ttk.Label(bybit_frame, text="Bybit API Secret:").pack(anchor="w")
        self.bybit_api_secret_entry = ttk.Entry(bybit_frame, width=50, show='*') # Nascondi il secret
        self.bybit_api_secret_entry.pack(fill="x", padx=5, pady=2)

        # Popola i campi con i valori attuali
        self._load_api_credentials_to_gui()

        # Bottoni Salva/Annulla
        button_frame = ttk.Frame(api_window)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Salva", command=lambda: self.save_api_config_from_window(api_window)).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Annulla", command=api_window.destroy).pack(side="left", padx=5)

        api_window.wait_window() # Attendi che la finestra sia chiusa

    def _load_api_credentials_to_gui(self):
        """Carica le credenziali API nelle entry della finestra di configurazione."""
        self.telegram_token_entry_api.delete(0, tk.END)
        self.telegram_token_entry_api.insert(0, self.telegram_token)
        self.telegram_chat_entry_api.delete(0, tk.END)
        self.telegram_chat_entry_api.insert(0, self.telegram_chat_id)
        self.bybit_api_key_entry.delete(0, tk.END)
        self.bybit_api_key_entry.insert(0, self.bybit_api_key)
        self.bybit_api_secret_entry.delete(0, tk.END)
        self.bybit_api_secret_entry.insert(0, self.bybit_api_secret)

    def save_api_config_from_window(self, api_window):
        """Salva le credenziali API dalla finestra di configurazione."""
        self.telegram_token = self.telegram_token_entry_api.get()
        self.telegram_chat_id = self.telegram_chat_entry_api.get()
        self.bybit_api_key = self.bybit_api_key_entry.get()
        self.bybit_api_secret = self.bybit_api_secret_entry.get()

        self.save_config() # Salva le nuove credenziali nel file config.ini
        self.update_configurations() # Applica le nuove credenziali ai moduli
        self.log_manager.info("Credenziali API aggiornate e salvate.")
        api_window.destroy()

    def select_area(self):
        """Avvia la selezione dell'area con interfaccia grafica"""
        self.root.withdraw()

        selector = AreaSelector(self.on_area_selected)
        selector.start_selection()

    def on_area_selected(self, area):
        """Callback quando un'area è selezionata"""
        self.root.deiconify()

        if area:
            self.screenshot_manager.set_monitor_area(area)
            x, y, w, h = area
            self.area_label.config(text=f"{x},{y} - {w}x{h}")
            self.log_manager.info(f"Area selezionata: {x},{y} - {w}x{h}")
        else:
            self.log_manager.warning("Selezione area annullata")

    def test_ocr(self):
        """Testa l'OCR sull'area selezionata"""
        if not self.screenshot_manager.monitor_area:
            self.log_manager.error("Seleziona prima un'area")
            return

        try:
            # Cattura e preprocessa immagine
            preprocessed_image = self.screenshot_manager.capture_and_preprocess()

            # Mostra immagine preprocessata
            self.screenshot_manager.show_preprocessed_image(
                preprocessed_image,
                window_title="Test OCR - Preprocessed",
                filename="test_ocr_preprocessed.png"
            )

            # Test OCR
            result = self.ocr_processor.test_ocr(preprocessed_image)

            self.log_manager.info(f"Test OCR completato. Testo rilevato: {result['char_count']} caratteri")

            # Mostra risultati in finestra popup
            self.show_ocr_results(result['text'])

        except Exception as e:
            self.log_manager.error(f"Errore test OCR: {e}")

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
        if not self.screenshot_manager.monitor_area:
            self.log_manager.error("Seleziona prima un'area da monitorare")
            return

        # Ora controlliamo le variabili interne, non le entry della GUI principale
        if not self.telegram_token or not self.telegram_chat_id:
            self.log_manager.error("Inserisci token e chat ID Telegram nella configurazione API.")
            return

        if self.is_monitoring:
            self.log_manager.warning("Monitoraggio già attivo")
            return

        # Aggiorna configurazioni
        self.update_configurations()

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        self.start_monitor_button.config(text="Monitor ATTIVO", state=tk.DISABLED, style="Active.TButton")
        self.stop_monitor_button.config(state=tk.NORMAL)

        self.log_manager.info("Monitoraggio avviato")

    def stop_monitor(self):
        """Ferma il monitoraggio"""
        if not self.is_monitoring:
            self.log_manager.warning("Monitoraggio non attivo")
            return

        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        self.start_monitor_button.config(text="Avvia Monitor", state=tk.NORMAL, style="Bold.TButton")
        self.stop_monitor_button.config(state=tk.DISABLED)

        self.log_manager.info("Monitoraggio fermato")

    def update_configurations(self):
        """Aggiorna le configurazioni dei moduli"""
        # Telegram
        self.telegram_notifier.set_credentials(
            self.telegram_token,
            self.telegram_chat_id
        )
        # Bybit
        self.bybit_trader.set_credentials(
            self.bybit_api_key,
            self.bybit_api_secret
        )

        # Message Analyzer
        self.message_analyzer.set_keywords(self.keywords_entry.get())
        self.message_analyzer.set_keywords_eliz(self.keywords_entry_eliz.get())
        self.message_analyzer.set_source_filter(self.source_filter.get())

        # Carica messaggi precedenti
        self.message_analyzer.last_messages = self.message_analyzer.load_last_messages()

    def monitor_loop(self):
        """Loop principale di monitoraggio"""
        last_hash = None
        first_message_dropped = False

        while self.is_monitoring:
            try:
                # Cattura e preprocessa screenshot
                preprocessed_image = self.screenshot_manager.capture_and_preprocess()
                self.log_manager.debug("Screen taken")

                # Calcola hash per rilevare cambiamenti
                img_hash = self.ocr_processor.calculate_image_hash(preprocessed_image)

                if last_hash != img_hash:
                    last_hash = img_hash

                    # OCR
                    text = self.ocr_processor.extract_text(preprocessed_image)
                    if "spot.png" not in self.screenshot_manager.find_templates_in_image(preprocessed_image):
                        if text.strip():
                            # Analizza messaggi
                            new_messages = self.message_analyzer.analyze_messages(text, self.message_analyzer.last_messages)

                            for message in new_messages:
                                if first_message_dropped:
                                    self.log_manager.info(f"Nuovo messaggio rilevato: {message[:50]}...")

                                    # Invia notifica Telegram
                                    result = self.telegram_notifier.send_discord_notification(message)
                                    if result['success']:
                                        self.log_manager.success("Notifica Telegram inviata")
                                        message_hash = hashlib.md5(message.encode()).hexdigest()
                                        self.message_analyzer.update_last_messages(message_hash)
                                        self.message_analyzer.save_last_messages(self.message_analyzer.last_messages)
    
                                    else:
                                        self.log_manager.error(f"Errore Telegram: {result['error']}")

                                    # Logica di Trading
                                    if "Current Trade" in message:
                                        if trade_data := self.message_analyzer.extract_trade_data(message):
                                            self.log_manager.info(f"Trade rilevato: {trade_data.token_name} - Entry: {trade_data.entry_price} - Side: {trade_data.side}")
                                            self.execute_trade(trade_data)

                                    # Aggiorna storico messaggi
                                    

                                else:
                                    first_message_dropped = True
                                    continue
                    else:
                        self.log_manager.error(f"SPOT trade rilevato e saltato")
                        

                # Aspetta prima del prossimo controllo
                interval = int(self.interval_var.get())
                time.sleep(interval)

            except Exception as e:
                self.log_manager.error(f"Errore nel monitoraggio: {e}")
                time.sleep(5)

    def execute_trade(self, trade_data):
        """Esegue il trade rilevato"""
        try:
            symbol = trade_data.token_name + "USDT"
            qty = str(trade_data.bought_token_amount)
            side = trade_data.side

            if trade_data.limit_order:
                order_type = "Limit"
                price = str(trade_data.entry_price)
            else:
                order_type = "Market"
                price = None

            # Piazza l'ordine
            order_result = self.bybit_trader.place_order(symbol, side, qty, order_type, price)
            if order_result and order_result['retCode'] == 0:
                self.log_manager.success(f"Ordine {order_type} piazzato con successo per {symbol}: {order_result['result']['orderId']}")

                # Se è un ordine a mercato, attendi un attimo
                if order_type == "Market":
                    time.sleep(2)

                # Imposta SL/TP se disponibili
                if trade_data.stop_loss or trade_data.take_profit:
                    sl = str(trade_data.stop_loss) if trade_data.stop_loss else None
                    tp = str(trade_data.take_profit) if trade_data.take_profit else None

                    sl_tp_result = self.bybit_trader.set_stop_loss_take_profit(symbol, sl, tp)
                    if sl_tp_result and sl_tp_result['retCode'] == 0:
                        self.log_manager.success(f"SL/TP impostati con successo per {symbol}")
                    else:
                        self.log_manager.error(f"Errore nell'impostazione SL/TP per {symbol}")

                # Invia notifica trade
                self.telegram_notifier.send_trade_notification(trade_data)

            else:
                self.log_manager.error(f"Errore nel piazzamento dell'ordine {order_type} per {symbol}")

        except Exception as e:
            self.log_manager.error(f"Errore nell'esecuzione del trade: {e}")

    def save_config(self):
        """Salva la configurazione corrente nel file config.ini"""
        config = configparser.ConfigParser()

        # Leggi la configurazione esistente per preservare le sezioni non gestite dalla GUI
        if os.path.exists('config.ini'):
            config.read('config.ini')

        # Sezione Telegram (ora dalle variabili interne)
        config['telegram'] = {
            'token': self.telegram_token,
            'chat_id': self.telegram_chat_id
        }

        # Sezione Bybit (ora dalle variabili interne)
        config['bybit'] = {
            'api_key': self.bybit_api_key,
            'api_secret': self.bybit_api_secret
        }

        # Sezione Monitoraggio
        config['monitoring'] = {
            'interval': self.interval_var.get(),
            'sensitivity': self.sensitivity_var.get(),
            'source_filter': self.source_filter.get(),
            'keywords': self.keywords_entry.get(),
            'keywords_eliz': self.keywords_entry_eliz.get()
        }

        # Sezione Area
        if self.screenshot_manager.monitor_area:
            x, y, w, h = self.screenshot_manager.monitor_area
            config['area'] = {
                'x': str(x),
                'y': str(y),
                'width': str(w),
                'height': str(h)
            }

        try:
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            self.log_manager.success("Configurazione salvata con successo in config.ini")
        except Exception as e:
            self.log_manager.error(f"Errore nel salvataggio della configurazione: {e}")

    def load_config(self):
        """Carica la configurazione da config.ini"""
        config = configparser.ConfigParser()
        try:
            if os.path.exists('config.ini'):
                config.read('config.ini')

                # Carica sezione Telegram
                if 'telegram' in config:
                    self.telegram_token = config['telegram'].get('token', '')
                    self.telegram_chat_id = config['telegram'].get('chat_id', '')

                # Carica sezione Bybit
                if 'bybit' in config:
                    self.bybit_api_key = config['bybit'].get('api_key', '')
                    self.bybit_api_secret = config['bybit'].get('api_secret', '')

                # Carica sezione Monitoraggio
                if 'monitoring' in config:
                    self.interval_var.set(config['monitoring'].get('interval', '2'))
                    self.sensitivity_var.set(config['monitoring'].get('sensitivity', '5'))
                    self.source_filter.set(config['monitoring'].get('source_filter', '@Eliz Challenge'))
                    self.keywords_entry.delete(0, tk.END)
                    self.keywords_entry.insert(0, config['monitoring'].get('keywords', 'long,short,@'))
                    self.keywords_entry_eliz.delete(0, tk.END)
                    self.keywords_entry_eliz.insert(0, config['monitoring'].get('keywords_eliz', 'current trade'))

                # Carica sezione Area
                if 'area' in config:
                    x = int(config['area'].get('x', '0'))
                    y = int(config['area'].get('y', '0'))
                    w = int(config['area'].get('width', '0'))
                    h = int(config['area'].get('height', '0'))
                    self.screenshot_manager.set_monitor_area((x, y, w, h))
                    self.area_label.config(text=f"Area: {x},{y} - {w}x{h}")

                self.log_manager.info("Configurazione caricata da config.ini")
            else:
                self.log_manager.info("Nessun file di configurazione trovato. Utilizzo i valori di default.")
        except Exception as e:
            self.log_manager.error(f"Errore nel caricamento della configurazione: {e}")

    def on_closing(self):
        """Gestisce la chiusura del programma"""
        try:
            # Salva i messaggi prima di chiudere
            self.message_analyzer.save_last_messages(self.message_analyzer.last_messages)

            # Ferma il monitoraggio se attivo
            if self.is_monitoring:
                self.stop_monitor()

            # Chiudi la finestra
            self.root.destroy()
        except Exception as e:
            print(f"Errore durante la chiusura: {e}")
            self.root.destroy()

    def run(self):
        """Avvia l'applicazione"""
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = AdvancedDiscordMonitor()
        app.run()
    except Exception as e:
        print(f"Errore nell'avvio dell'applicazione: {e}")