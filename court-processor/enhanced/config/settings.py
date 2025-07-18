"""
Configuration settings for enhanced court document processor

Provides centralized configuration management with environment variable
support, validation, and defaults.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "db"
    port: int = 5432
    database: str = "aletheia"
    user: str = "aletheia"
    password: str = "aletheia123"
    
    @property
    def url(self) -> str:
        """Get database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class ServiceConfig:
    """External service configuration"""
    # Doctor service
    doctor_url: str = "http://doctor-judicial:5050"
    doctor_timeout: int = 60
    doctor_enabled: bool = True
    
    # CourtListener API
    courtlistener_api_key: Optional[str] = None
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4"
    courtlistener_timeout: int = 30
    
    # Haystack service
    haystack_url: str = "http://haystack-judicial:8000"
    haystack_timeout: int = 30
    
    # Unstructured.io service
    unstructured_url: str = "http://unstructured-service:8880"
    unstructured_timeout: int = 60


@dataclass
class ProcessingConfig:
    """Document processing configuration"""
    # Batch processing
    default_batch_size: int = 100
    max_batch_size: int = 1000
    concurrent_workers: int = 4
    
    # Rate limiting
    api_rate_limit: float = 2.0  # requests per second
    
    # Deduplication
    deduplication_enabled: bool = True
    deduplication_cache_size: int = 10000
    
    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # File processing
    max_file_size_mb: int = 100
    allowed_file_types: list = field(default_factory=lambda: ['.pdf', '.txt', '.html'])


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size_mb: int = 100
    backup_count: int = 5


@dataclass
class Settings:
    """Main configuration settings"""
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    services: ServiceConfig = field(default_factory=ServiceConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Paths
    data_directory: str = "./data"
    log_directory: str = "./logs"
    temp_directory: str = "/tmp"
    
    @classmethod
    def from_environment(cls) -> "Settings":
        """Create settings from environment variables"""
        settings = cls()
        
        # Environment settings
        settings.environment = os.getenv("ENVIRONMENT", "development")
        settings.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Database configuration
        if db_url := os.getenv("DATABASE_URL"):
            # Parse database URL if provided
            # postgresql://user:password@host:port/database
            import urllib.parse
            parsed = urllib.parse.urlparse(db_url)
            if parsed.scheme == "postgresql":
                settings.database.host = parsed.hostname or "localhost"
                settings.database.port = parsed.port or 5432
                settings.database.database = parsed.path.lstrip("/") or "aletheia"
                settings.database.user = parsed.username or "aletheia"
                settings.database.password = parsed.password or "aletheia123"
        else:
            # Individual database environment variables
            settings.database.host = os.getenv("DB_HOST", "db")
            settings.database.port = int(os.getenv("DB_PORT", "5432"))
            settings.database.database = os.getenv("DB_NAME", "aletheia")
            settings.database.user = os.getenv("DB_USER", "aletheia")
            settings.database.password = os.getenv("DB_PASSWORD", "aletheia123")
        
        # Service configuration
        settings.services.doctor_url = os.getenv("DOCTOR_URL", "http://doctor-judicial:5050")
        settings.services.doctor_enabled = os.getenv("DOCTOR_ENABLED", "true").lower() == "true"
        settings.services.courtlistener_api_key = os.getenv("COURTLISTENER_API_TOKEN")
        settings.services.haystack_url = os.getenv("HAYSTACK_URL", "http://haystack-judicial:8000")
        settings.services.unstructured_url = os.getenv("UNSTRUCTURED_URL", "http://unstructured-service:8880")
        
        # Processing configuration
        settings.processing.default_batch_size = int(os.getenv("DEFAULT_BATCH_SIZE", "100"))
        settings.processing.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "1000"))
        settings.processing.concurrent_workers = int(os.getenv("CONCURRENT_WORKERS", "4"))
        
        # Logging configuration
        settings.logging.level = os.getenv("LOG_LEVEL", "INFO")
        settings.logging.file_path = os.getenv("LOG_FILE")
        
        # Paths
        settings.data_directory = os.getenv("DATA_DIRECTORY", "./data")
        settings.log_directory = os.getenv("LOG_DIRECTORY", "./logs")
        settings.temp_directory = os.getenv("TEMP_DIRECTORY", "/tmp")
        
        return settings
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return any issues"""
        issues = {}
        
        # Validate required API key for production
        if self.environment == "production":
            if not self.services.courtlistener_api_key:
                issues["courtlistener_api_key"] = "Required for production environment"
        
        # Validate paths exist
        for path_name, path_value in [
            ("data_directory", self.data_directory),
            ("log_directory", self.log_directory),
            ("temp_directory", self.temp_directory)
        ]:
            path = Path(path_value)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    issues[path_name] = f"Cannot create directory: {path_value}"
        
        # Validate numeric ranges
        if not 1 <= self.processing.concurrent_workers <= 50:
            issues["concurrent_workers"] = "Must be between 1 and 50"
        
        if not 1 <= self.processing.default_batch_size <= self.processing.max_batch_size:
            issues["batch_size"] = "Default batch size must be <= max batch size"
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        import dataclasses
        return dataclasses.asdict(self)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings.from_environment()
        
        # Validate settings
        issues = _settings.validate()
        if issues:
            import warnings
            for key, issue in issues.items():
                warnings.warn(f"Configuration issue - {key}: {issue}")
    
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = None
    return get_settings()