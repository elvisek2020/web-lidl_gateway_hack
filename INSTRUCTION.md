# Instrukce pro vytvoření Docker web aplikace - Lidl Gateway Hack

## 📋 Přehled projektu

Webová aplikace pro hackování Lidl Silvercrest Smart Home Gateway zařízení. Aplikace umožňuje:
1. Dekódování root hesla z flash paměti zařízení
2. SSH operace na gateway zařízení pro modifikaci firmware

## 🎯 Požadavky

### Funkcionalita

#### Tab 1: Návod

**Box 1: Návod na připojení a získání dat**
- Instrukce podle návodů z:
  - https://www.elvisek.cz/2021/08/zigbee-modifikace-lidl-silvercrest-zb-gateway/
  - https://paulbanks.org/projects/lidl-zigbee/root/
  - https://paulbanks.org/projects/lidl-zigbee/
- Krok za krokem:
  1. Připojení TTY3v3 serial portu k J1 konektoru na desce
  2. Nastavení serial portu: 38400 baud, 8N1, NO FLOW CONTROL
  3. Přerušení bootu pomocí ESC klávesy
  4. Přístup k RealTek bootloaderu (`<RealTek>` prompt)
  5. Získání KEK pomocí příkazů:
     ```
     FLR 80000000 401802 16
     DW 80000000 4
     ```
  6. Získání encrypted AUSKEY pomocí příkazů:
     ```
     FLR 80000000 402002 32
     DW 80000000 8
     ```
- Varování: Použít pouze 3.3V TTL serial port, nepřipojovat Vcc
- Formátování: Čistý, čitelný návod s příkazy v code blocích

**Box 2: Formulář pro dekódování**
- Pole pro KEK (jeden řádek hex string)
- Pole pro encrypted AUSKEY (dva řádky hex string)
- Tlačítko "Dekódovat" (modré, primární)
- Validace vstupů (kontrola hex formátu)
- Loading indikátor během dekódování

**Box 3: Výsledky**
- Zobrazení AUSKEY (celý string)
- Zobrazení root password (posledních 8 znaků AUSKEY)
- Tlačítko "Kopírovat heslo" (sekundární)
- Zobrazení pouze po úspěšném dekódování
- Error handling s popisnými chybami

#### Tab 2: Dekódování

**Box 1: Formulář pro dekódování**
- Pole pro KEK (jeden řádek hex string)
- Pole pro encrypted AUSKEY - řádek 1
- Pole pro encrypted AUSKEY - řádek 2
- Tlačítko "Dekódovat" (modré, primární)
- Validace vstupů (kontrola hex formátu)
- Loading indikátor během dekódování

**Box 2: Výsledky**
- Zobrazení AUSKEY (celý string)
- Zobrazení root password (posledních 8 znaků AUSKEY)
- Zobrazení pouze po úspěšném dekódování
- Error handling s popisnými chybami

#### Tab 3: Připojení

**Box 1: Připojení k SSH**
- Formulář:
  - IP adresa gateway (např. 10.104.2.39)
  - SSH port (výchozí 22, možnost změny)
  - Root heslo (z tabu 1 nebo ručně)
- Tlačítka:
  - "Připojit" (modré, primární)
  - "Odpojit" (šedé, sekundární)
- Status indikátor:
  - Zelená tečka + "Připojeno" / Červená tečka + "Odpojeno"
  - Zobrazení aktuální IP a portu při připojení
- Validace před připojením (IP formát, port rozsah)
- Error handling (špatné heslo, nedostupný host, atd.)

#### Tab 4: SSH server

**SSH Status Banner**
- Zobrazení aktuálního stavu SSH připojení (zelená/červená tečka)
- Zobrazení IP a portu při připojení

**Box 1: Vypnutí SSH monitoru**
- Popis: Vypne SSH monitor, který blokuje přihlášení po neúspěšných pokusech
- Příkazy:
  ```bash
  if [ ! -f /tuya/ssh_monitor.original.sh ]; then cp /tuya/ssh_monitor.sh /tuya/ssh_monitor.original.sh; fi 
  echo "#!/bin/sh" >/tuya/ssh_monitor.sh
  ```
- Tlačítko: "Vypnout SSH monitor" (modré)
- Status: ✓ Hotovo / ✗ Nevykonáno
- Požadavek na SSH připojení (disable pokud není připojeno)
- Po úspěchu: notifikace "SSH monitor byl vypnut"

**Box 2: Restart zařízení**
- Tlačítko: "Restartovat zařízení" (červené, destruktivní)
- Modal s potvrzením před rebootem
- Po rebootu automatické odpojení SSH session

#### Tab 5: Serial Gateway

**SSH Status Banner**
- Zobrazení aktuálního stavu SSH připojení (zelená/červená tečka)
- Zobrazení IP a portu při připojení

