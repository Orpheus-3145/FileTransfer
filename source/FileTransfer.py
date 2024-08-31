import Tools
import stat
import os
import shutil
import logging
import time
from datetime import datetime
from enum import Enum
from Exceptions import *

# Config = configparser.ConfigParser()
# Config.read("D:\\MyPython\\FileTransfer\\dist\\FileTransfer\\_internal\\settings\\config_filetransfer.ini")

COMPARE_FILE_PATH = "compare\\"


class FtState(Enum):
    START = 0
    FOLDERS_SET = 1
    ANALYSIS_DONE = 2
    TRANSFER_DONE = 3


class FileTransfer:
    """Questa classe si occupa di:
        1) confrontare due percorsi SRC e DST creando i loro relativi alberi di directory
        2) analizzare i due alberi creati trovando le differenze tra essi (file/cartelle da copiare/rimuovere) inserendo
            tali diversità in un file testuale (compare.txt)
        3) leggere un file compare ed eseguire tutte le azioni sul FS ivi elencate, allineando DST a SRC"""

    def __init__(self):
        self.state = FtState.START
        self.base_folder_src = ""                                           # percorso file cartella più aggiornata
        self.base_folder_dst = ""                                           # percorso file cartella da aggiornare
        # self.cmp_manager = CompareFileParser()                              # istanza del parser del file compare.txt
        self.compare_file = None

        logging.info("[%-15s]: %s", "FileTransfer", "*" * 80)
        logging.info("[%-15s]: creata un'istanza di FileTransfer", "FileTransfer")

    def check_state(self, expected_state):
        if self.state != expected_state:
            raise StateError(f"action performed in a wrong state: {self.state.name}, expected: {expected_state.name}")

    def set_state(self, new_state: FtState):
        if new_state not in list(FtState):
            raise StateError(f"unknown state: {new_state.name}")
        self.state = new_state

    def refresh(self):
        self.state = FtState.START
        self.base_folder_src = ""
        self.base_folder_dst = ""

    def inspect_compare_file(self):
        """Apre il file tramite notepad/notepad++"""
        try:
            os.startfile(self.compare_file.path)
        except FileNotFoundError:
            logging.error("[%-15s]: file compare %s non trovato o rimosso", "FileTransfer", self.compare_file.path)
            raise ParserError(f"File compare.txt non presente al percorso: {self.compare_file.path}")

    def set_src_and_dst(self, folder_src, folder_dst):
        self.check_state(FtState.START)
        for path_to_check in [folder_src, folder_dst]:
            if not path_to_check:
                raise SelectingFoldersError("Inserito un path vuoto")
            elif not Tools.path_exists(folder_src):
                raise SelectingFoldersError(f"{path_to_check} non esiste")
            elif os.path.isfile(path_to_check):
                raise SelectingFoldersError(f"{path_to_check} non è un file")
        if folder_src == folder_dst:
            raise SelectingFoldersError("Path inseriti sono uguali")
        elif os.path.basename(folder_src) != os.path.basename(folder_dst):  # devono condividere il nome della cartella alla fine del percorso
            raise SelectingFoldersError("I due punti di partenza non hanno lo stesso nome")
        elif len(os.listdir(folder_src)) == 0:
            raise SelectingFoldersError("Percorso {} vuoto".format(folder_src))
        self.base_folder_src = folder_src
        self.base_folder_dst = folder_dst
        self.set_state(FtState.FOLDERS_SET)
        logging.info("[%-15s]: SRC e DST selezionati correttamente", "FileTransfer")

    def write_compare_file(self):
        """Crea il file compare.txt, tramite il parser self.cmp_manager, in cui vengono inserite tutte le operazioni sul
         FS da eseguire per allineare DST a SRC"""
        self.check_state(FtState.FOLDERS_SET)
        self.compare_file = CompareFile(COMPARE_FILE_PATH)
        with self.compare_file:
            for directory, list_dir, list_file in os.walk(self.base_folder_src):
                current_src_folder = directory
                current_dst_folder = directory.replace(self.base_folder_src, self.base_folder_dst)
                if not Tools.path_exists(current_dst_folder):  # creating missing directory
                    self.compare_file.w_cp_dir(current_src_folder, current_dst_folder)
                    for file in list_file:          # and every file it contains
                        src_file = os.path.join(current_src_folder, file)
                        if not os.path.islink(src_file):
                            self.compare_file.w_cp_file(src_file, current_dst_folder)
                else:       # if directory exists check its content
                    for file in list_file:
                        src_file = os.path.join(current_src_folder, file)
                        if os.path.islink(src_file):
                            continue
                        dst_file = os.path.join(current_dst_folder, file)
                        # copy every missing or less updated file
                        if not Tools.path_exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                            self.compare_file.w_cp_file(src_file, current_dst_folder)
                    # clean stuff in dst but missing in src
                    entities_to_rm = set(os.listdir(current_dst_folder)) - set(list_file) - set(list_dir)
                    for to_drop in entities_to_rm:
                        entity_to_drop = os.path.join(current_dst_folder, to_drop)
                        if os.path.isdir(entity_to_drop):       # rm directory
                            self.compare_file.w_rm_dir(entity_to_drop)
                        elif os.path.isfile(entity_to_drop):    # rm file
                            self.compare_file.w_rm_file(entity_to_drop)
            self.compare_file.w_end_info()
        self.set_state(FtState.ANALYSIS_DONE)
        logging.info("[%-15s]: file %s creato", "FileTransfer", self.compare_file.path)

    def transfer(self):
        """"Il metodo self.cmp_manager.read_compare_file restituisce un dizionario, entity, con i seguenti attributi:
        - action: l'azione da effettuare crea/rimuovi file/cartella
        - path_src: il percorso d'origine
        - path_dst: opzionale, il percorso di destinazione"""
        self.check_state(FtState.ANALYSIS_DONE)
        for entity in self.cmp_manager.read_compare_file():
            try:
                if entity["action"] == "COPY":             # copio il file in DST
                    shutil.copy2(entity["source_path"], entity["destination_path"])     # uso shutil.copy2() così mantengo i metadati
                    logging.debug("[%-15s]: copio il file %s in %s", "FileTransfer", entity["source_path"], entity["destination_path"])
                elif entity["action"] == "RIMUOVI FILE":                        # rimuovo il file da DST
                    try:
                        os.remove(entity["destination_path"])
                    except PermissionError:  # il file è in read-only, lo modifico
                        os.chmod(entity["destination_path"], stat.S_IWUSR)
                        os.remove(entity["destination_path"])
                    logging.debug("[%-15s]: elimino il file %s", "FileTransfer", entity["destination_path"])
                elif entity["action"] == "CREA CARTELLA":                           # creo la cartella in DST
                    dst_folder = os.path.join(entity["destination_path"], os.path.basename(entity["source_path"]))
                    if os.path.exists(dst_folder):  # se la cartella da creare esiste già (e poichè il FS di Win è case insensitive) devo prima rimuoverla e poi crearla (vedi Tools.path_exists())
                        logging.debug("[%-15s]: rimuovo la cartella con tutto il suo contenuto %s", "FileTransfer", Tools.get_exact_folder(dst_folder))
                        shutil.rmtree(dst_folder)
                    Tools.create_dir_and_children(entity["source_path"], entity["destination_path"])
                    logging.debug("[%-15s]: creo la cartella %s", "FileTransfer", os.path.join(entity["destination_path"], os.path.basename(entity["source_path"])))
                elif entity["action"] == "RIMUOVI CARTELLA":                            # elimino la cartella in DST
                    if Tools.path_exists(entity["destination_path"]):      # perchè posso averla già eliminata nel caso di 'CREA CARTELLA'
                        shutil.rmtree(entity["destination_path"], onerror=Tools.remove_readonly)
                        logging.debug("[%-15s]: rimuovo la cartella con tutto il suo contenuto %s", "FileTransfer", entity["destination_path"])
                else:
                    self.cmp_manager.err_transfer_count += 1
                    logging.error("[%-15s]: azione da eseguire non valida: %s", "FileTransfer", entity["action"])
                    continue
            except OSError as os_error:
                self.cmp_manager.err_transfer_count += 1
                driver_removed = Tools.find_removed_drive([self.base_folder_src, self.base_folder_dst])
                if driver_removed:  # se è stata rimossa la periferica esterna, inserisco le info finali e interrompo l'analisi
                    err_text = "Trasferimento interrotto, periferica {} rimossa".format(driver_removed)
                    self.cmp_manager.write_info_close_compare(moment="transfer", err_text=err_text)
                    logging.error("[%-15s]: %s", "FileTransfer", err_text)
                    raise TransferingFilesError(error_text=err_text)
                elif os_error.errno == 28:  # esaurimento dello spazio sul disco di destinazione
                    err_text = "Spazio su disco {} esaurito!".format(entity["destination_path"][:2])
                    self.cmp_manager.write_info_close_compare(moment="transfer", err_text=err_text)
                    logging.error("[%-15s]: %s", "FileTransfer", err_text)
                    raise TransferingFilesError(error_text=err_text)
                else:  # in caso contrario segno solo l'errore e proseguo
                    err_text = "Errore generico, dettagli: " + str(os_error)
                    logging.error("[%-15s]: %s", "FileTransfer", err_text)
                    continue
        # self.reset_flags()  # ho terminato l'analisi, resetto a zero i flag
        logging.info("[%-15s]: trasferimento terminato, errori verificatisi: %s", "FileTransfer", str(self.cmp_manager.err_transfer_count))
        # se la conta degli errori durante il trasferimento è <> 0 inserisco questa informazione nel popup
        return False if self.cmp_manager.err_transfer_count == 0 else True

    def close(self):
        """concludo il log"""
        logging.info("[%-15s]: chiusura istanza di FileTransfer", "FileTransfer")
        logging.info("[%-15s]: %s", "FileTransfer", "*" * 80)


