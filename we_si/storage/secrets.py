"""
Secure API key encryption and storage utilities.
"""
import os
from cryptography.fernet import Fernet
from typing import Optional


class SecretManager:
    """
    Manages encryption and decryption of API keys using Fernet.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the secret manager.
        
        Args:
            encryption_key: Base64-encoded Fernet key. If not provided, 
                          will try to load from WESI_ENCRYPTION_KEY env var.
        
        Raises:
            ValueError: If no encryption key is provided or found
        """
        if encryption_key is None:
            encryption_key = os.environ.get('WESI_ENCRYPTION_KEY')
        
        if not encryption_key:
            raise ValueError(
                "No encryption key provided. Set WESI_ENCRYPTION_KEY environment variable "
                "or provide encryption_key parameter. Generate a key with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")
    
    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted bytes
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        return self.cipher.encrypt(plaintext.encode())
    
    def decrypt(self, ciphertext: bytes) -> str:
        """
        Decrypt ciphertext back to plaintext.
        
        Args:
            ciphertext: Encrypted bytes
            
        Returns:
            Decrypted string
            
        Raises:
            ValueError: If decryption fails
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty ciphertext")
        
        try:
            return self.cipher.decrypt(ciphertext).decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            Base64-encoded encryption key as string
        """
        return Fernet.generate_key().decode()


def store_api_key(session, user_id: int, service: str, api_key: str, secret_manager: SecretManager):
    """
    Store an encrypted API key for a user.
    
    Args:
        session: SQLAlchemy session
        user_id: User ID
        service: Service name (e.g., 'openai', 'google')
        api_key: Plaintext API key
        secret_manager: SecretManager instance
        
    Returns:
        APIKey model instance
    """
    from we_si.models import APIKey
    
    # Encrypt the key
    encrypted_key = secret_manager.encrypt(api_key)
    
    # Check if key already exists for this user and service
    existing_key = session.query(APIKey).filter_by(
        user_id=user_id,
        service=service
    ).first()
    
    if existing_key:
        # Update existing key
        existing_key.encrypted_key = encrypted_key
        session.commit()
        return existing_key
    else:
        # Create new key
        new_key = APIKey(
            user_id=user_id,
            service=service,
            encrypted_key=encrypted_key
        )
        session.add(new_key)
        session.commit()
        return new_key


def get_api_key(session, user_id: int, service: str, secret_manager: SecretManager) -> Optional[str]:
    """
    Retrieve and decrypt an API key for a user.
    
    Args:
        session: SQLAlchemy session
        user_id: User ID
        service: Service name
        secret_manager: SecretManager instance
        
    Returns:
        Decrypted API key or None if not found
    """
    from we_si.models import APIKey
    
    key_record = session.query(APIKey).filter_by(
        user_id=user_id,
        service=service
    ).first()
    
    if not key_record:
        return None
    
    try:
        return secret_manager.decrypt(key_record.encrypted_key)
    except ValueError:
        # Decryption failed - key may be corrupt
        return None


def delete_api_key(session, user_id: int, service: str) -> bool:
    """
    Delete an API key for a user.
    
    Args:
        session: SQLAlchemy session
        user_id: User ID
        service: Service name
        
    Returns:
        True if key was deleted, False if not found
    """
    from we_si.models import APIKey
    
    key_record = session.query(APIKey).filter_by(
        user_id=user_id,
        service=service
    ).first()
    
    if key_record:
        session.delete(key_record)
        session.commit()
        return True
    
    return False


def list_api_key_services(session, user_id: int) -> list:
    """
    List all services that have API keys stored for a user.
    
    Args:
        session: SQLAlchemy session
        user_id: User ID
        
    Returns:
        List of service names
    """
    from we_si.models import APIKey
    
    keys = session.query(APIKey).filter_by(user_id=user_id).all()
    return [key.service for key in keys]
