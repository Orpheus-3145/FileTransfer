import os
import shutil
import stat
import re
import time
from os.path import normpath
import logging
from datetime import date
from math import floor, ceil
import win32api


class ToolsUtilitiesError(Exception):
    """Eccezione sollevata da una delle funzioni del modulo Tools"""
    def __init__(self, error_text):
        super().__init__()
        self.error_text = error_text  # creo la proprietà di classe per avere maggiori informazioni sull'errore verificatosi

    def __str__(self):
        return self.error_text


# non usato
def remove_child_directories(list_to_filter):
    """Riceve una lista di percorsi di directory, viene filtrata togliendo tutte le cartelle che hanno una cartella madre
    già presente nella lista ---- e.g. l = [A, A\\B, A\\B\\C, A\\D] deve rimanere solo A, le altre sono tutte figlie di A e
    vanno pertanto rimosse; NB: funziona <=> le directory sono inserite nella lista in ordine (cioè [A, A\\B, A\\B\\C] e
    non [A\\B, A\\B\\C, A]"""

    filtered_list = []
    index_loop = 0

    while index_loop in range(len(list_to_filter)):
        current_folder = list_to_filter[index_loop]
        filtered_list.append(current_folder)

        # se non vado out of bounds e il carattere di controllo (current_folder) è contenuto nel successivo skippo il prossimo elemento
        while index_loop + 1 < len(list_to_filter) and list_to_filter[index_loop + 1].startswith(current_folder):
            index_loop += 1

        index_loop += 1

    return filtered_list


def create_dir_and_children(path_src, path_dst):
    """Crea l'ultima cartella di path_src al percorso dst, crea anche tutti i suoi file e tutte le eventuali sottocartelle"""
    path_of_folder = os.path.dirname(path_src)

    for directory, list_dir, list_file in os.walk(path_src):
        path_to_create = os.path.join(path_dst, directory.replace(path_of_folder + "\\", ""))  # rimuovo inoltre il percorso iniziale, comune a tutte le directory e lo unico alla cartella origine in dst
        os.mkdir(path_to_create)
        for file_name in list_file:
            shutil.copy2(os.path.join(directory, file_name), path_to_create)


def get_all_dirs_from_path(path, mode=None):
    """Ricava una lista contenente tutte le sottodirectory tramite la funzione os.walk()
        - il parametro mode ('base_directory' - None) indica se restituire i percorsi in modo assoluto
        oppure relativo a dirname(path), cioè dalla cartella di base in avanti"""

    dir_list = []

    def launch_error(os_error):
        """La funzione launch_error passata nel parametro onerror di os.walk() permette di esplicitare gli errori
        verificatosi durante la creazione delle sotto directory"""
        raise os_error

    for directory, list_dir, list_file in os.walk(path, onerror=launch_error):
        if mode == "base_directory":    # prendo il percorso dalla cartella di base in avanti
            directory = directory.replace(os.path.dirname(path), "")       # rimuovo inoltre il percorso iniziale, comune a tutte le directory

            while directory[0] == "\\":
                directory = directory[1:]

        dir_list.append(normpath(directory))

    return dir_list


def create_entity_list(path, type_entity="file", full_path=False):
    """Crea una lista di entità, file (default) o cartelle contenuti in path, se full_path=True allora restituisco le
    entità con il percorso file completo"""
    type_dict = {"file": os.path.isfile, "directory": os.path.isdir}
    if type_entity not in type_dict.keys():
        raise ToolsUtilitiesError("Valore passato non valido: {}".format(type_entity))

    # a seconda del parametro type (file/directory) uso per filtrare le funzioni isfile(), isdir()
    entities_list = list(filter(type_dict[type_entity], list(map(lambda element: os.path.join(path, element), os.listdir(path)))))

    if full_path is False:   # di default rimuovo i percorsi file delle entità
        entities_list = list(map(os.path.basename, entities_list))

    return entities_list


