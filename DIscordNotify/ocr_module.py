import pytesseract
import hashlib
from dataclasses import dataclass

class OCRProcessor:
    def __init__(self):
        self.custom_config = r'--oem 3 --psm 6 -l eng'
    
    def extract_text(self, preprocessed_image):
        """Estrae testo da un'immagine preprocessata"""
        try:
            text = pytesseract.image_to_string(preprocessed_image, config=self.custom_config)
            return text.strip()
        except Exception as e:
            print(f"Errore OCR: {e}")
            return ""
    
    def calculate_image_hash(self, image):
        """Calcola hash dell'immagine per rilevare cambiamenti"""
        return hashlib.md5(image.tobytes()).hexdigest()
    
    def test_ocr(self, preprocessed_image):
        """Testa l'OCR su un'immagine preprocessata"""
        text = self.extract_text(preprocessed_image)
        return {
            'text': text,
            'char_count': len(text),
            'success': bool(text.strip())
        }

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
    side: str  # 'Buy' or 'Sell'

class TextAnalyzer:
    def __init__(self):
        pass
    
    def remove_before_lo_or_sh_ww_simple(self, text):
        """Rimuove caratteri prima di Lo/Sh, rimuove w/ e tutto dopo @"""
        # 1. Trova la prima occorrenza di "Lo" o "Sh"
        for i in range(len(text) - 1):
            if text[i:i+2] in ["Lo", "Sh"]:
                # Rimuovi tutto prima di Lo/Sh
                result = text[i:]
                
                # 2. Rimuovi "w/" se presente
                result = result.replace("w/", "")
                
                # 3. Trova il primo "@" e rimuovi tutto da lì in poi
                at_pos = result.find("@")
                if at_pos != -1:
                    result = result[:at_pos]
                
                return result.strip()  # Rimuovi spazi extra
        return ""
    
    def parse_eliz_trade(self, text: str) -> eliz_data_trade:
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
            side = ""
            
            # Dividi il testo in righe
            lines = text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if "long" in line.lower():
                    side = "Buy"
                elif "short" in line.lower():
                    side = "Sell"
                
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
            return eliz_data_trade(
                limit_order=limit_order,
                token_name=token_name,
                bought_token_amount=bought_token_amount,
                balance=balance,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                e_retest=e_retest,
                side=side
            )
            
        except Exception as e:
            print(f"Errore nel parsing del trade: {e}")
            # Restituisci un oggetto con valori di default in caso di errore
            return eliz_data_trade(
                limit_order=False,
                token_name="",
                bought_token_amount=0,
                balance=0,
                entry_price=0.0,
                stop_loss="",
                take_profit="",
                e_retest=False,
                side=""
            )

    def format_eliz_trade(self, trade: eliz_data_trade) -> str:
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
            print(f"Errore nella formattazione del trade: {e}")
            return "Errore nella formattazione del trade" 