"""
Pydantic modely pro validaci vstupů a výstupů API.
"""
from pydantic import BaseModel, Field, field_validator
import re


class DecodeRequest(BaseModel):
    """Request model pro dekódování AUSKEY."""
    kek: str = Field(..., description="KEK hex string (jeden řádek)")
    auskey_line1: str = Field(..., description="První řádek encrypted AUSKEY")
    auskey_line2: str = Field(..., description="Druhý řádek encrypted AUSKEY")
    
    @field_validator('kek', 'auskey_line1', 'auskey_line2')
    @classmethod
    def validate_hex(cls, v: str) -> str:
        """Validuje hex string."""
        # Odstranění mezer a tabulátorů
        cleaned = v.replace(" ", "").replace("\t", "")
        # Kontrola hex formátu
        if not re.match(r'^[0-9a-fA-F:]+$', cleaned):
            raise ValueError("Neplatný hex formát")
        return v


class DecodeResponse(BaseModel):
    """Response model pro dekódování AUSKEY."""
    auskey: str
    root_password: str


class SSHConnectRequest(BaseModel):
    """Request model pro SSH připojení."""
    host: str = Field(..., description="IP adresa gateway")
    port: int = Field(22, ge=1, le=65535, description="SSH port")
    password: str = Field(..., description="Root heslo")
    
    @field_validator('host')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validuje IP adresu."""
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, v):
            raise ValueError("Neplatná IP adresa")
        parts = v.split('.')
        if not all(0 <= int(part) <= 255 for part in parts):
            raise ValueError("Neplatná IP adresa")
        return v


class SSHStatusResponse(BaseModel):
    """Response model pro SSH status."""
    connected: bool
    host: str | None = None
    port: int | None = None


class SSHOperationResponse(BaseModel):
    """Response model pro SSH operace."""
    status: str
    message: str


class UploadSerialgatewayRequest(BaseModel):
    """Request model pro nahrání serialgateway.bin."""
    filename: str = Field(..., description="Název souboru z binaries/")
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validuje název souboru."""
        if not v or '..' in v or '/' in v:
            raise ValueError("Neplatný název souboru")
        return v


class SetStaticIPRequest(BaseModel):
    """Request model pro nastavení statické IP."""
    ip: str = Field(..., description="IP adresa")
    
    @field_validator('ip')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validuje IP adresu."""
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, v):
            raise ValueError("Neplatná IP adresa")
        parts = v.split('.')
        if not all(0 <= int(part) <= 255 for part in parts):
            raise ValueError("Neplatná IP adresa")
        return v


class FileListResponse(BaseModel):
    """Response model pro seznam souborů."""
    files: list[str]


class FirmwareUpgradeRequest(BaseModel):
    """Request model pro upgrade firmware."""
    firmware_filename: str = Field(..., description="Název firmware souboru (.gbl)")
    ezsp_version: str = Field("V7", description="EZSP verze (V7 nebo V8)")
    
    @field_validator('firmware_filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validuje název souboru."""
        if not v or '..' in v or '/' in v:
            raise ValueError("Neplatný název souboru")
        if not v.endswith('.gbl'):
            raise ValueError("Firmware soubor musí mít příponu .gbl")
        return v
    
    @field_validator('ezsp_version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validuje EZSP verzi."""
        if v not in ["V7", "V8"]:
            raise ValueError("EZSP verze musí být V7 nebo V8")
        return v
