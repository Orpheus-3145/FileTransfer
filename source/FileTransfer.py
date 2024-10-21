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
    ERROR = 4


class CompareFileState(Enum):
    CREATED = 0
    WRITING_DONE = 1
    READING_DONE = 2
    ERROR = 3


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
            raise

    def set_src_and_dst(self, folder_src, folder_dst):
        self.check_state(FtState.START)
        for path_to_check in [folder_src, folder_dst]:
            if not path_to_check:
                raise SelectingFoldersError("Inserito un path vuoto")
            elif not Tools.path_exists(folder_src):
                raise SelectingFoldersError(f"{path_to_check} non esiste")
            elif os.path.isfile(path_to_check):
                raise SelectingFoldersError(f"{path_to_check} non è una directory")
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
        self.check_state(FtState.FOLDERS_SET)
        self.compare_file = CompareFile(COMPARE_FILE_PATH)
        with self.compare_file.open("w") as comp_file:
            for directory, list_dir, list_file in os.walk(self.base_folder_src):
                current_src_folder = directory
                current_dst_folder = directory.replace(self.base_folder_src, self.base_folder_dst)
                if not Tools.path_exists(current_dst_folder):  # create missing directory
                    comp_file.write_new_entry("MK_DIR", current_src_folder, current_dst_folder)
                    for file in list_file:          # and every file it contains
                        src_file = os.path.join(current_src_folder, file)
                        if not os.path.islink(src_file):
                            comp_file.write_new_entry("CP_FILE", src_file, current_dst_folder)
                else:       # if directory exists check its content
                    for file in list_file:
                        src_file = os.path.join(current_src_folder, file)
                        if os.path.islink(src_file):
                            continue
                        dst_file = os.path.join(current_dst_folder, file)
                        # copy every missing or less updated file
                        if not Tools.path_exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                            comp_file.write_new_entry("CP_FILE", src_file, current_dst_folder)
                    # clean stuff in dst but missing in src
                    entities_to_rm = set(os.listdir(current_dst_folder)) - set(list_file) - set(list_dir)
                    for to_drop in entities_to_rm:
                        entity_to_drop = os.path.join(current_dst_folder, to_drop)
                        if os.path.isdir(entity_to_drop):       # rm directory
                            comp_file.write_new_entry("RM_DIR", entity_to_drop)
                        elif os.path.isfile(entity_to_drop):    # rm file
                            comp_file.write_new_entry("RM_FILE", entity_to_drop)
        logging.info("[%-15s]: file %s creato", "FileTransfer", self.compare_file.path)
        self.set_state(FtState.ANALYSIS_DONE)

    def read_compare_file(self):
        self.check_state(FtState.ANALYSIS_DONE)
        errors = ""
        count_errs = 0
        with self.compare_file.open("r") as comp_file:
            entity = comp_file.read_entity()
            while entity is not None:
                try:
                    action = entity["action"]
                    if action == "CP_FILE":             # copio il file in DST
                        shutil.copy2(entity["source_path"], entity["destination_path"])     # uso shutil.copy2() così mantengo i metadati
                        logging.debug("[%-15s]: copio il file %s in %s", "FileTransfer", entity["source_path"], entity["destination_path"])
                    elif action == "RM_FILE":                        # rimuovo il file da DST
                        os.remove(entity["destination_path"])
                        logging.debug("[%-15s]: elimino il file %s", "FileTransfer", entity["destination_path"])
                    elif action == "MK_DIR":                           # creo la cartella in DST
                        os.mkdir(entity["destination_path"])
                        logging.debug("[%-15s]: creo la cartella %s", "FileTransfer", os.path.join(entity["destination_path"], os.path.basename(entity["source_path"])))
                    elif action == "RM_DIR":                            # elimino la cartella in DST
                        shutil.rmtree(entity["destination_path"], onerror=Tools.remove_readonly)
                        logging.debug("[%-15s]: rimuovo la cartella con tutto il suo contenuto %s", "FileTransfer", entity["destination_path"])
                except OSError as os_error:
                    driver_removed = Tools.find_removed_drive([self.base_folder_src, self.base_folder_dst])
                    if driver_removed:  # se è stata rimossa la periferica esterna, inserisco le info finali e interrompo l'analisi
                        err_text = "Trasferimento interrotto, periferica {} rimossa".format(driver_removed)
                        logging.error("[%-15s]: %s", "FileTransfer", err_text)
                        raise TransferingFilesError(error_text=err_text)
                    elif os_error.errno == 28:  # esaurimento dello spazio sul disco di destinazione
                        err_text = "Spazio su disco {} esaurito".format(entity["destination_path"][:2])
                        logging.error("[%-15s]: %s", "FileTransfer", err_text)
                        raise TransferingFilesError(error_text=err_text)
                    else:  # in caso contrario segno solo l'errore e proseguo
                        errors += f"operation: {action} failed, errno: {os_error.errno}, trace: {os_error.strerror}\n"
                        count_errs += 1
                        logging.debug("[%-15s]: errore non fatale: %s", "FileTransfer", os_error.strerror)
                        continue
        if count_errs:
            logging.info("[%-15s]: trasferimento terminato, %s errori", "FileTransfer", count_errs)
        else:
            logging.info("[%-15s]: trasferimento terminato con successo")
        self.set_state(FtState.TRANSFER_DONE)
        return count_errs == 0

    def close(self):
        """concludo il log"""
        logging.info("[%-15s]: chiusura istanza di FileTransfer", "FileTransfer")
        logging.info("[%-15s]: %s", "FileTransfer", "*" * 80)


