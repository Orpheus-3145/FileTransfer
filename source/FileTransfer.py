import Tools
import stat
import os
import shutil
import logging
import time
from datetime import datetime
import configparser
import inspect
from Exceptions import *

# Config = configparser.ConfigParser()
# Config.read("D:\\MyPython\\FileTransfer\\dist\\FileTransfer\\_internal\\settings\\config_filetransfer.ini")


class FileTransfer:
    """Questa classe si occupa di:
        1) confrontare due percorsi SRC e DST creando i loro relativi alberi di directory
        2) analizzare i due alberi creati trovando le differenze tra essi (file/cartelle da copiare/rimuovere) inserendo
            tali diversità in un file testuale (compare.txt)
        3) leggere un file compare ed eseguire tutte le azioni sul FS ivi elencate, allineando DST a SRC"""

    def __init__(self):
        self.base_folder_src = ""                                           # percorso file cartella più aggiornata
        self.base_folder_dst = ""                                           # percorso file cartella da aggiornare
        self.common_folder = ""                                             # nome della cartella, comune a SRC e DST
        self.src_dir_list = []                                              # lista di cartelle da analizzare in SRC
        self.dst_dir_list = []                                              # lista di cartelle da analizzare in DST
        self._ready_for_select = False                                      # variabile che indica se l'istanza di FileTransfer ha SRC e DST selezionati correttamente (vedi check_folders())
        self._ready_for_analysis = False                                    # variabile che indica se l'istanza di FileTransfer è pronta all'analisi
        self._ready_for_transfer = False                                    # variabile che indica se l'istanza di FileTransfer è pronta al trasferimento
        self.cmp_manager = CompareFileParser()                              # istanza del parser del file compare.txt

        logging.info("[%-15s]: %s", "FileTransfer", "*" * 80)
        logging.info("[%-15s]: creata un'istanza di FileTransfer", "FileTransfer")

    def check_folders(self, folder_src, folder_dst):
        """Verifica i due percorsi file passati in argomento, folder_src e folder_dst, se rispettano determinati
        le indicazioni allor possono essere salvati e si può procedere all'analisi valorizzando _ready_for_select a True"""
        self.reset_flags()  # inizio da zero il processo, resetto tutto a False
        if not (folder_src != "" and folder_dst != ""):     # devono essere entrambi <> ""
            raise SelectingFoldersError("Non hai inserito {}".format("l'origine e la destinazione" if folder_src == "" and folder_dst == "" else "uno dei due elementi!"))
        elif os.path.isfile(folder_src) or os.path.isfile(folder_dst):      # devono essere delle cartelle
            raise SelectingFoldersError("Selezione non valida")
        elif folder_src == folder_dst:                                      # devono essere diversi
            raise SelectingFoldersError("I due percorsi sono uguali")
        elif os.path.basename(folder_src) != os.path.basename(folder_dst):  # devono condividere il nome della cartella alla fine del percorso
            raise SelectingFoldersError("I due punti di partenza non hanno lo stesso nome")
        elif len(os.listdir(folder_src)) == 0:                              # la cartella di origine non può essere vuota
            raise SelectingFoldersError("La cartella {} è vuota".format(folder_src))
        else:
            self.common_folder = os.path.basename(folder_src)
            self.base_folder_src = os.path.dirname(folder_src)
            self.base_folder_dst = os.path.dirname(folder_dst)
            self._ready_for_select = True
        logging.info("[%-15s]: SRC e DST selezionati correttamente", "FileTransfer")

    def set_folders(self):
        """Crea due alberi di directory (uno per SRC e l'altro per DST) che partono da self.common_folder (e il loro
        percorso inizia da questa cartella) i quali poi verrano confrontati tramite self.create_entities(); se non si
        verificano errori setto _ready_for_analysis a True"""
        if self._ready_for_select is False:
            raise SelectingFoldersError(error_text="Non sono stati verificati correttamente l'origine e/o la destinazione")

        folder_src = os.path.join(self.base_folder_src, self.common_folder)
        folder_dst = os.path.join(self.base_folder_dst, self.common_folder)

        try:
            self.src_dir_list = Tools.get_all_dirs_from_path(folder_src, mode="base_directory")     # creo albero SRC
            self.dst_dir_list = Tools.get_all_dirs_from_path(folder_dst, mode="base_directory")     # creo albero DST

        except OSError as os_error:     # errore sul FS scrivo su log e propago
            driver_removed = Tools.find_removed_drive([folder_src, folder_dst])     # trovo, se esiste, il driver rimosso

            if driver_removed or os_error.winerror == 433:  # NB ci sono varie eccezioni che si verificano quando si rimuove un driver
                err_text = "Periferica {} rimossa".format(driver_removed if driver_removed else os_error.filename[:2])

            else:               # in caso contrario è un errore generico
                err_text = "Errore generico, dettagli: " + str(os_error)

            logging.error("[%-15s]: %s", "FileTransfer", err_text)
            raise SelectingFoldersError(error_text=err_text)

        else:
            logging.info("[%-15s]: SRC e DST espansi correttamente", "FileTransfer")
            logging.info("[%-15s]: SRC: %s", "FileTransfer", folder_src)
            logging.info("[%-15s]: DST: %s", "FileTransfer", folder_dst)
            self._ready_for_analysis = True

    def create_entities(self):
        """Cicla ogni cartella presente della lista SRC: se esiste anche in DST verifica che abbiano gli stessi file
        (confronto tramite la dimensione in byte) e copia/rimuove quelli mancanti/di troppo; se invece la cartella non è
         presente nella lista di DST la crea, ricorsivamente con tutto il suo contenuto di file e sottocartelle. Alla
         fine del ciclo, le rimaneneti cartelle nella lista DST verranno rimosse, in quanto non presenti in SRC.
        NB: solleva OSError --> FileNotExistsingError, PermissionError """
        index_src = 0   # indice della lista SRC
        index_dst = 0   # indice della lista DST

        # uso il loop while perchè mi permette di modificare gli elementi delle liste ce si stanno ciclando
        try:
            while index_src in range(len(self.src_dir_list)):  # per ogni cartella in SRC
                src_dir = self.src_dir_list[index_src]
                current_src_folder = os.path.join(self.base_folder_src, src_dir)    # mi serve il percorso completo per operare sul FS
                current_dst_folder = os.path.join(self.base_folder_dst, src_dir)

                if src_dir in self.dst_dir_list:  # se la cartella esiste anche in DST
                    src_file_list = Tools.create_entity_list(current_src_folder, type_entity="file")    # creo la lista dei file della cartella in SRC e DST
                    dst_file_list = Tools.create_entity_list(current_dst_folder, type_entity="file")

                    for file_name in src_file_list:  # verifico che entrambi abbiano gli stessi file
                        current_src_file = os.path.join(current_src_folder, file_name)

                        if file_name in dst_file_list:  # se il file esiste anche nella in DST ma ha dimensione diversa lo sovrascrivo
                            current_dst_file = os.path.join(current_dst_folder, file_name)
                            size_src_file = os.path.getsize(current_src_file)
                            size_dst_file = os.path.getsize(current_dst_file)
                            if size_src_file != size_dst_file:
                                yield {"action": "COPIA FILE",
                                       "entity": file_name,
                                       "size": os.path.getsize(current_src_file),
                                       "source_path": current_src_file,
                                       "destination_path": current_dst_folder}  # sovrascrivi file

                            dst_file_list.remove(file_name)     # rimuovo dalla lista il file

                        else:  # se non esiste in DST ==> lo copio lì
                            yield {"action": "COPIA FILE",
                                   "entity": file_name,
                                   "size": os.path.getsize(current_src_file),
                                   "source_path": current_src_file,
                                   "destination_path": current_dst_folder}  # copia file

                    if len(dst_file_list) > 0:  # nel caso di file rimanenti in DST (che non sono in SRC) li elimino
                        for file_to_delete in dst_file_list:
                            current_dst_file = os.path.join(current_dst_folder, file_to_delete)
                            yield {"action": "RIMUOVI FILE",
                                   "entity": file_to_delete,
                                   "size": os.path.getsize(current_dst_file),
                                   "destination_path": current_dst_file}  # rimuovi file

                    self.dst_dir_list.remove(src_dir)   # rimuovo la cartella comune dalla lista di DST
                    index_src += 1

                else:  # se la cartella non esiste in DST devo crearla con tutto il suo contenuto
                    # l'albero di directory è creato a espansione, le cartelle sono ordinate in modo che la precedente
                    # contiene la successiva; poiché la cartella viene creata in modo ricorsivo, creo la cartella madre e in
                    # modo ricorsivo tutto il suo contenuto, ignoro tutte le successive e vado a un nuovo gruppo
                    n_directories = 0
                    n_files = 0
                    total_size = 0
                    while index_src in range(len(self.src_dir_list)) and self.src_dir_list[index_src].startswith(src_dir):  # se non è l'ultimo e il path originale è contenuto nel successivo skippo
                        current_folder = os.path.join(self.base_folder_src, self.src_dir_list[index_src])
                        file_list = Tools.create_entity_list(current_folder, "file")
                        n_directories += 1
                        n_files += len(file_list)

                        for file in file_list:
                            total_size += os.path.getsize(os.path.join(current_folder, file))

                        index_src += 1

                    yield {"action": "CREA CARTELLA",  # crea (ricorsivamente) cartella
                           "entity": os.path.basename(current_dst_folder),
                           "size": total_size,
                           "source_path": current_src_folder,
                           "destination_path": os.path.dirname(current_dst_folder),
                           "tmp_n_directories": n_directories,              # mi serve temporaneamente, poi lo elimino,
                           "tmp_n_files": n_files}                          # mi serve temporaneamente, poi lo elimino,

            while index_dst in range(len(self.dst_dir_list)):  # nel caso di folder rimanenti (quindi non in SRC) in DST li elimino
                dst_dir = self.dst_dir_list[index_dst]
                path_dst_to_remove = os.path.join(self.base_folder_dst, dst_dir)
                n_directories = 0
                n_files = 0
                total_size = 0
                # vedi CREA CARTELLA, stessa logica ma la conta avviene sui file e directory da rimuovere
                while index_dst in range(len(self.dst_dir_list)) and self.dst_dir_list[index_dst].startswith(dst_dir):  # se non è l'ultimo e il path originale è contenuto nel successivo skippo
                    current_folder = os.path.join(self.base_folder_dst, self.dst_dir_list[index_dst])
                    file_list = Tools.create_entity_list(current_folder, "file")
                    n_directories += 1
                    n_files += len(file_list)

                    for file in file_list:
                        total_size += os.path.getsize(os.path.join(current_folder, file))

                    index_dst += 1

                yield {"action": "RIMUOVI CARTELLA",         # rimuovi cartella
                       "entity": os.path.basename(path_dst_to_remove),
                       "size": total_size,
                       "destination_path": path_dst_to_remove,
                       "tmp_n_directories": n_directories,      # mi serve temporaneamente, poi lo elimino,
                       "tmp_n_files": n_files}                  # mi serve temporaneamente, poi lo elimino,

        except OSError as os_error:
            driver_removed = Tools.find_removed_drive([self.base_folder_src, self.base_folder_dst])

            if driver_removed:  # se è stata rimossa la periferica esterna, inserisco le info finali e interrompo l'analisi
                err_text = "Analisi interrotta, periferica {} rimossa".format(driver_removed)

            else:  # in caso contrario segno solo l'errore e proseguo
                err_text = "Errore generico, dettagli: " + str(os_error)

            self.cmp_manager.write_info_close_compare(moment="compare", err_text=err_text)      # scrivo l'anomalia verificatasi prima di chiudere il file compare
            raise ComparingFoldersError(error_text=err_text)

    def compare(self):
        """Crea il file compare.txt, tramite il parser self.cmp_manager, in cui vengono inserite tutte le operazioni sul
         FS da eseguire per allineare DST a SRC"""
        if self._ready_for_analysis is not True:
            raise ComparingFoldersError(error_text="Errore imprevisto, applicazione non pronta all'analisi")

        try:
            # scrivo il file compare più a basso livello, qui gestisco solo le eccezioni che si possono verificare,
            # il metodo generatore self.create_iter permette di ciclare tutte le azioni da inserire
            self.cmp_manager.write_compare_file(self.create_entities)

        except ComparingFoldersError as comparing_error:    # scrivo su log e propago
            logging.error("[%-15s]: %s", "FileTransfer", comparing_error.error_text)
            raise

        else:
            logging.info("[%-15s]: analisi terminata", "FileTransfer")
            self._ready_for_transfer = True  # analisi terminata, pronto per il trasferimento

    def transfer(self):
        """"Il metodo self.cmp_manager.read_compare_file restituisce un dizionario, entity, con i seguenti attributi:
        - action: l'azione da effettuare crea/rimuovi file/cartella
        - path_src: il percorso d'origine
        - path_dst: opzionale, il percorso di destinazione"""

        if self._ready_for_transfer is not True:
            raise TransferingFilesError(error_text="Errore imprevisto: l'applicazione non è pronta al trasferimento")

        elif not os.path.exists(os.path.join(self.cmp_manager.compare_file.compare_file_path, self.cmp_manager.compare_file.compare_file_name)):
            logging.error("[%-15s]: file compare %s non trovato o rimosso", "FileTransfer", self.cmp_manager.compare_file.compare_file_name)
            raise TransferingFilesError(error_text="File compare {} non trovato o rimosso".format(self.cmp_manager.compare_file.compare_file_name))

        for entity in self.cmp_manager.read_compare_file():
            try:
                if entity["action"] == "COPIA FILE":             # copio il file in DST
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

                    if os.path.exists(dst_folder):  # se la cartella da creare esiste già (e poichè il FS di Win è case insensitive) devo prima rimuoverla e poi crearla (vedi Tools.check_if_path_exists())
                        logging.debug("[%-15s]: rimuovo la cartella con tutto il suo contenuto %s", "FileTransfer", Tools.get_exact_folder(dst_folder))
                        shutil.rmtree(dst_folder)

                    Tools.create_dir_and_children(entity["source_path"], entity["destination_path"])
                    logging.debug("[%-15s]: creo la cartella %s", "FileTransfer", os.path.join(entity["destination_path"], os.path.basename(entity["source_path"])))

                elif entity["action"] == "RIMUOVI CARTELLA":                            # elimino la cartella in DST
                    if Tools.check_if_path_exists(entity["destination_path"]):      # perchè posso averla già eliminata nel caso di 'CREA CARTELLA'
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

        self.reset_flags()  # ho terminato l'analisi, resetto a zero i flag
        logging.info("[%-15s]: trasferimento terminato, errori verificatisi: %s", "FileTransfer", str(self.cmp_manager.err_transfer_count))

        # se la conta degli errori durante il trasferimento è <> 0 inserisco questa informazione nel popup
        return False if self.cmp_manager.err_transfer_count == 0 else True

    def reset_flags(self):
        self._ready_for_select = False
        self._ready_for_analysis = False
        self._ready_for_transfer = False

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
        self.copy_prog = 0  # progressivi delle varie azioni da eseguire
        self.rmfile_prog = 0
        self.mkdir_prog = 0
        self.rmdir_prog = 0
        self.err_transfer_count = 0
        self.total_size_to_move = 0  # dimensione totale dei file da copiare/rimuovere
        self.total_size_to_delete = 0
        self.time_analysis = 0      # tempo di esecuzione analisi/trasferimento
        self.time_transfer = 0
        self._new_line_seq_chars = "---"        # sequenza di caratteri che indica la nuova linea/termine della sequenza di azioni da eseguire
        self._end_compare_seq_chars = "***"
        self._sepatator_seq_chars = "--->"

    def write_compare_file(self, line_generator):
        """line_generator è una funzione generatrice che restituisce un dizionario, contente le varie informazioni della
        relativa azione, il quale verrà formattato, tramite il metodo format_new_line() in una nuova linea da inserire
        nel file compare.txt"""
        if not inspect.isgeneratorfunction(line_generator):  # verifico di iterare un oggetto di tipo generatore
            raise ParserError("Errore, passato un oggetto sbagliato per il popolatomento del file compare.txt")

        self.reset_all_counters()               # prima di scrivere un nuovo file resetto a zero tutti i contatori
        self.compare_file = CompareFile()       # creo un nuovo file

        with self.compare_file as compare_file_w:
            start_time = time.time()
            for entity in line_generator():  # aumento prima i vari progressivi e scrivo successivamente la riga nel file compare.txt
                if entity["action"] == "COPIA FILE":
                    self.copy_prog += 1
                    self.total_size_to_move += entity["size"]

                elif entity["action"] == "RIMUOVI FILE":
                    self.rmfile_prog += 1
                    self.total_size_to_delete += entity["size"]

                elif entity["action"] == "CREA CARTELLA":
                    self.mkdir_prog += entity["tmp_n_directories"]
                    self.copy_prog += entity["tmp_n_files"]
                    self.total_size_to_move += entity["size"]

                elif entity["action"] == "RIMUOVI CARTELLA":
                    self.rmdir_prog += entity["tmp_n_directories"]
                    self.rmfile_prog += entity["tmp_n_files"]
                    self.total_size_to_delete += entity["size"]

                for key in [k for k in entity.keys() if k.startswith("tmp_")]:  # rimuovo gli elementi temporanei del dizionario, se ve ne sono
                    del entity[key]

                entity["size"] = Tools.format_byte_size(entity["size"])
                compare_file_w.write(self.format_new_line(**entity))    # scrivo una nuova riga
                end_time = time.time()
                self.time_analysis = end_time - start_time              # non faccio una somma progressiva perchè deve prendere il tempo totale (tutto ciò che viene fatto in line_generator())

            compare_file_w.write("\n{}\n".format(self.create_last_info_compare()))    # inserisco le info conclusive (progressivi, tempi, errori)

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

    def format_new_line(self, **kw):
        """Riceve un dizionario, kw, e lo scrive nel file compare nella formata 'chiave [separatore] valore (new line)'"""
        new_line = "{}\n".format(self._new_line_seq_chars)
        for key, value in kw.items():
            new_line += "{:16} {} {}\n".format(key, self._sepatator_seq_chars, value)

        return new_line

    def create_last_info_compare(self):
        """In fase di analisi, crea una stringa terminale contenente le info di riepilogo dell'analisi: progressivi,
        errori, tempo, ..."""
        return "{}\n\nFile da copiare: {}\n" \
               "File da eliminare: {}\n" \
               "Cartelle da creare: {}\n" \
               "Cartelle da eliminare: {}\n" \
               "Totale azioni: {}\n\n" \
               "Dimensione totale dei file da spostare: {}\n" \
               "Dimensione totale dei file da eliminare: {}\n\n" \
               "Tempo di esecuzione analisi: {}\n".format(
            self._end_compare_seq_chars,
            self.copy_prog,
            self.rmfile_prog,
            self.mkdir_prog,
            self.rmdir_prog,
            self.copy_prog + self.rmfile_prog + self.mkdir_prog + self.rmdir_prog,
            Tools.format_byte_size(self.total_size_to_move),
            Tools.format_byte_size(self.total_size_to_delete),
            Tools.format_sec_min_hour(self.time_analysis))
            # self.err_analysis_count)

    def create_last_info_transfer(self):
        """In fase di trasferimento, crea una stringa terminale contenente le info di riepilogo del trasferimento"""
        return "Tempo di esecuzione trasferimento: {}\nErrori durante il trasferimento: {}".format(
            Tools.format_sec_min_hour(self.time_transfer), self.err_transfer_count)

    def reset_all_counters(self):
        """Nel momento in cui si fa una nuova anlisi vengono resettati a zero tutti i progressivi"""
        self.copy_prog = 0
        self.rmfile_prog = 0
        self.mkdir_prog = 0
        self.rmdir_prog = 0
        self.err_transfer_count = 0
        self.total_size_to_move = 0
        self.total_size_to_delete = 0
        self.time_analysis = 0
        self.time_transfer = 0

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

    def write_info_close_compare(self, moment, **kw):
        """In caso di errore durante la lettura/scrittura viene chiamato questo metodo per inserire le informazioni di
        recap prima che venga chiuso il fil compare"""
        if moment == "compare":
            self.compare_file.insert_last_info(additional_info=self.create_last_info_compare(), **kw)

        elif moment == "transfer":
            self.compare_file.insert_last_info(additional_info=self.create_last_info_transfer(), **kw)


