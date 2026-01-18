"""
FastAPI aplikace pro Lidl Gateway Hack.
"""
from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
import logging
import uuid
from typing import Dict

from app.decode import decode_auskey
from app.models import (
    DecodeRequest, DecodeResponse,
    SSHConnectRequest, SSHStatusResponse, SSHOperationResponse,
    UploadSerialgatewayRequest, SetStaticIPRequest, FileListResponse,
    FirmwareUpgradeRequest
)
from app.ssh_operations import SSHSession, FirmwareUpgrade, get_available_files, get_file_path

# Konfigurace logování
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI aplikace
app = FastAPI(title="Lidl Gateway Hack", version="1.0.0")

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "change-me-in-production"),
    https_only=False,  # Pro lokální vývoj
    same_site="lax",
)

# Templates
templates = Jinja2Templates(directory="/app/templates")

# Static files
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

# In-memory storage pro SSH session (klíč = session ID)
ssh_sessions: Dict[str, SSHSession] = {}


def get_ssh_session(request: Request) -> SSHSession:
    """Získá SSH session z in-memory storage."""
    session_id = request.session.get("session_id")
    if not session_id:
        # Vytvoření nového session ID
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id
    
    # Vytvoření nebo načtení SSH session
    if session_id not in ssh_sessions:
        ssh_sessions[session_id] = SSHSession()
    
    return ssh_sessions[session_id]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Hlavní stránka aplikace."""
    return templates.TemplateResponse("index.html", {"request": request})


# API endpointy pro dekódování
@app.post("/api/decode")
async def decode(
    req: Request,
    kek: str = Form(...),
    auskey_line1: str = Form(...),
    auskey_line2: str = Form(...)
):
    """Dekóduje AUSKEY a root password."""
    try:
        result = decode_auskey(kek, auskey_line1, auskey_line2)
        # Vracíme HTML partial pro HTMX
        return templates.TemplateResponse(
            "partials/decode_result.html",
            {"request": req, **result}
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "partials/decode_result.html",
            {"request": req, "error": str(e)}
        )
    except Exception as e:
        logger.error(f"Chyba při dekódování: {e}")
        return templates.TemplateResponse(
            "partials/decode_result.html",
            {"request": req, "error": "Vnitřní chyba serveru"}
        )


# API endpointy pro SSH operace
@app.post("/api/ssh/connect")
async def ssh_connect(
    req: Request,
    host: str = Form(...),
    port: int = Form(22),
    password: str = Form(...)
):
    """Připojí se k SSH serveru."""
    try:
        session = get_ssh_session(req)
        result = session.connect(host, port, password)
        # Uložení informací do session
        req.session["ssh_host"] = host
        req.session["ssh_port"] = port
        # Vracíme HTML partial pro HTMX
        return templates.TemplateResponse(
            "partials/ssh_status.html",
            {"request": req, "connected": True, "host": host, "port": port}
        )
    except ValueError as e:
        # Vracíme HTML partial s chybou
        return templates.TemplateResponse(
            "partials/ssh_status.html",
            {"request": req, "connected": False, "error": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Chyba při SSH připojení: {e}")
        return templates.TemplateResponse(
            "partials/ssh_status.html",
            {"request": req, "connected": False, "error": str(e)},
            status_code=500
        )


@app.post("/api/ssh/disconnect")
async def ssh_disconnect(req: Request):
    """Odpojí SSH session."""
    try:
        session = get_ssh_session(req)
        session.disconnect()
        # Vyčištění session
        session_id = req.session.get("session_id")
        if session_id and session_id in ssh_sessions:
            del ssh_sessions[session_id]
        req.session.pop("ssh_host", None)
        req.session.pop("ssh_port", None)
        return {"status": "disconnected"}
    except Exception as e:
        logger.error(f"Chyba při odpojení: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ssh/status", response_model=SSHStatusResponse)
async def ssh_status(req: Request):
    """Vrací status SSH připojení."""
    try:
        session = get_ssh_session(req)
        if session.is_connected():
            host = req.session.get("ssh_host") or session.host
            port = req.session.get("ssh_port") or session.port
            return SSHStatusResponse(
                connected=True,
                host=host,
                port=port
            )
        else:
            return SSHStatusResponse(connected=False)
    except:
        return SSHStatusResponse(connected=False)


@app.post("/api/ssh/disable-monitor", response_model=SSHOperationResponse)
async def ssh_disable_monitor(req: Request):
    """Vypne SSH monitor."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            raise HTTPException(status_code=400, detail="SSH není připojeno")
        result = session.disable_ssh_monitor()
        return SSHOperationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chyba při vypínání SSH monitoru: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ssh/upload-serialgateway")
