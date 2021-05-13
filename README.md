# Bundabergmixer 9000

## Autostart
Kopiere Code in Verzeichnis /home/pi/bundabergmixer_9000 und kopiere touchinterface.service nach /etc/systemd/system.
`sudo systemctl daemon-reload` (Einmalig nach Kopieren der .service)
`sudo systemctl enable touchinterface` (Um Autostart zu aktivieren)
## GPIO-Ansteuerung
Folgendes Paket installieren: `sudo apt install python3-gpiozero`
