import requests
from datetime import datetime

class TelegramNotifier:
    def __init__(self, token="", chat_id=""):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def set_credentials(self, token, chat_id):
        """Imposta le credenziali Telegram"""
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, message, parse_mode="Markdown"):
        """Invia un messaggio semplice a Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                return {"success": True, "message": "Messaggio inviato con successo"}
            else:
                return {"success": False, "error": f"Errore HTTP: {response.status_code}", "response": response.text}
                
        except Exception as e:
            return {"success": False, "error": f"Errore di connessione: {str(e)}"}
    
    def send_discord_notification(self, message):
        """Invia notifica specifica per messaggi Discord"""
        try:
            telegram_message = f"""
🔔 **Nuovo messaggio Discord**
📱 Rilevato: {datetime.now().strftime('%H:%M:%S')}
📝 Contenuto:
{message}
"""
            
            return self.send_message(telegram_message)
            
        except Exception as e:
            return {"success": False, "error": f"Errore nella formattazione del messaggio: {str(e)}"}
    
    def send_trade_notification(self, trade_data, action="Nuovo trade rilevato"):
        """Invia notifica specifica per trade"""
        try:
            telegram_message = f"""
🚀 **{action}**
📊 Token: {trade_data.token_name}
💰 Entry Price: {trade_data.entry_price}
📈 Side: {trade_data.side}
🛑 Stop Loss: {trade_data.stop_loss}
🎯 Take Profit: {trade_data.take_profit}
⏰ Rilevato: {datetime.now().strftime('%H:%M:%S')}
"""
            
            return self.send_message(telegram_message)
            
        except Exception as e:
            return {"success": False, "error": f"Errore nella formattazione del trade: {str(e)}"}
    
    def send_error_notification(self, error_message):
        """Invia notifica di errore"""
        try:
            telegram_message = f"""
❌ **Errore Sistema**
⚠️ Messaggio: {error_message}
⏰ Timestamp: {datetime.now().strftime('%H:%M:%S')}
"""
            
            return self.send_message(telegram_message)
            
        except Exception as e:
            return {"success": False, "error": f"Errore nell'invio notifica errore: {str(e)}"}
    
    def test_connection(self):
        """Testa la connessione con Telegram"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            
            if response.status_code == 200:
                bot_info = response.json()
                return {"success": True, "bot_name": bot_info['result']['first_name']}
            else:
                return {"success": False, "error": f"Errore API: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": f"Errore di connessione: {str(e)}"} 