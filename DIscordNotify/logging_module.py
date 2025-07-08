import tkinter as tk
from tkinter import ttk
from datetime import datetime
import json
import os

class LogManager:
    def __init__(self, log_widget=None):
        self.log_widget = log_widget
        self.log_levels = {
            "INFO": "blue",
            "WARNING": "orange", 
            "ERROR": "red",
            "SUCCESS": "green",
            "DEBUG": "gray"
        }
    
    def set_log_widget(self, log_widget):
        """Imposta il widget di log per l'interfaccia grafica"""
        self.log_widget = log_widget
    
    def log(self, level, message, save_to_file=True):
        """Aggiunge un messaggio al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {level}: {message}\n"
        
        # Log su widget GUI se disponibile
        if self.log_widget:
            self.log_widget.insert(tk.END, log_message)
            self.log_widget.see(tk.END)
            
            # Colora in base al livello
            if level in self.log_levels:
                self.log_widget.tag_add(level.lower(), f"end-{len(log_message)}c", "end-1c")
                self.log_widget.tag_config(level.lower(), foreground=self.log_levels[level])
        
        # Log su console
        print(log_message.strip())
        
        # Salva su file se richiesto
        if save_to_file:
            self.save_to_file(level, message, timestamp)
    
    def info(self, message, save_to_file=True):
        """Log di livello INFO"""
        self.log("INFO", message, save_to_file)
    
    def warning(self, message, save_to_file=True):
        """Log di livello WARNING"""
        self.log("WARNING", message, save_to_file)
    
    def error(self, message, save_to_file=True):
        """Log di livello ERROR"""
        self.log("ERROR", message, save_to_file)
    
    def success(self, message, save_to_file=True):
        """Log di livello SUCCESS"""
        self.log("SUCCESS", message, save_to_file)
    
    def debug(self, message, save_to_file=False):
        """Log di livello DEBUG (non salvato su file di default)"""
        self.log("DEBUG", message, save_to_file)
    
    def save_to_file(self, level, message, timestamp):
        """Salva il log su file"""
        try:
            log_entry = {
                "timestamp": timestamp,
                "level": level,
                "message": message,
                "datetime": datetime.now().isoformat()
            }
            
            # Crea directory logs se non esiste
            os.makedirs("logs", exist_ok=True)
            
            # Salva in file giornaliero
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"logs/app_{date_str}.log"
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {level}: {message}\n")
            
            # Salva anche in formato JSON per analisi future
            json_filename = f"logs/app_{date_str}.json"
            
            try:
                with open(json_filename, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logs = []
            
            logs.append(log_entry)
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Errore nel salvataggio del log: {e}")
    
    def clear_log(self):
        """Pulisce il log dell'interfaccia grafica"""
        if self.log_widget:
            self.log_widget.delete(1.0, tk.END)
    
    def get_logs_by_level(self, level, date=None):
        """Recupera i log filtrati per livello e data"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        json_filename = f"logs/app_{date}.json"
        
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            return [log for log in logs if log['level'] == level]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def get_recent_logs(self, count=50, date=None):
        """Recupera i log più recenti"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        json_filename = f"logs/app_{date}.json"
        
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            return logs[-count:] if len(logs) > count else logs
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def export_logs(self, start_date, end_date, filename="exported_logs.json"):
        """Esporta i log in un range di date"""
        all_logs = []
        
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_date_obj:
            date_str = current_date.strftime("%Y-%m-%d")
            json_filename = f"logs/app_{date_str}.json"
            
            try:
                with open(json_filename, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                all_logs.extend(logs)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            current_date = current_date.replace(day=current_date.day + 1)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_logs, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Errore nell'esportazione: {e}")
            return False

class LogWidget:
    """Widget personalizzato per la visualizzazione dei log"""
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        
        # Filtri
        filter_frame = ttk.Frame(self.frame)
        filter_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(filter_frame, text="Filtro:").pack(side="left")
        self.log_filter = ttk.Combobox(filter_frame, values=["Tutti", "Info", "Warning", "Error", "Success", "Debug"])
        self.log_filter.set("Tutti")
        self.log_filter.pack(side="left", padx=5)
        
        ttk.Button(filter_frame, text="Pulisci Log", command=self.clear_log).pack(side="right")
        
        # Area log
        log_text_frame = ttk.Frame(self.frame)
        log_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_text_frame, wrap=tk.WORD, height=10)
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
    
    def get_widget(self):
        """Restituisce il widget di testo per il logging"""
        return self.log_text
    
    def clear_log(self):
        """Pulisce il log"""
        self.log_text.delete(1.0, tk.END) 