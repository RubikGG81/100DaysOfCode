# monitor_service.py

import configparser
import cv2
import numpy as np
import time
import hashlib
import mss
import json
import os
import requests
import pytesseract
from datetime import datetime
from dataclasses import dataclass
import logging
from logicheapiexchange import BybitTrader

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("monitor_service.log"),
        logging.StreamHandler()
    ]
)

# --- Data Classes and Parsers (Copied from main.py) ---
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
    side: str # 'Buy' or 'Sell'

def parse_eliz_trade(text: str) -> eliz_data_trade:
    try:
        limit_order = False
        token_name = ""
        bought_token_amount = 0
        balance = 0
        entry_price = 0.0
        stop_loss = ""
        take_profit = ""
        e_retest = False
        side = ""

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
                limit_order = True

            if line.startswith("Token Name:"):
                token_name = line.replace("Token Name:", "").strip()
            elif line.startswith("Bought Token Amount:"):
                try:
                    bought_token_amount = int(line.replace("Bought Token Amount:", "").strip())
                except ValueError:
                    bought_token_amount = 0
            elif line.startswith("Balance:"):
                try:
                    balance = int(line.replace("Balance:", "").strip())
                except ValueError:
                    balance = 0
            elif line.startswith("Entry Price:"):
                try:
                    entry_price = float(line.replace("Entry Price:", "").strip())
                except ValueError:
                    entry_price = 0.0
            elif line.startswith("Stop Loss:"):
                sl_str = line.replace("Stop Loss:", "").strip()
                try:
                    stop_loss = float(sl_str)
                except ValueError:
                    stop_loss = sl_str
            elif line.startswith("Take Profit:"):
                tp_str = line.replace("Take Profit:", "").strip()
                try:
                    take_profit = float(tp_str)
                except ValueError:
                    take_profit = tp_str
            elif line.startswith("EP Retest:"):
                retest_str = line.replace("EP Retest:", "").strip()
                e_retest = retest_str.lower() in ['true', 'yes', '1', 'si', 'sì']

        return eliz_data_trade(
            limit_order=limit_order, token_name=token_name,
            bought_token_amount=bought_token_amount, balance=balance,
            entry_price=entry_price, stop_loss=stop_loss,
            take_profit=take_profit, e_retest=e_retest, side=side
        )
    except Exception as e:
        logging.error(f"Errore nel parsing del trade: {e}")
        return eliz_data_trade(
            limit_order=False, token_name="", bought_token_amount=0, balance=0,
            entry_price=0.0, stop_loss="", take_profit="", e_retest=False, side=""
        )