async def ssh_upload_serialgateway(
    req: Request,
    filename: str = Form(...)
):
    """Nahraje serialgateway.bin na server."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            raise HTTPException(status_code=400, detail="SSH není připojeno")
        
        local_path = get_file_path(filename)
        result = session.upload_file(local_path, "/tuya/serialgateway")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chyba při nahrávání souboru: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ssh/update-tuya-start", response_model=SSHOperationResponse)
async def ssh_update_tuya_start(req: Request):
    """Upraví tuya_start.sh."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            raise HTTPException(status_code=400, detail="SSH není připojeno")
        result = session.update_tuya_start()
        return SSHOperationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chyba při úpravě tuya_start.sh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ssh/set-static-ip", response_model=SSHOperationResponse)
async def ssh_set_static_ip(
    req: Request,
    ip: str = Form(...)
):
    """Nastaví statickou IP."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            raise HTTPException(status_code=400, detail="SSH není připojeno")
        result = session.set_static_ip(ip)
        return SSHOperationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chyba při nastavení statické IP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ssh/reboot", response_model=SSHOperationResponse)
async def ssh_reboot(req: Request):
    """Restartuje zařízení."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            raise HTTPException(status_code=400, detail="SSH není připojeno")
        result = session.reboot()
        # Vyčištění session po rebootu
        session_id = req.session.get("session_id")
        if session_id and session_id in ssh_sessions:
            del ssh_sessions[session_id]
        req.session.pop("ssh_host", None)
        req.session.pop("ssh_port", None)
        return SSHOperationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chyba při rebootu: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/list", response_model=FileListResponse)
async def list_files():
    """Vrací seznam dostupných binárních souborů."""
    try:
        files = get_available_files()
        return FileListResponse(files=files)
    except Exception as e:
        logger.error(f"Chyba při čtení souborů: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# API endpointy pro upgrade firmware
@app.post("/api/firmware/stop-serialgateway")
async def firmware_stop_serialgateway(req: Request):
    """Zastaví serialgateway před upgrade."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            return templates.TemplateResponse(
                "partials/firmware_status.html",
                {"request": req, "status": "error", "message": "SSH není připojeno"},
                status_code=400
            )
        upgrade = FirmwareUpgrade(session)
        result = upgrade.stop_serialgateway()
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, **result}
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Chyba při zastavování serialgateway: {e}")
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=500
        )


@app.post("/api/firmware/upload-files")
async def firmware_upload_files(
    req: Request,
    firmware_filename: str = Form(...)
):
    """Nahraje soubory potřebné pro upgrade."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            return templates.TemplateResponse(
                "partials/firmware_status.html",
                {"request": req, "status": "error", "message": "SSH není připojeno"},
                status_code=400
            )
        upgrade = FirmwareUpgrade(session)
        result = upgrade.upload_upgrade_files(firmware_filename)
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, **result}
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Chyba při nahrávání souborů: {e}")
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=500
        )


@app.post("/api/firmware/upgrade")
async def firmware_upgrade(
    req: Request,
    firmware_filename: str = Form(None),
    ezsp_version: str = Form("V7")
):
    """Provede upgrade firmware Zigbee modulu."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            return templates.TemplateResponse(
                "partials/firmware_status.html",
                {"request": req, "status": "error", "message": "SSH není připojeno"},
                status_code=400
            )
        # Ověření, že firmware soubor existuje na serveru
        if firmware_filename:
            try:
                get_file_path(firmware_filename)
            except ValueError:
                return templates.TemplateResponse(
                    "partials/firmware_status.html",
                    {"request": req, "status": "error", "message": f"Firmware soubor {firmware_filename} nebyl nalezen"},
                    status_code=400
                )
        upgrade = FirmwareUpgrade(session)
        result = upgrade.perform_upgrade(ezsp_version)
        # Vyčištění session po rebootu
        session_id = req.session.get("session_id")
        if session_id and session_id in ssh_sessions:
            del ssh_sessions[session_id]
        req.session.pop("ssh_host", None)
        req.session.pop("ssh_port", None)
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, **result}
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Chyba při upgrade firmware: {e}")
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=500
        )


@app.post("/api/firmware/restore-serialgateway")
async def firmware_restore_serialgateway(req: Request):
    """Obnoví serialgateway po upgrade."""
    try:
        session = get_ssh_session(req)
        if not session.is_connected():
            return templates.TemplateResponse(
                "partials/firmware_status.html",
                {"request": req, "status": "error", "message": "SSH není připojeno"},
                status_code=400
            )
        upgrade = FirmwareUpgrade(session)
        result = upgrade.restore_serialgateway()
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, **result}
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Chyba při obnovování serialgateway: {e}")
        return templates.TemplateResponse(
            "partials/firmware_status.html",
            {"request": req, "status": "error", "message": str(e)},
            status_code=500
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