**Box 1: Nahrání serialgateway.bin**
- Popis: Nahrání binárního souboru na gateway
- Formulář:
  - Select dropdown pro výběr souboru z `binaries/` adresáře (nebo file input jako fallback)
  - Zobrazení dostupných souborů z volume (serialgateway.bin, sx.bin, atd.)
  - Cílová cesta: `/tuya/serialgateway` (zobrazeno jako info)
- Tlačítko: "Nahrát serialgateway.bin" (modré)
- Status: ✓ Nahrané / ✗ Nevykonáno
- Zobrazení velikosti souboru po výběru
- Po nahrání automaticky `chmod 755 /tuya/serialgateway`
- Požadavek na SSH připojení
- Progress indikátor během uploadu
- **Poznámka:** Soubory se načítají z Docker volume (`/app/binaries/`), takže je možné je aktualizovat bez rebuildu

**Box 2: Úprava tuya_start.sh**
- Popis: Upraví startovací skript pro spuštění serialgateway při bootu
- Příkazy:
  ```bash
  if [ ! -f /tuya/tuya_start.original.sh ]; then cp /tuya/tuya_start.sh /tuya/tuya_start.original.sh; fi
  cat >/tuya/tuya_start.sh <<EOF
  #!/bin/sh
  /tuya/serialgateway &
  EOF
  ```
- Tlačítko: "Upravit tuya_start.sh" (modré)
- Status: ✓ Hotovo / ✗ Nevykonáno
- Volitelné: Zobrazení aktuálního obsahu souboru (expandovatelný box)
- Požadavek na SSH připojení

**Box 3: Restart zařízení**
- Tlačítko: "Restartovat zařízení" (červené, destruktivní)
- Modal s potvrzením před rebootem
- Po rebootu automatické odpojení SSH session

#### Tab 6: Statická IP adresa

**SSH Status Banner**
- Zobrazení aktuálního stavu SSH připojení (zelená/červená tečka)
- Zobrazení IP a portu při připojení

**Box 1: Nastavení statické IP adresy**
- Popis: Nastaví statickou IP adresu pro eth1 rozhraní
- Formulář:
  - IP adresa (např. 10.104.2.22)
  - Rozhraní: eth1 (pevně, zobrazeno jako info)
- Tlačítko: "Nastavit statickou IP" (modré)
- Status: ✓ Nastaveno / ✗ Nevykonáno
- Varování: "Změna se projeví po rebootu zařízení"
- Příkazy:
  ```bash
  killall udhcpc
  ifconfig eth1 [IP_ADDRESS]
  ```
- Požadavek na SSH připojení

**Box 2: Restart zařízení**
- Tlačítko: "Restartovat zařízení" (červené, destruktivní)
- Modal s potvrzením před rebootem:
  - Text: "Opravdu chcete restartovat zařízení?"
  - Tlačítka: "Zrušit" (šedé) / "Ano, restartovat" (červené)
- Po rebootu automatické odpojení SSH session

#### Tab 7: Upgrade Firmware

**SSH Status Banner**
- Zobrazení aktuálního stavu SSH připojení (zelená/červená tečka)
- Zobrazení IP a portu při připojení

**Box 1: Návod**
- Popis upgrade procesu TuYa Zigbee modulu TYZS4
- Informace o upgrade z verze 6.5.0.0 na 6.7.8.0
- Varování a instrukce

**Box 2: Zastavení serialgateway**
- Zastaví serialgateway službu před upgrade
- Příkazy:
  ```bash
  mv /tuya/serialgateway /tuya/serialgateway_norun
  killall serialgateway
  ```

**Box 3: Nahrání upgrade souborů**
- Výběr firmware souboru (.gbl) z `binaries/` adresáře
- Automatické nahrání `sx.bin` a vybraného firmware souboru
- Cílové cesty: `/tmp/sx` a `/tmp/firmware.gbl`

**Box 4: Spuštění upgrade**
- Výběr EZSP verze (V7 nebo V8)
- Spuštění upgrade procesu (může trvat několik minut)
- Automatický reboot po dokončení
- Potvrzení před spuštěním

**Box 5: Obnovení serialgateway (po restartu)**
- Obnoví serialgateway službu po úspěšném upgrade
- Příkaz: `mv /tuya/serialgateway_norun /tuya/serialgateway`

### Technologický stack

**Backend:**
- FastAPI (Python 3.11+)
- Paramiko pro SSH operace
- Cryptography pro dekódování AUSKEY
- Jinja2 pro server-side rendering
- Uvicorn jako ASGI server

**Frontend:**
- Tailwind CSS (via CDN) - box-style komponenty
- HTMX pro dynamické obsahy bez reloadu
- Vanilla JavaScript (minimální) - pouze pro notifikace
- Server-side rendering s Jinja2