class CompareFileParser:
    """Si occupa di fare da intermediario tra la scrittura/lettura del file compare.txt, tramite un'istanza di
    CompareFile(), e le operazioni sul filesysyem:
        CompareFileParser.write <---> Filetransfer.compare      scrive compare le info provenienti da compare
        CompareFileParser.read <---> Filetransfer.transfer      legge file compare e restituisce a trasnfer ogni azione da eseguire"""
    def __init__(self):
        self.compare_file = None

    def read_compare_file(self):
        """Apre il file compare creato con il metodo write_compare_file() e legge ogni blocco, delimitato dalla sequenza
         self._new_line_seq_chars, corrispondente ad un'entità che contiene le varie informazioni (azione, percocrsi, ...)
         """
        self.compare_file.open(mode="r+", encoding="utf-8")

        with self.compare_file as compare_file_r:
            line = compare_file_r.readline()

            while line:
                start_time = time.time()
                if line.startswith(self._end_compare_seq_chars):    # termine delle file compare, esco dal flusso
                    break

                elif line.startswith(self._new_line_seq_chars):  # se è una nuova entità
                    line_to_parse = ""
                    while True:
                        line = compare_file_r.readline()
                        if line.startswith(self._new_line_seq_chars) or line.startswith(self._end_compare_seq_chars):
                            break  # delimitatore che indica la fine dell'entità o del file compare
                        else:
                            line_to_parse += line

                    yield self.get_entity_from_string(line_to_parse)    # formatto la stringa per ricavare il dizionario e lo restituisco

                else:
                    line = compare_file_r.readline()

                end_time = time.time()
                self.time_transfer += end_time - start_time  # non faccio una somma totale perchè in caso di errore avrei tempo tot = 0

            compare_file_r.write("\n\n{}\n".format(self.create_last_info_transfer()))  # inserisco le info conclusive (progressivi, tempi, errori)

    def create_last_info_transfer(self):
        """In fase di trasferimento, crea una stringa terminale contenente le info di riepilogo del trasferimento"""
        return "Tempo di esecuzione trasferimento: {}\nErrori durante il trasferimento: {}".format(Tools.format_sec_min_hour(self.time_transfer), self.err_transfer_count)

    def get_entity_from_string(self, string_to_parse):
        """Riceve una stringa che rappresenta un'entità, la scompone creando un dizionario contenete tutte le varie
        informazioni di questa, e lo restituisce"""
        entity_dict = {}
        for line in string_to_parse.strip().split("\n"):
            separator_index = line.index(self._sepatator_seq_chars)
            key = line[: separator_index].strip()
            value = line[separator_index + 4:].strip()
            entity_dict[key] = value

        return entity_dict