class CompareFile:
    """Classe wrapper che rappresenta il file compare, è utilizzabile nel context manager"""

    def __init__(self, compare_file_path):
        """Il percorso e il nome del file compare possono essere passati come argomento oppure di default vengono presi
        dal file .ini. Crea il file compare, se esiste già ne crea uno nuovo compare_x.txt in modo ricorsivo"""
        self.compare_file_name = "{}_compare.txt".format(datetime.now().strftime("%Y%m%d"))
        self.compare_file_path = compare_file_path
        self.file_object = None

        while True:     # creo il file object per eseguire operazioni r/w
            try:
                self.file_object = open(os.path.join(self.compare_file_path, self.compare_file_name), mode="x", encoding="utf-8")
                break

            except FileExistsError:    # se esiste un file con lo stesso nome aggiungo '_1, _2, ... '
                self.compare_file_name = Tools.update_file_name(self.compare_file_name)

    def __enter__(self):
        """Mi permette di utilizzare CompareFile() con il context manager"""
        return self.file_object

    def __exit__(self, type, value, traceback):
        """Mi permette di utilizzare CompareFile() con il context manager"""
        self.file_object.close()

    def open(self, **kw):
        """wrappa il metodo open(), premette di evitare di inserire il percorso e nome del file compare.txt"""
        self.file_object = open(os.path.join(self.compare_file_path, self.compare_file_name), **kw)

    def inspect(self):
        """Apre il file tramite notepad/notepad++"""
        try:
            os.startfile(os.path.join(self.compare_file_path, self.compare_file_name))

        except FileNotFoundError:
            raise ParserError("File compare.txt non presente al percorso: " + os.path.join(self.compare_file_path, self.compare_file_name))

    def insert_last_info(self, additional_info=None, err_text=None):
        """Inserisce delle inforamzioni al termine oppure in caso di anomalia"""
        try:
            self.file_object.seek(0, 2)     # vado alla fine del file e scrivo l'eccezione
            if additional_info:
                self.file_object.write("\n\n{}\n".format(additional_info))

            if err_text:
                self.file_object.write("\n***\nERRORE IMPREVISTO: {}\n***\n".format(err_text))

        except ValueError:
            raise FileTransferError("Il file compare: {} non è aperto!".format(self.compare_file_name))