class CompareFile:
    """Classe wrapper che rappresenta il file compare, è utilizzabile nel context manager"""
    def __init__(self, base_path):
        self.compare_file_path = None
        self.file_object = None
        self.set_compare_file_name(base_path)
        self.analysis_done = False

        self.total_size_to_move = 0
        self.total_size_to_remove = 0

        self._entry_separator = "---"        # sequenza di caratteri che indica la nuova linea/termine della sequenza di azioni da eseguire
        self._end_compare_seq = "***"
        self._sepatator_seq_chars = "--->"
        self._actions = {"CP_FILE": 0, "MK_DIR": 0, "RM_FILE": 0, "RM_DIR": 0}

    def set_compare_file_name(self, base_path):
        compare_file_name = f"{datetime.now().strftime('%Y%m%d')}_compare.txt"
        count = 1
        while True:
            test_path = os.path.normpath(os.path.join(os.getcwd(), base_path, compare_file_name))
            if Tools.path_exists(test_path):
                compare_file_name = f"{datetime.now().strftime('%Y%m%d')}_compare_{count}.txt"
                count += 1
            else:
                self.compare_file_path = test_path
                break

    def __enter__(self):
        """Mi permette di utilizzare CompareFile() con il context manager"""
        if self.file_object is None:
            raise CompareFileError("Compare file is closed")
        return self.file_object

    def __exit__(self, exception, value, traceback):
        """Mi permette di utilizzare CompareFile() con il context manager"""
        if exception is None and self.analysis_done is False:
            self.file_object.write(f"{self._end_compare_seq}\n\nFile da copiare: {self._actions['CP_FILE']}, size: {Tools.format_byte_size(self.total_size_to_move)}\n")
            self.file_object.write(f"File da eliminare: {self._actions['RM_FILE']}, size: {Tools.format_byte_size(self.total_size_to_remove)}\n")
            self.file_object.write(f"Cartelle da creare: {self._actions['MK_DIR']}\n")
            self.file_object.write(f"Cartelle da eliminare: {self._actions['RM_DIR']}\n")
            self.analysis_done = True
        self.close()

    def open(self, **kw):
        if self.file_object is not None:
            self.file_object.close()
        self.file_object = open(self.compare_file_path, **kw)

    def close(self):
        self.file_object.close()
        self.file_object = None

    def read_entry(self):
        try:
            if self.analysis_done is False:
                raise CompareFileError("Analysis not performed")
            line = self.file_object.readline()
            if line.startswith(self._end_compare_seq):      # end
                yield None
            elif not line.startswith(self._entry_separator):
                raise CompareFileError(f"bad format, entry should start with '{self._entry_separator}' sequence")
            entry = {}
            while True:
                line = self.file_object.readline()
                if not line:    # not good
                    raise CompareFileError("EOF reached unexpectedly")
                elif line.startswith(self._entry_separator):
                    break
                key, value = line.split(self._sepatator_seq_chars)
                entry[key.strip()] = value.strip()
            yield entry
        except AttributeError:  # file_object is None
            raise CompareFileError("File closed")
        except ValueError:
            raise CompareFileError(f"bad format: missing '{self._sepatator_seq_chars}' in line")

    def write_new_entry(self, action, src, dst=""):
        if self.analysis_done is True:
            raise CompareFileError("Analysis already performed")
        elif action not in self._actions.keys():
            raise CompareFileError(f"action: '{action}' not mapped")
        self._actions[action] += 1      # increasing counter action
        size = Tools.get_size(src)
        if action == "CP_FILE":
            self.total_size_to_move += size
        elif action.startswith("RM_"):
            self.total_size_to_remove += size
        self.file_object.write(f"{self._entry_separator}\n")
        self.file_object.write(f"{'action':<16} {self._sepatator_seq_chars} {action}\n")
        self.file_object.write(f"{'name':<16} {self._sepatator_seq_chars} {os.path.basename(src)}\n")
        self.file_object.write(f"{'size':<16} {self._sepatator_seq_chars} {Tools.format_byte_size(size)}\n")
        self.file_object.write(f"{'source':<16} {self._sepatator_seq_chars} {os.path.dirname(src)}\n")
        if dst:
            self.file_object.write(f"{'destination':<16} {self._sepatator_seq_chars} {dst}\n")
        self.file_object.write(f"{self._entry_separator}")
