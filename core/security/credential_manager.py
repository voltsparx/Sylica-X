"""Credential vault wrapper around encrypted credential manager."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import dataclass, field

from core.foundation.credential_manager import CredentialManager
from core.security.encryption import derive_secret_key


@dataclass
class CredentialVault:
    """Secure credential vault with derived key bootstrap."""

    passphrase: str
    _salt: bytes = field(default_factory=bytes)
    _manager: CredentialManager | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        key_bytes, salt = derive_secret_key(self.passphrase, self._salt or None)
        self._salt = salt
        manager_key = urlsafe_b64encode(key_bytes)
        self._manager = CredentialManager(manager_key)

    def store(self, service: str, token: str) -> None:
        """Store encrypted service token."""

        assert self._manager is not None
        self._manager.store_token(service, token)

    def retrieve(self, service: str) -> str | None:
        """Retrieve decrypted service token."""

        assert self._manager is not None
        return self._manager.retrieve_token(service)

    def remove(self, service: str) -> bool:
        """Remove token for a service."""

        assert self._manager is not None
        return self._manager.remove_token(service)

    def services(self) -> list[str]:
        """List all services with stored credentials."""

        assert self._manager is not None
        return self._manager.list_services()