# non usato
def get_total_count_children(path):
    """Restituisce un dizionario rappresentante il numero totale di file e sottocartelle contenuti nel percorso passato,
    vengono contati tutti i file di tutte le eventuali sottocartelle, l'ultimo elemento del dizionario è la dimensione
    totale dei file contenuti il path"""

    dir_count = 0       # conteggio delle cartelle e sottocartelle contenute in path
    file_count = 0      # conteggio di tutti i file contenuti in path
    total_size = 0      # dimensione totale di path

    for directory, list_dir, list_file in os.walk(path):
        dir_count += 1
        file_count += len(list_file)

        for file in list_file:
            total_size += os.path.getsize(os.path.join(directory, file))

    return {"n_directory": dir_count, "n_file": file_count, "size": total_size}     # dir_count - 1 perchè il metodo walk() restituisce anche la cartella stessa


def check_if_path_exists(path):
    """Windows ha un filesystem case insensitive, quindi non fa differenza tra i percorsi A\\B e a\\b; in questo modo
    posso verificare se un percorso esiste o meno in modo case sensitive"""

    if not os.path.exists(path):
        return False

    else:   # lo strutturo in questo modo per sfruttare la lazy evaluation con un funzione pesante (os.listdir)
        if os.path.basename(path) in os.listdir(os.path.dirname(path)):
            return True

        else:
            return False


def find_removed_drive(drive_list):
    """Poichè le eccezioni sollevate in caso di rimozione accidentale di un driver esterno sono varie, come alternativa
    si verica da un totale di driver inizialmente collegati, quali sono ancora esistenti"""
    for drive in drive_list:
        if not os.path.exists(drive):
            return drive[:2]

    return None


def get_exact_folder(path):
    """Vedi funzione check_if_path_exists(), passo come parametro un percorso ad una directory che esiste e che ha lo
    stesso nome, case sensitivity a parte, restituisco il percorso con il nome corretto, rispettando la case sensitivity"""

    dir_list = create_entity_list(os.path.dirname(path), type_entity="directory")
    dir_to_check = os.path.basename(path)

    for directory in dir_list:
        if directory.lower() == dir_to_check.lower():
            return os.path.join(os.path.dirname(path), directory)

    raise ToolsUtilitiesError("Cartella: {} non trovata!".format(path))  # se arrivo a questo punto vuol dire che la cartella non esiste più, lancio errore


def format_byte_size(bytes_size):
    """Riceve un numero x di byte, restituisce una stringa in cui i bytes sono formattati in Kb, Mb e Gb"""
    if bytes_size == "":
        return "0 b"

    try:
        int(bytes_size)

    except ValueError:
        raise ToolsUtilitiesError("Passato un valore non valido: {}".format(bytes_size))

    else:
        if bytes_size > 1024:
            k_bytes = bytes_size / 1024  # ottengo i kilobyte

            if k_bytes > 1024:
                m_bytes = k_bytes / 1024  # ottengo i megabyte

                if m_bytes > 1024:
                    g_bytes = m_bytes / 1024  # ottengo i gigabyte

                    if g_bytes >= 1024:
                        return "dimensione superiore ad 1 Tb!"

                    return "{:.2f} Gb".format(g_bytes)

                else:
                    return "{:.2f} Mb".format(m_bytes)

            else:
                return "{:.2f} Kb".format(k_bytes)

        else:
            return "{} b".format(bytes_size)


def format_sec_min_hour(secs):
    """Riceve un numero x di secondi, restituisce una stringa in cui i secondi sono formattati in ore, minuti, secondi"""
    if secs == "":
        return "0 sec"

    try:
        secs = float(secs)

    except ValueError:
        raise ToolsUtilitiesError("Passato un valore non valido: {}".format(secs))

    else:
        if secs > 60:
            mins = floor(secs / 60)  # ottengo i minuti
            if mins > 60:
                hours = floor(mins / 60)  # ottengo le ore

                if hours > 24:
                    return "Durata superiore a 24h!"

                return "{} hour {} min {} sec".format(hours, floor(mins - hours * 60), floor(secs - mins * 60))

            else:
                return "{} min {} sec".format(mins, floor(secs - mins * 60))

        else:
            return "{:.2f} sec".format(secs)


