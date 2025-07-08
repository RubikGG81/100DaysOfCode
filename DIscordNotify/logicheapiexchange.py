import configparser
from pybit.unified_trading import HTTP
import time


### sito per controllo trade test
# https://testnet.bybit.com/trade/usdt/BTCUSDT 
# ###


class BybitTrader:
    def __init__(self, config_file='config.ini'):
        self.session = self._get_session(config_file)

    def _get_session(self, config_file):
        # sourcery skip: inline-immediately-returned-variable
        config = configparser.ConfigParser()
        config.read(config_file)
        api_key = config['bybit']['api_key']
        api_secret = config['bybit']['api_secret']
        
        session = HTTP(
            testnet=True,
            api_key=api_key,
            api_secret=api_secret,
        )
        return session

    def get_balance(self):  # sourcery skip: inline-immediately-returned-variable
        try:
            balance = self.session.get_wallet_balance(accountType="UNIFIED")
            return balance
        except Exception as e:
            print(f"Errore during il recupero del saldo: {str(e)}")
            return None

    def place_order(self, symbol, side, qty, order_type="Market", price=None):
        # sourcery skip: inline-immediately-returned-variable
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": qty,
            }
            if order_type == "Limit":
                params["price"] = price

            order = self.session.place_order(**params)
            return order
        except Exception as e:
            print(f"Errore during l'invio dell'ordine: {str(e)}")
            return None

    def close_position(self, symbol, side, qty, price):
        # sourcery skip: inline-immediately-returned-variable
        # Bybit uses the same place_order function to close, but with reduce_only flag
        try:
            order = self.session.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Limit",
                qty=qty,
                price=price,
                reduce_only=True
            )
            return order
        except Exception as e:
            print(f"Errore during la chiusura della posizione: {str(e)}")
            return None

    def set_stop_loss_take_profit(self, symbol, stop_loss, take_profit):
        # sourcery skip: inline-immediately-returned-variable
        try:
            result = self.session.set_trading_stop(
                category="linear",
                symbol=symbol,
                stopLoss=stop_loss,
                takeProfit=take_profit,
            )
            return result
        except Exception as e:
            print(f"Errore during l'impostazione di SL/TP: {str(e)}")
            return None

    def get_positions(self, symbol=None):
        # sourcery skip: inline-immediately-returned-variable
        try:
            positions = self.session.get_positions(category="linear", symbol=symbol)
            return positions
        except Exception as e:
            print(f"Errore during il recupero delle posizioni: {str(e)}")
            return None

    def get_pnl(self, symbol):
        try:
            # This gets unrealized PNL for open positions
            positions = self.get_positions(symbol)
            if positions and positions['result']['list']:
                for position in positions['result']['list']:
                    if position['symbol'] == symbol and float(position['size']) > 0:
                        return position['unrealisedPnl']
            return "0" # Return 0 if no position is found
        except Exception as e:
            print(f"Errore during il recupero del PNL: {str(e)}")
            return None


# sourcery skip: use-named-expression
# sourcery skip: use-named-expression
if __name__ == '__main__':
    trader = BybitTrader()
    
    # Esempio di utilizzo:
    symbol = "BTCUSDT"
    qty = "0.05"

    # 1. Ottenere il saldo
    balance = trader.get_balance()
    if balance:
        print(f'Saldo Iniziale --->>{balance}')
        # print(balance) # Commentato per brevità

    # 2. Piazzare un ordine di MERCATO per aprire una posizione
    print("\n--- Piazzamento Ordine a Mercato ---")
    # Usiamo un ordine a mercato per essere sicuri che la posizione si apra subito
    order = trader.place_order(symbol, "Buy", qty, order_type="Market")
    if order:
        print("Ordine a mercato piazzato con successo:")
        print(order)
        # Diamo un attimo di tempo all'API per registrare la posizione
        time.sleep(2) 

    # 3. Ottenere le posizioni aperte per verificare
    print("\n--- Posizioni Aperte ---")
    positions = trader.get_positions(symbol)
    if positions and positions['result']['list']:
        print("Posizioni aperte:")
        print(positions['result']['list'])
        
        # Prendiamo il prezzo di entrata per calcolare SL/TP
        entry_price = float(positions['result']['list'][0]['avgPrice'])
        sl_price = str(entry_price * 0.95) # Stop loss al 5% sotto l'entrata
        tp_price = str(entry_price * 1.05) # Take profit al 5% sopra l'entrata

        # 4. Impostare Stop Loss e Take Profit
        print("\n--- Impostazione SL/TP ---")
        print(f"Impostazione SL a {sl_price} e TP a {tp_price}")
        sl_tp = trader.set_stop_loss_take_profit(symbol, sl_price, tp_price)
        if sl_tp:
            print("SL/TP impostati con successo:")
            print(sl_tp)

        """# 5. Ottenere PNL non realizzato
        print("\n--- PNL Non Realizzato ---")
        pnl = trader.get_pnl(symbol)
        if pnl:
            print(f"PNL non realizzato per {symbol}: {pnl}") """

        """ # 6. Chiudere la posizione (esempio con un ordine di vendita a mercato)
        # Per chiudere, piazziamo un ordine opposto (Sell)
        print("\n--- Chiusura Posizione ---")
        close_order = trader.place_order(symbol, "Sell", qty, order_type="Market")
        if close_order:
            print("Ordine di chiusura piazzato con successo:")
            print(close_order) """