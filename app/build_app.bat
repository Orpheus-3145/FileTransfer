rem nome dell'applicazione
set app_name=FileTransfer

rem eseguo il modulo PyInstaller e creo l'eseguibile
D:\"Python 3.11"\python -m PyInstaller %app_name%.spec --noconfirm

rem creo le cartelle logs e compare, necessarie al funzionamento dell'app
cd dist\%app_name%\_internal
mkdir logs, backup, compare