class AppException(Exception):
    """Se si verifica un errore interno a livello di funzionamento di widget"""
    def __init__(self, error_text):
        super().__init__()
        self.error_text = error_text  # creo la proprietà di classe per avere maggiori informazioni sull'errore verificatosi

    def __str__(self):
        return self.error_text


class FileTransferError(Exception):
    """Eccezione del modulo FileTransfer.py """
    def __init__(self, error_text):
        self.error_text = error_text  # creo la proprietà di classe per avere maggiori informazioni sull'errore verificatosi
        super().__init__()

    def __str__(self):
        return self.error_text


class StateError(FileTransferError):
    """in caso di azione eseguita nello stato errato"""
    pass


# class PathError(FileTransferError):
#     pass


class SelectingFoldersError(FileTransferError):
    """Eccezione sollevata in fase di selezione dei percorsi SRC e DST, nel caso in cui uno di essi non sia valido"""
    pass


# class ComparingFoldersError(FileTransferError):
#     """Eccezione sollevata in fase di analisi di SRC e DST"""
#     pass


class TransferingFilesError(FileTransferError):
    """Eccezione sollevata in caso di errore durante il trasferimento (copia/rimuovi file/cartella)"""
    pass


class CompareFileError(FileTransferError):
    pass

# class ParserError(FileTransferError):
#     """Eccezione sollevata in caso di errore relativo ad operazioni di accesso/modifica al file compare tramite un'istanza
#     di CompareFileParser()"""
#     pass


class ToolsUtilitiesError(Exception):
    """Eccezione sollevata da una delle funzioni del modulo Tools"""
    def __init__(self, error_text):
        super().__init__()
        self.error_text = error_text  # creo la proprietà di classe per avere maggiori informazioni sull'errore verificatosi

    def __str__(self):
        return self.error_text