# --- Core Monitor Class ---
class HeadlessMonitor:
    def __init__(self, config):
        self.config = config
        self.bybit_trader = BybitTrader()
        self.last_messages = self.load_last_messages()
        self.is_monitoring = False

        self.telegram_token = config.get('telegram', 'token')
        self.telegram_chat_id = config.get('telegram', 'chat_id')
        self.interval = config.getint('monitoring', 'interval', fallback=2)
        self.source_filter = config.get('monitoring', 'source_filter', fallback='@Eliz Challenge')
        self.keywords = [kw.strip() for kw in config.get('monitoring', 'keywords', fallback='long,short,@').split(',')]
        self.keywords_eliz = [kw.strip() for kw in config.get('monitoring', 'keywords_eliz', fallback='current trade').split(',')]
        
        self.monitor_area = (
            config.getint('area', 'x'),
            config.getint('area', 'y'),
            config.getint('area', 'width'),
            config.getint('area', 'height')
        )

    def load_last_messages(self):
        try:
            if os.path.exists('last_messages.json'):
                with open('last_messages.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logging.error(f"Errore caricamento messaggi: {e}")
            return []

    def save_last_messages(self):
        try:
            with open('last_messages.json', 'w', encoding='utf-8') as f:
                json.dump(self.last_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Errore salvataggio messaggi: {e}")

    def send_telegram_notification(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            telegram_message = f"🔔 **Nuovo messaggio Discord**\n📱 Rilevato: {datetime.now().strftime('%H:%M:%S')}\n📝 Contenuto:\n{message}"
            data = {"chat_id": self.telegram_chat_id, "text": telegram_message, "parse_mode": "Markdown"}
            response = requests.post(url, data=data)
            if response.status_code == 200:
                logging.info("Notifica Telegram inviata")
            else:
                logging.error(f"Errore Telegram: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Errore invio Telegram: {e}")

    def detect_new_messages(self, text, last_messages):
        new_messages = []
        for line in text.split('\n'):
            if any(kw in line.lower() for kw in self.keywords if kw):
                current_message = self.remove_before_lo_or_sh_ww_simple(line)
                if current_message:
                    message_hash = hashlib.md5(current_message.encode()).hexdigest()
                    if message_hash not in last_messages:
                        new_messages.append(current_message)
        return new_messages

    def detect_new_messages_eliz(self, text, last_messages):
        new_messages = []
        current_message = []
        for line in text.split('\n'):
            line = line.strip()
            if any(kw in line.lower() for kw in self.keywords_eliz if kw):
                if current_message:
                    message_text = '\n'.join(current_message)
                    if hashlib.md5(message_text.encode()).hexdigest() not in last_messages:
                        new_messages.append(message_text)
                current_message = [line]
            elif not line.startswith("(Edited"):
                current_message.append(line)
        if current_message:
            message_text = '\n'.join(current_message)
            if hashlib.md5(message_text.encode()).hexdigest() not in last_messages:
                new_messages.append(message_text)
        return new_messages

    def remove_before_lo_or_sh_ww_simple(self, text):
        for i in range(len(text) - 1):
            if text[i:i+2] in ["Lo", "Sh"]:
                result = text[i:].replace("w/", "")
                at_pos = result.find("@")
                if at_pos != -1:
                    result = result[:at_pos]
                return result.strip()
        return ""

    def start(self):
        self.is_monitoring = True
        logging.info("Monitoraggio headless avviato.")
        self.monitor_loop()

    def stop(self):
        self.is_monitoring = False
        logging.info("Monitoraggio headless fermato.")
        self.save_last_messages()

    def monitor_loop(self):
        last_hash = None
        first_message_dropped = False

        while self.is_monitoring:
            try:
                with mss.mss() as sct:
                    monitor = {"top": self.monitor_area[1], "left": self.monitor_area[0], "width": self.monitor_area[2], "height": self.monitor_area[3]}
                    sct_img = sct.grab(monitor)
                    img_cv = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)

                logging.info("Screen taken")

                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
                sharp = cv2.filter2D(gray, -1, np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]]))
                inverted = cv2.bitwise_not(sharp)
                img_hash = hashlib.md5(inverted.tobytes()).hexdigest()

                if last_hash != img_hash:
                    last_hash = img_hash
                    text = pytesseract.image_to_string(inverted, config=r'--oem 3 --psm 6 -l eng')

                    if text.strip():
                        detector = self.detect_new_messages_eliz if self.source_filter == "@Eliz Challenge" else self.detect_new_messages
                        new_messages = detector(text, self.last_messages)

                        for message in new_messages:
                            if not first_message_dropped:
                                first_message_dropped = True
                                continue

                            logging.info(f"Nuovo messaggio: {message[:50]}...")
                            self.send_telegram_notification(message)

                            if "Current Trade" in message:
                                trade_data = parse_eliz_trade(message)
                                logging.info(f"Trade rilevato: {trade_data.token_name} - Side: {trade_data.side}")
                                # Trading logic here...
                                symbol = trade_data.token_name + "USDT"
                                qty = str(trade_data.bought_token_amount)
                                side = trade_data.side
                                order_type = "Limit" if trade_data.limit_order else "Market"
                                price = str(trade_data.entry_price) if trade_data.limit_order else None
                                
                                order_result = self.bybit_trader.place_order(symbol, side, qty, order_type, price)
                                if order_result and order_result.get('retCode') == 0:
                                    logging.info(f"Ordine {order_type} piazzato per {symbol}")
                                    if order_type == "Market": time.sleep(2)
                                    
                                    sl = str(trade_data.stop_loss) if trade_data.stop_loss else None
                                    tp = str(trade_data.take_profit) if trade_data.take_profit else None
                                    if sl or tp:
                                        sl_tp_result = self.bybit_trader.set_stop_loss_take_profit(symbol, sl, tp)
                                        if sl_tp_result and sl_tp_result.get('retCode') == 0:
                                            logging.info(f"SL/TP impostati per {symbol}.")
                                        else:
                                            logging.error(f"Errore impostazione SL/TP: {sl_tp_result.get('retMsg')}")
                                else:
                                    logging.error(f"Errore piazzamento ordine: {order_result.get('retMsg')}")


                            self.last_messages.append(hashlib.md5(message.encode()).hexdigest())
                            self.last_messages = self.last_messages[-30:]
                            self.save_last_messages()

                time.sleep(self.interval)
            except Exception as e:
                logging.error(f"Errore nel loop: {e}", exc_info=True)
                time.sleep(1)

if __name__ == '__main__':
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        logging.error("Errore: config.ini non trovato. Esegui main.py per crearlo.")
    else:
        config.read('config.ini')
        if not config.has_section('area') or not config.has_section('telegram'):
             logging.error("Errore: config.ini incompleto. Esegui main.py per salvarlo correttamente.")
        else:
            monitor = HeadlessMonitor(config)
            try:
                monitor.start()
            except KeyboardInterrupt:
                monitor.stop()
