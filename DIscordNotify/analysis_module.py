import hashlib
import json
import os
from ocr_module import TextAnalyzer, eliz_data_trade

class MessageAnalyzer:
    def __init__(self, keywords="", keywords_eliz="", source_filter="@Eliz Challenge"):
        self.keywords = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        self.keywords_eliz = [kw.strip() for kw in keywords_eliz.split(',') if kw.strip()]
        self.source_filter = source_filter
        self.text_analyzer = TextAnalyzer()
        self.last_messages = self.load_last_messages()
    
    def set_keywords(self, keywords):
        """Imposta le parole chiave generiche"""
        self.keywords = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    
    def set_keywords_eliz(self, keywords_eliz):
        """Imposta le parole chiave per Eliz"""
        self.keywords_eliz = [kw.strip() for kw in keywords_eliz.split(',') if kw.strip()]
    
    def set_source_filter(self, source_filter):
        """Imposta il filtro sorgente"""
        self.source_filter = source_filter
    
    def detect_new_messages(self, text, last_messages):
        """Rileva nuovi messaggi nel testo generico"""
        new_messages = []
        
        # Dividi in righe
        lines = text.split('\n')
        
        # Trova messaggi con parole chiave
        current_message = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Controlla se contiene parole chiave
            has_keyword = any(kw in line.lower() for kw in self.keywords if kw)
            
            if has_keyword:
                # Salva messaggio precedente
                if current_message := self.text_analyzer.remove_before_lo_or_sh_ww_simple(line):
                    message_hash = hashlib.md5(current_message.encode()).hexdigest()
                    
                    if message_hash not in last_messages:
                        new_messages.append(current_message)
                
                # Inizia nuovo messaggio
                current_message = []
        
        return new_messages
    
    def detect_new_messages_eliz(self, text, last_messages):
        """Rileva nuovi messaggi nel testo di Eliz"""
        new_messages = []
        
        # Dividi in righe
        lines = text.split('\n')
        
        # Trova messaggi con parole chiave
        current_message = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Controlla se contiene parole chiave
            has_keyword = any(kw in line.lower() for kw in self.keywords_eliz if kw)
            
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
        
        return new_messages
    
    def analyze_messages(self, text, last_messages):
        """Analizza i messaggi in base al filtro sorgente"""
        if self.source_filter == "@Eliz Challenge":
            return self.detect_new_messages_eliz(text, last_messages)
        else:
            return self.detect_new_messages(text, last_messages)
    
    def extract_trade_data(self, message):
        """Estrae dati di trading da un messaggio"""
        if "Current Trade" in message:
            return self.text_analyzer.parse_eliz_trade(message)
        return None
    
    def save_last_messages(self, messages, filename='last_messages.json'):
        """Salva last_messages in un file JSON"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Errore nel salvataggio dei messaggi: {e}")
            return False
    
    def load_last_messages(self, filename='last_messages.json'):
        """Carica last_messages da un file JSON"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                return messages
            else:
                return []
        except Exception as e:
            print(f"Errore nel caricamento dei messaggi: {e}")
            return []
    
    def update_last_messages(self, new_message_hash):
        """Aggiorna la lista dei messaggi recenti"""
        self.last_messages.append(new_message_hash) #Fa update della lista degli ultimi messaggi al volo
        
        # Mantieni solo ultimi 30 messaggi
        if len(self.last_messages) > 30:
            self.last_messages = self.last_messages[-30:] 