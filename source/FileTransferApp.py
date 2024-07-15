import os.path

import Tools
from FileTransfer import FileTransfer, SelectingFoldersError, TransferingFilesError, ComparingFoldersError
from kivy.config import Config
from functools import partial

Config.read("D:\\MyPython\\FileTransfer\\dist\\FileTransfer\\_internal\\settings\\config_filetransfer.ini")
Tools.set_center_app(Config)

LOG_LEVELS = {10: logging.DEBUG, 20: logging.INFO, 30: logging.WARNING, 40: logging.ERROR, 50: logging.CRITICAL}

from Widgets import *
from kivy.app import App
# from kivy.uix.button import Button
# from kivy.uix.label import Label
# from kivy.uix.modalview import ModalView
# from kivy.lang import Builder
# from kivy.properties import StringProperty, ObjectProperty
# from kivy.uix.widget import Widget
# from kivy.core.audio import SoundLoader
# from kivy.clock import Clock
# from kivy.animation import Animation
# from kivy.graphics import Ellipse, Color


def sound_decorator(sound_file_path):
    """Decoratore per associare l'esecuzione di un suono al termine di una funzione"""
    def wrap(function_to_wrap):
        def sound_function(*args, **kwargs):
            sound = SoundLoader.load(sound_file_path)  # suono da riprodurre
            if sound:
                sound.play()
            else:
                logging.warning("[%-15s]: file audio %s non trovato!", "FileTransferApp", sound_file_path)
            function_to_wrap(*args, **kwargs)
        return sound_function
    return wrap


class FileTransferApp(App):
    colors = {key: [float(element.strip()) for element in value[1:len(value) - 1].split(",")] for key, value in Config["kivy_colors"].items()}  # dizionario --> nome_colore: rgba
    source_path = ObjectProperty("")              # percorso di origine (più aggiornato)
    destination_path = ObjectProperty("")         # percorso di destinazione (da aggiornare)

    def __init__(self, **kwargs):
        create_logger(level=LOG_LEVELS[Config.getint("log", "log_level")],
                      log_path=Config["log"]["log_path"],
                      log_name=Config["log"]["log_name"],
                      fmt=Config["log"]["format"])

        logging.info("[%-15s]: %s", "FileTransferApp", "#" * 80)
        logging.info("[%-15s]: applicazione avviata", "FileTransferApp")
        self.ft = FileTransfer()                # istanza di FileTransfer, con cui gestirò le azioni più a basso livello
        self._stopped = False                   # variabile interna mi serve per evitare di scrivere due volte sul log quando chiudo l'app
        self.main_popup_instance = None         # reference del popup principale

        super().__init__(**kwargs)

    def build(self):
        Builder.load_file("../kv/Style.kv")
        Builder.load_file("../kv/MyDefaultWidgets.kv")
        logging.debug("[%-15s]: caricati i fogli di stile .kv", "FileTransferApp")
        self.main_popup_instance = MainPopup()
        self.main_popup_instance.open()

    def check_src_dst(self):
        """Se entrambi self.source_path e self.destination_path sono popolati (cioè <> ""), verifica i valori inseriti
        con il metodo FileTransfer.check_folders()"""
        if self.source_path != "" and self.destination_path != "":
            try:
                self.ft.check_folders(self.source_path, self.destination_path)
            except SelectingFoldersError as error:
                ErrorPopup(error_text=str(error)).open()
                App.get_running_app().main_popup_instance.ids.start_analisys_btn.opacity = 0
            else:   # rendo visibile il bottone per iniziare l'analisi e chiudo il popup
                self.main_popup_instance.ids.start_analisys_btn.opacity = 1

    def start_analysis(self):
        """Funzione per l'analisi di SRC e DST, prima crea gli alberi di directory (FileTransfer.set_foders()) poi scrive
        il file compare.txt (FileTransfer.compare())"""
        try:
            self.ft.set_folders()
            self.ft.compare()

        except (ComparingFoldersError, SelectingFoldersError) as error:
            ErrorPopup(error_text=str(error)).open()
            self.clear_labels()

        else:   # se tutto è andato come previsto apro il popup ad analisi terminata
            AnalyzerPopup().open()

    def start_transfer(self, popup_to_close):
        """Metodo lanciato all'inizio del trasferimento, apre il popup 'trasferimento in corso' durante l'effettivo
        trasferimento e chiude quello dell'analisi (popup_to_update)"""
        transfering_popup = TransferingPopup()
        transfering_popup.open()
        Clock.schedule_once(popup_to_close.dismiss, 0)                      # chiudo il popup precedentemente aperto (AnalyzerPopup)
        Clock.schedule_once(partial(self.transfer, transfering_popup), 1)   # avvio il trasferimento

    def transfer(self, popup_to_close, *args):
        """Metodo per eseguire le azioni di allineamento di DST a SRC, wrappa FileTransfer.transfer(), al termine apre
        il popup informativo sull'avvenuto trasferimento, avvisando nel caso di errori verificatisi"""
        popup_to_close.dismiss()

        try:
            errors_occurred = self.ft.transfer()

        except TransferingFilesError as error:
            ErrorPopup(error_text=str(error)).open()

        else:
            if errors_occurred is False:
                TransferPopup().open()

            else:
                ErrorPopup(error_text="Il trasferimento è terminato, tuttavia si sono verificati alcuni errori, controlla nel log per ulteriori dettagli").open()

            self.clear_labels()     # pulisco le etichette su SRC e DST scelte, inoltre nascondo il tasto per avviare l'analisi

    def get_compare_file(self):
        """Apre il file compare.txt"""
        try:
            self.ft.cmp_manager.compare_file.inspect()

        except ComparingFoldersError as error:
            ErrorPopup(error_text=str(error)).open()

    def on_stop(self):
        """Non è chiaro perchè ma il metodo app.stop() viene chiamato due volte, per evitare di scrivere due volte sul log
        utilizzo il parametro _stopped"""
        if not self._stopped:
            self._stopped = True

            if self.ft:
                self.ft.close()

            logging.info("[%-15s]: chiusura applicazione", "FileTransferApp")
            logging.info("[%-15s]: %s", "FileTransferApp", "#" * 80)

    def on_source_path(self, instance, path):
        """Ogni volta che viene valorizzato source verifico che source e destination siano corretti per attivare i
        bottoni e iniziare l'analisi"""
        self.check_src_dst()

    def on_destination_path(self, instance, path):
        """Come sopra"""
        self.check_src_dst()

    def clear_labels(self):
        """Alla fine del trasferimento o in caso di errore in caso di analisi/trasferimento bisogna riprendere da 0 il
        processo: pertanto rimuovo i valori sulle label di SRC e DST e delle variabili dell'app, inoltre nascondo il
        bottone di 'Avvia Analisi', questo ricompare quando il metodo self.check_src_dst() va a buon fine"""

        self.main_popup_instance.ids.source_lbl.text = ""               # testo etichetta SRC
        self.main_popup_instance.ids.destination_lbl.text = ""          # testo etichetta DST
        self.source_path = ""                         # variabile dell'app di SRC
        self.destination_path = ""                    # variabile dell'app di DST
        self.main_popup_instance.ids.start_analisys_btn.opacity = 0     # disattivo (opacità a 0) il pulsante di avvio analisi, lo riattiverò quando verifico i nuovi SRC e DST


if __name__ == "__main__":
    app = FileTransferApp()
    app.run()
