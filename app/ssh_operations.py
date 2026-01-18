"""
SSH operace na Lidl Gateway zařízení.
"""
import paramiko
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Cesta k binárním souborům v kontejneru
BINARIES_PATH = "/app/binaries"


class SSHSession:
    """Správa SSH session."""
    
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.host: Optional[str] = None
        self.port: Optional[int] = None
    
    def connect(self, host: str, port: int, password: str, timeout: int = 30) -> dict:
        """
        Připojí se k SSH serveru.
        
        Returns:
            dict s statusem připojení
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=host,
                port=port,
                username="root",
                password=password,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False
            )
            self.sftp = self.client.open_sftp()
            self.host = host
            self.port = port
            logger.info(f"SSH připojení úspěšné: {host}:{port}")
            return {"status": "connected", "host": host, "port": port}
        except paramiko.AuthenticationException:
            logger.error("SSH autentizace selhala")
            raise ValueError("Špatné heslo nebo uživatel")
        except paramiko.SSHException as e:
            logger.error(f"SSH chyba: {e}")
            raise ValueError(f"SSH chyba: {str(e)}")
        except Exception as e:
            logger.error(f"Připojení selhalo: {e}")
            raise ValueError(f"Nelze se připojit k {host}:{port} - {str(e)}")
    
    def disconnect(self):
        """Odpojí SSH session."""
        if self.sftp:
            try:
                self.sftp.close()
            except:
                pass
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.client = None
        self.sftp = None
        self.host = None
        self.port = None
        logger.info("SSH odpojeno")
    
    def is_connected(self) -> bool:
        """Zkontroluje, zda je SSH připojeno."""
        if not self.client:
            return False
        try:
            transport = self.client.get_transport()
            return transport and transport.is_active()
        except:
            return False
    
    def execute_command(self, command: str, timeout: int = 30) -> tuple[str, str, int]:
        """
        Provede příkaz přes SSH.
        
        Returns:
            tuple (stdout, stderr, exit_code)
        """
        if not self.is_connected():
            raise ValueError("SSH není připojeno")
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8', errors='ignore')
            stderr_text = stderr.read().decode('utf-8', errors='ignore')
            return stdout_text, stderr_text, exit_code
        except Exception as e:
            logger.error(f"Chyba při provádění příkazu: {e}")
            raise ValueError(f"Chyba při provádění příkazu: {str(e)}")
    
    def disable_ssh_monitor(self) -> dict:
        """Vypne SSH monitor."""
        commands = [
            'if [ ! -f /tuya/ssh_monitor.original.sh ]; then cp /tuya/ssh_monitor.sh /tuya/ssh_monitor.original.sh; fi',
            'echo "#!/bin/sh" >/tuya/ssh_monitor.sh'
        ]
        
        for cmd in commands:
            stdout, stderr, exit_code = self.execute_command(cmd)
            if exit_code != 0:
                raise ValueError(f"Chyba při vypínání SSH monitoru: {stderr}")
        
        return {"status": "success", "message": "SSH monitor byl vypnut"}
    
    def upload_file(self, local_path: str, remote_path: str) -> dict:
        """
        Nahraje soubor na vzdálený server.
        
        Args:
            local_path: Cesta k lokálnímu souboru
            remote_path: Cesta na vzdáleném serveru
        """
        if not self.is_connected() or not self.sftp:
            raise ValueError("SSH není připojeno")
        
        try:
            # Získání velikosti souboru
            file_size = os.path.getsize(local_path)
            
            # Nahrání souboru
            self.sftp.put(local_path, remote_path)
            
            # Nastavení oprávnění
            self.sftp.chmod(remote_path, 0o755)
            
            logger.info(f"Soubor nahrán: {local_path} -> {remote_path} ({file_size} bytes)")
            return {"status": "success", "size": file_size}
        except Exception as e:
            logger.error(f"Chyba při nahrávání souboru: {e}")
            raise ValueError(f"Chyba při nahrávání souboru: {str(e)}")
    
    def update_tuya_start(self) -> dict:
        """Upraví tuya_start.sh pro spuštění serialgateway."""
        commands = [
            'if [ ! -f /tuya/tuya_start.original.sh ]; then cp /tuya/tuya_start.sh /tuya/tuya_start.original.sh; fi',
            '''cat >/tuya/tuya_start.sh <<'EOF'
#!/bin/sh
/tuya/serialgateway &
EOF'''
        ]
        
        for cmd in commands:
            stdout, stderr, exit_code = self.execute_command(cmd)
            if exit_code != 0:
                raise ValueError(f"Chyba při úpravě tuya_start.sh: {stderr}")
        
        return {"status": "success", "message": "tuya_start.sh byl upraven"}
    
    def set_static_ip(self, ip: str) -> dict:
        """Nastaví statickou IP adresu."""
        commands = [
            'killall udhcpc',
            f'ifconfig eth1 {ip}'
        ]
        
        for cmd in commands:
            stdout, stderr, exit_code = self.execute_command(cmd)
            # killall může vrátit exit code 1 pokud proces neběží, to je OK
            if exit_code != 0 and 'killall' not in cmd:
                raise ValueError(f"Chyba při nastavení statické IP: {stderr}")
        
        return {"status": "success", "message": f"Statická IP nastavena na {ip}"}
    
    def reboot(self) -> dict:
        """Restartuje zařízení."""
        try:
            # Spuštění rebootu na pozadí (aby se SSH session mohla zavřít)
            self.execute_command('reboot &', timeout=5)
            # Odpojení session
            self.disconnect()
            return {"status": "rebooting", "message": "Zařízení se restartuje"}
        except:
            # I když příkaz selže, odpojíme session
            self.disconnect()
            return {"status": "rebooting", "message": "Zařízení se restartuje"}


def get_available_files() -> list[str]:
    """Vrací seznam dostupných binárních souborů."""
    if not os.path.exists(BINARIES_PATH):
        return []
    
    try:
        files = []
        for filename in os.listdir(BINARIES_PATH):
            filepath = os.path.join(BINARIES_PATH, filename)
            if os.path.isfile(filepath):
                files.append(filename)
        return sorted(files)
    except Exception as e:
        logger.error(f"Chyba při čtení souborů: {e}")
        return []


def get_file_path(filename: str) -> str:
    """Vrací plnou cestu k souboru."""
    filepath = os.path.join(BINARIES_PATH, filename)
    # Bezpečnostní kontrola
    if not os.path.abspath(filepath).startswith(os.path.abspath(BINARIES_PATH)):
        raise ValueError("Neplatná cesta k souboru")
    if not os.path.exists(filepath):
        raise ValueError(f"Soubor {filename} neexistuje")
    return filepath


class FirmwareUpgrade:
    """Správa upgrade firmware Zigbee modulu."""
    
    def __init__(self, ssh_session: SSHSession):
        self.session = ssh_session
    
    def stop_serialgateway(self) -> dict:
        """Zastaví serialgateway službu."""
        commands = [
            'mv /tuya/serialgateway /tuya/serialgateway_norun',
            'killall serialgateway'
        ]
        
        for cmd in commands:
            stdout, stderr, exit_code = self.session.execute_command(cmd)
            # killall může vrátit exit code 1 pokud proces neběží, to je OK
            if exit_code != 0 and 'killall' not in cmd:
                raise ValueError(f"Chyba při zastavování serialgateway: {stderr}")
        
        logger.info("serialgateway byl zastaven")
        return {"status": "success", "message": "serialgateway byl zastaven"}
    
    def upload_upgrade_files(self, firmware_filename: str) -> dict:
        """
        Nahraje soubory potřebné pro upgrade.
        
        Args:
            firmware_filename: Název firmware souboru (.gbl)
        """
        if not self.session.is_connected() or not self.session.sftp:
            raise ValueError("SSH není připojeno")
        
        try:
            # Nahrání sx.bin
            sx_path = get_file_path("sx.bin")
            self.session.sftp.put(sx_path, "/tmp/sx")
            self.session.sftp.chmod("/tmp/sx", 0o755)
            
            # Nahrání firmware
            firmware_path = get_file_path(firmware_filename)
            self.session.sftp.put(firmware_path, "/tmp/firmware.gbl")
            
            logger.info(f"Upgrade soubory nahrány: sx.bin a {firmware_filename}")
            return {"status": "success", "message": f"Soubory sx.bin a {firmware_filename} byly nahrány"}
        except FileNotFoundError as e:
            logger.error(f"Soubor nenalezen: {e}")
            raise ValueError(f"Soubor nenalezen: {str(e)}")
        except Exception as e:
            logger.error(f"Chyba při nahrávání upgrade souborů: {e}")
            raise ValueError(f"Chyba při nahrávání souborů: {str(e)}")
    
    def perform_upgrade(self, ezsp_version: str = "V7") -> dict:
        """
        Provede upgrade firmware Zigbee modulu.
        
        Args:
            ezsp_version: Verze EZSP (V7 nebo V8)
        """
        if ezsp_version not in ["V7", "V8"]:
            raise ValueError("EZSP verze musí být V7 nebo V8")
        
        # Konfigurační frame podle verze
        if ezsp_version == "V8":
            config_frame = "\\x00\\x42\\x21\\xA8\\x5C\\x2C\\xA0\\x7E"
        else:
            config_frame = "\\x00\\x42\\x21\\xA8\\x53\\xDD\\x4F\\x7E"
        
        # Sekvence příkazů pro upgrade
        commands = [
            'stty -F /dev/ttyS1 115200 cs8 -cstopb -parenb -ixon crtscts raw',
            f"echo -en '\\x1A\\xC0\\x38\\xBC\\x7E' > /dev/ttyS1",
            f"echo -en '{config_frame}' > /dev/ttyS1",
            "echo -en '\\x81\\x60\\x59\\x7E' > /dev/ttyS1",
            "echo -en '\\x7D\\x31\\x43\\x21\\x27\\x55\\x6E\\x90\\x7E' > /dev/ttyS1",
            'stty -F /dev/ttyS1 115200 cs8 -cstopb -parenb -ixon -crtscts raw',
            "echo -e '1' > /dev/ttyS1",
            '/tmp/sx /tmp/firmware.gbl < /dev/ttyS1 > /dev/ttyS1'
        ]
        
        try:
            for i, cmd in enumerate(commands):
                stdout, stderr, exit_code = self.session.execute_command(cmd, timeout=120 if '/tmp/sx' in cmd else 60)
                if exit_code != 0:
                    # Poslední příkaz (sx) může trvat déle a může skončit s chybou, ignorujeme
                    if '/tmp/sx' in cmd:
                        logger.info("Upgrade probíhá, může trvat několik minut...")
                        # Počkáme chvíli a pak reboot
                        break
                    else:
                        raise ValueError(f"Chyba při upgrade: {stderr}")
            
            # Reboot po upgrade
            logger.info("Upgrade dokončen, spouštím reboot...")
            self.session.reboot()
            return {"status": "success", "message": "Upgrade dokončen, zařízení se restartuje"}
        except Exception as e:
            logger.error(f"Chyba při upgrade firmware: {e}")
            raise ValueError(f"Chyba při upgrade: {str(e)}")
    
    def restore_serialgateway(self) -> dict:
        """Obnoví serialgateway službu."""
        try:
            stdout, stderr, exit_code = self.session.execute_command(
                'mv /tuya/serialgateway_norun /tuya/serialgateway'
            )
            if exit_code != 0:
                raise ValueError(f"Chyba při obnovování serialgateway: {stderr}")
            return {"status": "success", "message": "serialgateway byl obnoven"}
        except Exception as e:
            logger.error(f"Chyba při obnovování serialgateway: {e}")
            raise ValueError(f"Chyba při obnovování: {str(e)}")
