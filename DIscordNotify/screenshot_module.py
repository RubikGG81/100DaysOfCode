import tkinter as tk
from tkinter import ttk
import pyautogui
import cv2
import numpy as np
from PIL import Image, ImageTk
import time
import mss
from dataclasses import dataclass
import os

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
    def __init__(self, monitor_area=None, templates_dir=None):
        self.monitor_area = monitor_area
        self.loaded_templates = {}
        if templates_dir:
            if not os.path.isdir(templates_dir):
                raise FileNotFoundError(f"La directory dei template non è stata trovata: {templates_dir}")
            
            for filename in os.listdir(templates_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    path = os.path.join(templates_dir, filename)
                    template_data = cv2.imread(path, 0) # Carica in scala di grigi
                    if template_data is not None:
                        self.loaded_templates[filename] = template_data
                    else:
                        print(f"Attenzione: impossibile caricare il template {path}")
            print(f"Caricati {len(self.loaded_templates)} template dalla directory: {templates_dir}")

    
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

    def find_template(self, template_path, threshold=0.8):
        """
        Cerca un'immagine template all'interno dell'area monitorata.
        Restituisce le coordinate del match se trovato, altrimenti None.
        """
        if not self.monitor_area:
            raise ValueError("Area di monitoraggio non impostata")

        # Cattura lo screenshot dell'area
        screenshot_pil = self.capture_screenshot()
        screenshot_cv = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2BGR)
        
        # Carica il template
        template = cv2.imread(template_path)
        if template is None:
            raise FileNotFoundError(f"Immagine template non trovata a: {template_path}")

        # Esegui il template matching
        res = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            # Le coordinate sono relative all'area dello screenshot
            top_left = max_loc
            h, w, _ = template.shape
            bottom_right = (top_left[0] + w, top_left[1] + h)
            
            # Converte le coordinate in coordinate globali dello schermo
            global_x = self.monitor_area[0] + top_left[0]
            global_y = self.monitor_area[1] + top_left[1]
            
            return (global_x, global_y, w, h)
        
        return None

    def find_templates_in_image(self, image_to_search, threshold=0.8):
        """
        Cerca i template pre-caricati all'interno di un'immagine fornita.
        Restituisce un set con i nomi dei file dei template trovati.
        """
        if not self.loaded_templates:
            print("Attenzione: Nessun template è stato caricato. La ricerca non verrà eseguita.")
            return set()

        if isinstance(image_to_search, Image.Image):
            image_cv = cv2.cvtColor(np.array(image_to_search), cv2.COLOR_RGB2BGR)
        elif isinstance(image_to_search, np.ndarray):
            image_cv = image_to_search
        else:
            raise TypeError("Il formato dell'immagine non è supportato. Fornire un'immagine PIL o un array NumPy.")

        search_gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        
        found_templates = set()

        for template_filename, template_data in self.loaded_templates.items():
            res = cv2.matchTemplate(search_gray, template_data, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            if max_val >= threshold:
                found_templates.add(template_filename)
        
        return found_templates

@dataclass
class ScreenshotResult:
    image: Image.Image
    preprocessed_image: np.ndarray

def select_area_and_get_screenshot():
    """Funzione principale per avviare la selezione e catturare lo screenshot"""
    
    selected_area = None
    
    def on_area_selected(area):
        nonlocal selected_area
        selected_area = area
    
    selector = AreaSelector(callback=on_area_selected)
    selector.start_selection()
    
    if selected_area:
        manager = ScreenshotManager(monitor_area=selected_area)
        
        # Cattura e preprocessa
        preprocessed_img = manager.capture_and_preprocess()
        
        # Cattura un'immagine non processata per il salvataggio
        original_img = manager.capture_screenshot()
        
        return ScreenshotResult(image=original_img, preprocessed_image=preprocessed_img)
    
    return None

def find_template_on_screen(template_path, threshold=0.8):
    """
    Seleziona un'area dello schermo e cerca un'immagine template al suo interno.
    """
    selected_area = None
    
    def on_area_selected(area):
        nonlocal selected_area
        selected_area = area
        
    selector = AreaSelector(callback=on_area_selected)
    selector.start_selection()
    
    if selected_area:
        manager = ScreenshotManager(monitor_area=selected_area)
        print(f"Area selezionata: {selected_area}")
        print(f"Ricerca del template: {template_path}")
        
        match_location = manager.find_template(template_path, threshold)
        
        if match_location:
            print(f"Template trovato alle coordinate globali: {match_location}")
            return match_location
        else:
            print("Template non trovato.")
            return None
    else:
        print("Selezione dell'area annullata.")
        return None

if __name__ == '__main__':
    # Esempio di utilizzo del nuovo metodo find_templates_in_image

    # 1. Definisci il percorso della cartella dei template
    templates_folder = "templates"
    if not os.path.exists(templates_folder):
        print(f"Creazione della directory dei template: {templates_folder}")
        os.makedirs(templates_folder)

        # Crea due template fittizi
        print("Creazione di template fittizi...")
        template1 = np.zeros((40, 80, 3), dtype=np.uint8)
        cv2.putText(template1, 'Btn_OK', (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(templates_folder, "ok_button.png"), template1)

        template2 = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.putText(template2, 'X', (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
        cv2.imwrite(os.path.join(templates_folder, "close_icon.png"), template2)

    # 2. Simula di avere un'immagine già catturata
    screenshot_to_search_path = "test_screenshot_multi.png"
    if not os.path.exists(screenshot_to_search_path):
        print(f"Creazione di un'immagine di ricerca fittizia: {screenshot_to_search_path}")
        dummy_screenshot = np.full((400, 500, 3), (20, 20, 20), dtype=np.uint8)
        
        # Posiziona i template nell'immagine di ricerca
        ok_btn_img = cv2.imread(os.path.join(templates_folder, "ok_button.png"))
        close_icon_img = cv2.imread(os.path.join(templates_folder, "close_icon.png"))
        
        dummy_screenshot[50:90, 100:180] = ok_btn_img      # Posizione del pulsante OK
        dummy_screenshot[200:250, 300:350] = close_icon_img # Posizione dell'icona di chiusura
        cv2.imwrite(screenshot_to_search_path, dummy_screenshot)

    # 3. Carica l'immagine in cui cercare
    try:
        # 4. Crea un'istanza di ScreenshotManager UNA SOLA VOLTA, caricando i template
        print("--- Inizializzazione del Manager ---")
        manager = ScreenshotManager(templates_dir=templates_folder)
        print("---------------------------------")

        # 5. Carica l'immagine in cui cercare
        image_to_search = Image.open(screenshot_to_search_path)
        print(f"\nImmagine di ricerca caricata: {screenshot_to_search_path}")

        # 6. Esegui la ricerca usando i template pre-caricati
        found_template_names = manager.find_templates_in_image(
            image_to_search=image_to_search,
            threshold=0.8
        )

        # 7. Controlla i risultati
        if found_template_names:
            print(f"\nTrovati {len(found_template_names)} template nell'immagine:")
            for name in found_template_names:
                print(f"  - Presente: {name}")
            
            # Esempio di come verificare la presenza di un template specifico
            if "ok_button.png" in found_template_names:
                print("\nConferma: Il template 'ok_button.png' è stato trovato.")

        else:
            print("Nessun template è stato trovato nell'immagine fornita.")

    except FileNotFoundError as e:
        print(f"Errore: {e}. Assicurati che i file e le cartelle esistano.")
    except Exception as e:
        print(f"Si è verificato un errore inaspettato: {e}")
 