**Deployment:**
- Docker (Python 3.11-slim base image)
- Docker Compose pro snadné spuštění

### Struktura projektu

```
lidl_gateway_hack/
├── binaries/                   # Adresář s binárními soubory (mapován do Docker volume)
│   ├── serialgateway.bin
│   ├── sx.bin
│   ├── NCP_UHW_MG1B232_678_PA0-PA1-PB11_PA5-PA4.gbl
│   └── ... (další firmware soubory)
├── _docker/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI aplikace + routy
│   │   ├── decode.py               # Logika dekódování AUSKEY (z lidl_auskey_decode_v0.3.py)
│   │   ├── ssh_operations.py       # SSH operace na gateway
│   │   └── models.py               # Datové modely (Pydantic)
│   ├── templates/
│   │   ├── base.html               # Base template s Tailwind CSS, HTMX, JS
│   │   ├── index.html              # Hlavní stránka s tabs
│   │   └── partials/               # HTMX partials
│   │       ├── decode_result.html
│   │       ├── ssh_status.html
│   │       └── firmware_status.html
│   ├── images/
│   │   └── screen.png              # Screenshot aplikace
│   ├── static/
│   │   ├── css/
│   │   │   └── app.css             # Vlastní CSS (pokud potřeba)
│   │   └── js/
│   │       └── app.js              # JavaScript pro notifikace (showNotification)
│   ├── requirements.txt            # Python závislosti
│   ├── Dockerfile                  # Docker image definice
│   ├── docker-compose.yml          # Docker Compose konfigurace
│   ├── INSTRUCTION.md              # Tento dokument
│   └── README.md                   # Dokumentace podle TEMPLATE_README.md
└── ... (ostatní soubory projektu)
```

### API endpointy

**Dekódování:**
- `GET /` - hlavní stránka
- `POST /api/decode` - dekódování AUSKEY
  - Request: `{ "kek": "...", "auskey_line1": "...", "auskey_line2": "..." }`
  - Response: `{ "auskey": "...", "root_password": "..." }`

**SSH operace:**
- `POST /api/ssh/connect` - připojení k SSH
  - Request: Form data `{ "host": "...", "port": 22, "password": "..." }`
  - Response: HTML partial se statusem
- `POST /api/ssh/disconnect` - odpojení
  - Response: HTML partial se statusem
- `GET /api/ssh/status` - status připojení
  - Response: `{ "connected": true/false, "host": "...", "port": 22 }`
- `POST /api/ssh/disable-monitor` - vypnutí SSH monitoru
  - Response: HTML partial se statusem
- `POST /api/ssh/upload-serialgateway` - nahrání serialgateway.bin
  - Request: Form data `{ "filename": "serialgateway.bin" }` (soubor se načte z `/app/binaries/`)
  - Response: HTML partial se statusem
- `GET /api/files/list` - seznam dostupných binárních souborů
  - Response: `{ "files": ["serialgateway.bin", "sx.bin", ...] }`
- `POST /api/ssh/update-tuya-start` - úprava tuya_start.sh
  - Response: HTML partial se statusem
- `POST /api/ssh/set-static-ip` - nastavení statické IP
  - Request: Form data `{ "ip": "10.104.2.22" }`
  - Response: HTML partial se statusem
- `POST /api/ssh/reboot` - reboot zařízení
  - Response: HTML partial se statusem

**Upgrade firmware:**
- `POST /api/firmware/stop-serialgateway` - zastavení serialgateway
  - Response: HTML partial se statusem
- `POST /api/firmware/upload-files` - nahrání upgrade souborů
  - Request: Form data `{ "firmware_filename": "firmware.gbl" }`
  - Response: HTML partial se statusem
- `POST /api/firmware/upgrade` - spuštění upgrade firmware
  - Request: Form data `{ "firmware_filename": "...", "ezsp_version": "V7" }`
  - Response: HTML partial se statusem
- `POST /api/firmware/restore-serialgateway` - obnovení serialgateway
  - Response: HTML partial se statusem

### UI komponenty (podle TEMPLATE_COMPONENTS.md)

**Tabs jako tlačítka:**
- Aktivní tab: `bg-blue-600 text-white`
- Neaktivní tab: `bg-gray-100 text-gray-700 hover:bg-gray-200`

**Boxy:**
- Standardní box: `bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6`
- Nadpis sekce: `text-lg font-semibold text-gray-900 mb-4`

**Tlačítka:**
- Primární: `px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors`
- Sekundární: `px-4 py-2 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700 transition-colors`
- Destruktivní: `px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors`

**Formuláře:**
- Input: `w-full px-3 py-2 border border-gray-300 rounded-lg h-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500`
- Label: `block text-sm font-medium text-gray-700 mb-2`

**Status indikátory:**
- Úspěch: `inline-block w-3 h-3 rounded-full bg-green-500`
- Chyba: `inline-block w-3 h-3 rounded-full bg-red-500`

