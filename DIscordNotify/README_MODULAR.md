# Discord Monitor - Versione Modulare

Questo progetto è stato riorganizzato in una struttura modulare per una migliore manutenibilità e organizzazione del codice.

## Struttura dei Moduli

### 📸 `screenshot_module.py`
**Responsabilità**: Cattura e gestione degli screenshot
- **`AreaSelector`**: Gestisce la selezione dell'area di monitoraggio con overlay trasparente
- **`ScreenshotManager`**: Cattura screenshot e preprocessa le immagini per OCR
- **Funzionalità**:
  - Cattura screenshot dell'area selezionata
  - Preprocessing delle immagini (grayscale, upscale, sharpen, invert)
  - Visualizzazione debug delle immagini preprocessate

### 🔍 `ocr_module.py`
**Responsabilità**: Elaborazione OCR e analisi del testo
- **`OCRProcessor`**: Gestisce l'estrazione del testo dalle immagini
- **`TextAnalyzer`**: Analizza e processa il testo estratto
- **`eliz_data_trade`**: Dataclass per i dati di trading
- **Funzionalità**:
  - Estrazione testo con Tesseract OCR
  - Calcolo hash per rilevare cambiamenti
  - Parsing dei dati di trading da messaggi Eliz
  - Pulizia del testo (rimozione caratteri prima di Lo/Sh, w/, @)

### 🧠 `analysis_module.py`
**Responsabilità**: Analisi dei messaggi e identificazione di contenuti rilevanti
- **`MessageAnalyzer`**: Analizza i messaggi per identificare trade e contenuti importanti
- **Funzionalità**:
  - Rilevamento nuovi messaggi
  - Filtro per parole chiave
  - Gestione storico messaggi
  - Estrazione dati di trading
  - Salvataggio/caricamento messaggi in JSON

### 📱 `notification_module.py`
**Responsabilità**: Invio notifiche su Telegram
- **`TelegramNotifier`**: Gestisce tutte le comunicazioni con Telegram
- **Funzionalità**:
  - Invio messaggi generici
  - Notifiche specifiche per messaggi Discord
  - Notifiche per trade rilevati
  - Notifiche di errore
  - Test connessione bot

### 📝 `logging_module.py`
**Responsabilità**: Logging e tracciamento delle attività
- **`LogManager`**: Gestisce il sistema di logging
- **`LogWidget`**: Widget GUI per la visualizzazione dei log
- **Funzionalità**:
  - Log su GUI e console
  - Salvataggio su file (formato testo e JSON)
  - Filtri per livello di log
  - Esportazione log per date
  - Colori per diversi livelli di log

### 🏦 `logicheapiexchange.py`
**Responsabilità**: Interfaccia con l'exchange Bybit
- **`BybitTrader`**: Gestisce tutte le operazioni di trading
- **Funzionalità**:
  - Piazzamento ordini (Market/Limit)
  - Gestione posizioni
  - Impostazione Stop Loss/Take Profit
  - Recupero saldi e PnL

### 🎯 `main_modular.py`
**Responsabilità**: Coordinamento di tutti i moduli e interfaccia utente
- **`AdvancedDiscordMonitor`**: Classe principale che orchestra tutti i moduli
- **Funzionalità**:
  - Setup dell'interfaccia grafica
  - Coordinamento tra moduli
  - Gestione configurazioni
  - Loop principale di monitoraggio

## Vantaggi della Struttura Modulare

### 🔧 **Manutenibilità**
- Ogni modulo ha una responsabilità specifica
- Facile identificare e correggere problemi
- Modifiche isolate per funzionalità

### 🧪 **Testabilità**
- Ogni modulo può essere testato indipendentemente
- Mock objects facili da implementare
- Test unitari più semplici

### 🔄 **Riutilizzabilità**
- Moduli possono essere riutilizzati in altri progetti
- Interfacce chiare tra moduli
- Dipendenze esplicite

### 👥 **Collaborazione**
- Team diversi possono lavorare su moduli diversi
- Conflitti Git ridotti
- Code review più focalizzate

### 📈 **Scalabilità**
- Facile aggiungere nuove funzionalità
- Moduli possono essere estesi senza modificare altri
- Architettura flessibile

## Come Utilizzare

### Avvio dell'Applicazione
```bash
python main_modular.py
```

### Configurazione
1. Imposta le variabili d'ambiente nel file `.env`:
   ```
   TELEGRAM_TOKEN=il_tuo_token_bot
   TELEGRAM_CHAT_ID=il_tuo_chat_id
   ```

2. Configura il file `config.ini` per Bybit:
   ```ini
   [bybit]
   api_key=la_tua_api_key
   api_secret=il_tuo_api_secret
   ```

### Flusso di Lavoro
1. **Setup**: L'applicazione carica configurazioni e inizializza tutti i moduli
2. **Selezione Area**: L'utente seleziona l'area da monitorare
3. **Monitoraggio**: Il sistema cattura screenshot periodicamente
4. **OCR**: Le immagini vengono processate per estrarre testo
5. **Analisi**: I messaggi vengono analizzati per identificare trade
6. **Notifiche**: Telegram viene notificato dei nuovi messaggi/trade
7. **Trading**: Se configurato, vengono eseguiti ordini automatici

## Estensioni Future

### Possibili Nuovi Moduli
- **`database_module.py`**: Persistenza dati su database
- **`backtest_module.py`**: Backtesting delle strategie
- **`risk_module.py`**: Gestione del rischio
- **`reporting_module.py`**: Generazione report
- **`webhook_module.py`**: Webhook per integrazioni esterne

### Miglioramenti
- **Configurazione dinamica**: Modifica parametri senza riavvio
- **Plugin system**: Caricamento dinamico di moduli
- **API REST**: Interfaccia web per controllo remoto
- **Dashboard**: Interfaccia web per monitoraggio

## Troubleshooting

### Problemi Comuni
1. **OCR non funziona**: Verifica installazione Tesseract
2. **Screenshot vuoti**: Controlla area selezionata
3. **Telegram non invia**: Verifica token e chat ID
4. **Trading non funziona**: Controlla configurazione Bybit

### Debug
- Usa il sistema di logging integrato
- Controlla i file di log in `logs/`
- Testa ogni modulo separatamente
- Verifica le configurazioni

## Dipendenze

### Principali
- `tkinter`: Interfaccia grafica
- `pyautogui`: Screenshot
- `pytesseract`: OCR
- `opencv-python`: Elaborazione immagini
- `requests`: Comunicazioni HTTP
- `pybit`: API Bybit

### Opzionali
- `python-dotenv`: Variabili d'ambiente
- `pillow`: Elaborazione immagini
- `numpy`: Calcoli numerici 