class CompareFile:
    """Classe wrapper che rappresenta il file compare, è utilizzabile nel context manager"""
    def __init__(self, compare_file_path):
        self.file_object = None
        self.cpfile_prog = 0       # progressivi delle varie azioni da eseguire
        self.rmfile_prog = 0
        self.cpdir_prog = 0
        self.rmdir_prog = 0
        self.err_transfer_count = 0
        self.total_size_to_move = 0
        self.total_size_to_delete = 0
        self._new_line_seq_chars = "---"        # sequenza di caratteri che indica la nuova linea/termine della sequenza di azioni da eseguire
        self._end_compare_seq_chars = "***"
        self._sepatator_seq_chars = "--->"
        current_date = datetime.now().strftime("%Y%m%d")
        compare_file_name = f"{current_date}_compare.txt"
        count = 1
        while True:
            test_path = os.path.normpath(os.path.join(os.getcwd(), compare_file_path, compare_file_name))
            try:
                self.file_object = open(test_path, mode="x", encoding="utf-8")
            except FileExistsError:
                compare_file_name = f"{current_date}_compare_{count}.txt"
                count += 1
            else:
                self.path = test_path
                break

    def __enter__(self):
        """Mi permette di utilizzare CompareFile() con il context manager"""
        return self.file_object

    def __exit__(self, type, value, traceback):
        """Mi permette di utilizzare CompareFile() con il context manager"""
        self.file_object.close()
        self.file_object = None

    def open(self, **kw):
        """wrappa il metodo open(), premette di evitare di inserire il percorso e nome del file compare.txt"""
        if self.file_object is not None:
            self.file_object.close()
        try:
            self.file_object = open(self.path, **kw)
        except FileNotFoundError:
            logging.error("[%-15s]: file compare %s non trovato o rimosso", "FileTransfer", self.path)
            raise TransferingFilesError(error_text=f"File compare {self.path} non trovato o rimosso")

    def w_cp_file(self, src, dst):
        self.cpfile_prog += 1
        size = os.path.getsize(src)
        self.total_size_to_move += size
        # NB: protect when write fails
        self.file_object.write(f"COPY FILE\n")
        self.file_object.write(f"{'file':<16} {self._sepatator_seq_chars} {os.path.basename(src)}\n")
        self.file_object.write(f"{'size':<16} {self._sepatator_seq_chars} {Tools.format_byte_size(size)}\n")
        self.file_object.write(f"{'source':<16} {self._sepatator_seq_chars} {os.path.dirname(src)}\n")
        self.file_object.write(f"{'destination':<16} {self._sepatator_seq_chars} {dst}\n\n")

    def w_rm_file(self, src):
        self.rmfile_prog += 1
        size = os.path.getsize(src)
        self.total_size_to_delete += size
        # NB: protect when write fails
        self.file_object.write(f"REMOVE FILE\n")
        self.file_object.write(f"{'file':<16} {self._sepatator_seq_chars} {os.path.basename(src)}\n")
        self.file_object.write(f"{'size':<16} {self._sepatator_seq_chars} {Tools.format_byte_size(size)}\n")
        self.file_object.write(f"{'source':<16} {self._sepatator_seq_chars} {os.path.dirname(src)}\n\n")

    def w_cp_dir(self, src, dst):
        self.cpdir_prog += 1
        # NB: protect when write fails
        self.file_object.write(f"COPY DIRECTORY\n")
        self.file_object.write(f"{'directory':<16} {self._sepatator_seq_chars} {os.path.basename(src)}\n")
        self.file_object.write(f"{'source':<16} {self._sepatator_seq_chars} {os.path.dirname(src)}\n")
        self.file_object.write(f"{'destination':<16} {self._sepatator_seq_chars} {os.path.dirname(dst)}\n\n")

    def w_rm_dir(self, dst):
        self.rmdir_prog += 1
        # NB: protect when write fails
        self.file_object.write(f"REMOVE DIRECTORY (R)\n")
        self.file_object.write(f"{'directory':<16} {self._sepatator_seq_chars} {os.path.basename(dst)}\n")
        self.file_object.write(f"{'source':<16} {self._sepatator_seq_chars} {os.path.dirname(dst)}\n\n")

    def w_end_info(self):
        # NB: protect when write fails
        self.file_object.write(f"{self._end_compare_seq_chars}\n\nFile da copiare: {self.cpfile_prog}, size: {Tools.format_byte_size(self.total_size_to_move)}\n")
        self.file_object.write(f"File da eliminare: {self.rmfile_prog}\n")
        self.file_object.write(f"Cartelle da creare: {self.cpdir_prog}\n")
        self.file_object.write(f"Cartelle da eliminare: {self.rmdir_prog}\n")
        self.file_object.write(f"Totale azioni: {self.cpfile_prog + self.rmfile_prog + self.cpdir_prog + self.rmdir_prog}\n\n")