def remove_readonly(func, path, excinfo):
    """Definisco una funzione che mi permette di gestire la cancellazione di file read only --> quando shutil.rmtree() od
     os.remove solleva PermissionError; non viene proprio generata l'eccezione, il file in questione viene messo in write ed
    eliminato"""
    os.chmod(path, stat.S_IWUSR)
    func(path)


def update_file_name(old_file_name):
    """Il parametro passato rappresenta il nome di un file già esistente e deve essere nella forma 'nome_file_x.txt'
    dove x rappresenta un progressivo, restituisce un nuovo nome nella forma 'nome_file_(x+1).txt'"""

    try:
        old_prog = int(re.search(r"_\d*.txt", old_file_name).group()[1: -4])

    except AttributeError:  # se re.search(r"_\d*.txt", old_file_name) = None, non esiste progressivo, parto da 1
        return old_file_name.replace(".txt", "_1.txt")

    else:   # se old_prog <> None allora il metodo group() non solleva eccezioni ==> esiste già un progressivo, lo aumento
        new_prog = old_prog + 1
        return old_file_name.replace("_{}.txt".format(old_prog), "_{}.txt".format(new_prog))


def create_logger(level, log_name, log_path, fmt):
    """Funzione che crea un log, popolato tramite le chiamate a logging"""
    logger = logging.getLogger('filetransfer_logger')
    logging.root = logger
    logger.setLevel(level)

    file_handler = logging.FileHandler(filename=os.path.join(log_path, log_name.format(date.today().strftime("%d-%m-%Y"))), encoding="utf-8")
    log_formatter = logging.Formatter(fmt=fmt)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)


def set_center_app(config_obj):
    """A seconda dello schermo che uso, centro l'app nel monitor aggiornando il file .ini associato all'istanza di
    Config"""
    from win32api import GetSystemMetrics   # per trovare le dimensioni dello schermo in uso

    width_app = config_obj.getint("graphics", "width")
    height_app = config_obj.getint("graphics", "height")
    width_screen = GetSystemMetrics(0)
    height_screen = GetSystemMetrics(1)

    config_obj.set("graphics", "top", str((height_screen - height_app) // 2))
    config_obj.set("graphics", "left", str((width_screen - width_app) // 2))

    config_obj.write()


def get_drive_list():
    """Restituisce una lista degli hard disk presenti nel pc"""
    drives = win32api.GetLogicalDriveStrings()
    return drives.split('\000')[:-1]


def get_perc_font(len_str):
    """La dimensione del font deve essere in funzione del numero di caratteri della stringa che deve essere inserita in
    un'etichetta (per evitare tagli), creo quindi una funzione interpolante (polinomiale, metodo di Lagrange) a seconda
    di alcuni punti (elencati qui sotto) per cui si ha un buon compromesso font_size/lunghezza caratteri"""
    # TODO nb la dimensione finale è calcolata in base alle dimensioni della label che contiene la stringa, bisogna generalizzare

    # 1° coppia (250, 0.32)
    # 2° coppia (63, 0.5)
    # 3° coppia (163, 0.37)
    # 4° coppia (116, 0.42)
    # 5° coppia (209, 0.324)
    # 6° coppia (91, 0.45)

    x_0, y_0 = 250, 0.32    # 250 estremo superiore
    x_1, y_1 = 63, 0.5      # 63 estremo inferiore
    x_2, y_2 = 163, 0.37    # valore contenuto tra x_0 e x_1

    if len_str < x_1:       # se la lunghezza di len_str è minore dell'estremo inf o maggiore di quello sup. uso valori costanti
        return y_1

    elif len_str > x_0:
        return y_0

    else:   # se invece è contenuta nell'intervallo uso la funzione interpolante
        return y_0 * ((len_str - x_1)/(x_0 - x_1)) * ((len_str - x_2)/(x_0 - x_2)) +\
               y_1 * ((len_str - x_0)/(x_1 - x_0)) * ((len_str - x_2)/(x_1 - x_2)) +\
               y_2 * ((len_str - x_0)/(x_2 - x_0)) * ((len_str - x_1)/(x_2 - x_1))


if __name__ == "__main__":
    pass