### Bezpečnost

- SSH hesla se neukládají persistentně (pouze v server-side session)
- Timeout pro SSH operace (30 sekund)
- Validace všech vstupů (IP adresy, porty, hex stringy)
- Sanitizace všech výstupů
- Max velikost uploadu: 10MB
- Error handling s popisnými chybami (bez zveřejnění citlivých informací)

### Logika dekódování

Použít přesnou logiku z `lidl_auskey_decode_v0.3.py`:
- `_decode_kek()` - dekódování KEK
- `_get_bytes()` - parsování hex stringů
- AES ECB dekódování pomocí `cryptography` knihovny
- Root password = posledních 8 znaků AUSKEY

### Session management

- SSH připojení se ukládají v server-side session (FastAPI sessions)
- Session ID se ukládá v cookie
- Při odpojení se SSH klient zavře a odstraní ze session
- Timeout session: 1 hodina nečinnosti

### Error handling

- Všechny SSH operace v try-except blocích
- Popisné error messages pro uživatele
- Logging všech chyb na serveru
- HTMX error handling (zobrazení chyb v UI)

### Notifikace

- Použít globální `showNotification()` funkci
- Typy: 'success', 'error', 'info'
- Automatické zmizení po 5 sekundách

### Docker konfigurace

**Dockerfile:**
- Base: `python:3.11-slim`
- Instalace závislostí z `requirements.txt`
- Kopírování aplikace
- Exponování portu 8000
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

**docker-compose.yml:**
- Service: `app`
- Port mapping: `8001:8000` (aplikace dostupná na http://localhost:8001)
- Environment: `PYTHONUNBUFFERED=1`, `LOG_LEVEL=INFO`, `SESSION_SECRET`
- Restart: `unless-stopped`
- **Volume pro binární soubory:**
  - Mapování: `./binaries:/app/binaries` (read-only)
  - Účel: Ukládání a přístup k binárním souborům (serialgateway.bin, sx.bin, firmware soubory)
  - Umožňuje aktualizaci souborů bez rebuildu Docker image
  - Aplikace bude přistupovat k souborům z `/app/binaries/` v kontejneru

**Struktura binárních souborů:**
- Vytvořit adresář `binaries/` v root projektu (sourozenec `_docker/`)
- Umístit tam soubory:
  - `serialgateway.bin`
  - `sx.bin`
  - `NCP_UHW_MG1B232_678_PA0-PA1-PB11_PA5-PA4.gbl`
  - Další firmware soubory podle potřeby
- Aplikace bude číst soubory z tohoto adresáře při SSH operacích

### README.md struktura

Podle TEMPLATE_README.md:
- Název aplikace: "Lidl Gateway Hack"
- Popis aplikace
- Funkce (seznam všech funkcí)
- Použití (workflow)
- Deployment (Docker Compose)
- Technická dokumentace
- API dokumentace
- Vývoj

### Reference

- Původní Python skript: `lidl_auskey_decode_v0.3.py`
- Návody:
  - https://www.elvisek.cz/2021/08/zigbee-modifikace-lidl-silvercrest-zb-gateway/
  - https://paulbanks.org/projects/lidl-zigbee/root/
  - https://paulbanks.org/projects/lidl-zigbee/
- Template dokumentace: `_TEMPLATES_WEB_APPLICATION/`
- SSH příkazy: `!script-read-me.txt`

## ✅ Checklist implementace

- [x] Vytvořit strukturu projektu
- [x] Implementovat base template s Tailwind CSS a HTMX
- [x] Implementovat Tab 1 - Návod
- [x] Implementovat Tab 2 - Dekódování (všechny boxy)
- [x] Implementovat Tab 3 - Připojení
- [x] Implementovat Tab 4 - SSH server
- [x] Implementovat Tab 5 - Serial Gateway
- [x] Implementovat Tab 6 - Statická IP adresa
- [x] Implementovat Tab 7 - Upgrade Firmware
- [x] Implementovat backend API endpointy
- [x] Implementovat SSH operace s Paramiko
- [x] Implementovat logiku dekódování
- [x] Implementovat session management
- [x] Přidat error handling
- [x] Přidat validace
- [x] Vytvořit adresář `binaries/` v root projektu
- [x] Přesunout/zkopírovat binární soubory do `binaries/`
- [x] Vytvořit Dockerfile
- [x] Vytvořit docker-compose.yml s volume mappingem
- [x] Implementovat přístup k souborům z volume v aplikaci
- [x] Vytvořit README.md podle šablony
- [x] Přidat screenshot aplikace
- [x] Otestovat všechny funkce

---

**Poznámka:** Při implementaci vždy používej box-style komponenty podle TEMPLATE_COMPONENTS.md a dodržuj strukturu podle TEMPLATE_LAYOUT.md.
