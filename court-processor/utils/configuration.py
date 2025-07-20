"""
Extracted configuration management from enhanced/config/settings.py
Provides centralized configuration with environment variable support and validation
"""
import os
import warnings
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
import dataclasses
import urllib.parse


@dataclass
class DatabaseConfig:
    """Database configuration with connection management"""
    host: str = "db"
    port: int = 5432
    database: str = "aletheia"
    user: str = "aletheia_user"
    password: str = ""
    schema: str = "public"
    
    # Connection pool settings
    min_connections: int = 1
    max_connections: int = 20
    connection_timeout: int = 30
    
    @property
    def url(self) -> str:
        """Get database URL for connection"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def connection_params(self) -> Dict[str, Any]:
        """Get connection parameters as dictionary"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }
    
    def validate(self) -> List[str]:
        """Validate database configuration"""
        issues = []
        
        if not self.host:
            issues.append("Database host is required")
        
        if not 1 <= self.port <= 65535:
            issues.append("Database port must be between 1 and 65535")
        
        if not self.database:
            issues.append("Database name is required")
        
        if not self.user:
            issues.append("Database user is required")
        
        if not 1 <= self.min_connections <= self.max_connections:
            issues.append("Min connections must be <= max connections")
        
        return issues


@dataclass
class ServiceConfig:
    """External service configuration"""
    # CourtListener API
    courtlistener_api_key: Optional[str] = None
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4"
    courtlistener_timeout: int = 30
    courtlistener_rate_limit: float = 2.0  # requests per second
    
    # Haystack service
    haystack_url: str = "http://haystack-service:8000"
    haystack_timeout: int = 30
    haystack_enabled: bool = True
    
    # Doctor service (for PDF processing)
    doctor_url: str = "http://doctor:5050"
    doctor_timeout: int = 60
    doctor_enabled: bool = True
    
    # Unstructured.io service
    unstructured_url: str = "http://unstructured-service:8880"
    unstructured_timeout: int = 60
    unstructured_enabled: bool = True
    
    # Redis for caching
    redis_url: str = "redis://redis:6379"
    redis_timeout: int = 5
    redis_enabled: bool = False
    
    def validate(self) -> List[str]:
        """Validate service configuration"""
        issues = []
        
        # Validate URLs
        url_fields = [
            ('courtlistener_base_url', self.courtlistener_base_url),
            ('haystack_url', self.haystack_url),
            ('doctor_url', self.doctor_url),
            ('unstructured_url', self.unstructured_url),
            ('redis_url', self.redis_url)
        ]
        
        for field_name, url in url_fields:
            if url and not (url.startswith('http://') or url.startswith('https://') or url.startswith('redis://')):
                issues.append(f"{field_name} must be a valid URL")
        
        # Validate timeouts
        timeout_fields = [
            ('courtlistener_timeout', self.courtlistener_timeout),
            ('haystack_timeout', self.haystack_timeout),
            ('doctor_timeout', self.doctor_timeout),
            ('unstructured_timeout', self.unstructured_timeout),
            ('redis_timeout', self.redis_timeout)
        ]
        
        for field_name, timeout in timeout_fields:
            if not 1 <= timeout <= 300:  # 1 second to 5 minutes
                issues.append(f"{field_name} must be between 1 and 300 seconds")
        
        return issues


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
    retry_exponential_backoff: bool = True
    
    # File processing
    max_file_size_mb: int = 100
    allowed_file_types: List[str] = field(default_factory=lambda: ['.pdf', '.txt', '.html'])
    
    # Processing limits
    max_processing_time_minutes: int = 60
    memory_limit_mb: int = 2048
    
    def validate(self) -> List[str]:
        """Validate processing configuration"""
        issues = []
        
        if not 1 <= self.concurrent_workers <= 50:
            issues.append("Concurrent workers must be between 1 and 50")
        
        if not 1 <= self.default_batch_size <= self.max_batch_size:
            issues.append("Default batch size must be <= max batch size")
        
        if not 0.1 <= self.api_rate_limit <= 100:
            issues.append("API rate limit must be between 0.1 and 100 requests/second")
        
        if not 1 <= self.max_retries <= 10:
            issues.append("Max retries must be between 1 and 10")
        
        if not 0.1 <= self.retry_delay <= 60:
            issues.append("Retry delay must be between 0.1 and 60 seconds")
        
        if not 1 <= self.max_file_size_mb <= 1000:
            issues.append("Max file size must be between 1 and 1000 MB")
        
        return issues


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size_mb: int = 100
    backup_count: int = 5
    console_output: bool = True
    json_format: bool = False
    
    def validate(self) -> List[str]:
        """Validate logging configuration"""
        issues = []
        
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.level.upper() not in valid_levels:
            issues.append(f"Log level must be one of: {', '.join(valid_levels)}")
        
        if not 1 <= self.max_file_size_mb <= 1000:
            issues.append("Max file size must be between 1 and 1000 MB")
        
        if not 1 <= self.backup_count <= 100:
            issues.append("Backup count must be between 1 and 100")
        
        return issues


@dataclass
class SecurityConfig:
    """Security configuration"""
    # API security
    api_key_required: bool = False
    api_key_header: str = "X-API-Key"
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # Rate limiting
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 100
    
    # Data protection
    encrypt_sensitive_data: bool = True
    mask_passwords_in_logs: bool = True
    
    def validate(self) -> List[str]:
        """Validate security configuration"""
        issues = []
        
        if not 1 <= self.rate_limit_per_minute <= 10000:
            issues.append("Rate limit per minute must be between 1 and 10000")
        
        return issues


@dataclass
class Settings:
    """Main configuration settings"""
    # Environment
    environment: str = "development"
    debug: bool = False
    version: str = "1.0.0"
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    services: ServiceConfig = field(default_factory=ServiceConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Paths
    data_directory: str = "./data"
    log_directory: str = "./logs"
    temp_directory: str = "/tmp"
    config_directory: str = "./config"
    
    @classmethod
    def from_environment(cls) -> "Settings":
        """Create settings from environment variables"""
        settings = cls()
        
        # Environment settings
        settings.environment = os.getenv("ENVIRONMENT", "development")
        settings.debug = os.getenv("DEBUG", "false").lower() == "true"
        settings.version = os.getenv("VERSION", "1.0.0")
        
        # Database configuration
        settings._load_database_config()
        
        # Service configuration
        settings._load_service_config()
        
        # Processing configuration
        settings._load_processing_config()
        
        # Logging configuration
        settings._load_logging_config()
        
        # Security configuration
        settings._load_security_config()
        
        # Paths
        settings._load_path_config()
        
        return settings
    
    def _load_database_config(self):
        """Load database configuration from environment"""
        if db_url := os.getenv("DATABASE_URL"):
            # Parse database URL if provided
            parsed = urllib.parse.urlparse(db_url)
            if parsed.scheme == "postgresql":
                self.database.host = parsed.hostname or "localhost"
                self.database.port = parsed.port or 5432
                self.database.database = parsed.path.lstrip("/") or "aletheia"
                self.database.user = parsed.username or "aletheia_user"
                self.database.password = parsed.password or ""
        else:
            # Individual database environment variables
            self.database.host = os.getenv("DB_HOST", "db")
            self.database.port = int(os.getenv("DB_PORT", "5432"))
            self.database.database = os.getenv("DB_NAME", "aletheia")
            self.database.user = os.getenv("DB_USER", "aletheia_user")
            self.database.password = os.getenv("DB_PASSWORD", "")
        
        # Additional database settings
        self.database.schema = os.getenv("DB_SCHEMA", "public")
        self.database.max_connections = int(os.getenv("DB_MAX_CONNECTIONS", "20"))
        self.database.connection_timeout = int(os.getenv("DB_TIMEOUT", "30"))
    
    def _load_service_config(self):
        """Load service configuration from environment"""
        self.services.courtlistener_api_key = os.getenv("COURTLISTENER_API_TOKEN")
        self.services.courtlistener_base_url = os.getenv("COURTLISTENER_URL", self.services.courtlistener_base_url)
        self.services.courtlistener_timeout = int(os.getenv("COURTLISTENER_TIMEOUT", "30"))
        
        self.services.haystack_url = os.getenv("HAYSTACK_URL", "http://haystack-service:8000")
        self.services.haystack_enabled = os.getenv("HAYSTACK_ENABLED", "true").lower() == "true"
        
        self.services.doctor_url = os.getenv("DOCTOR_URL", "http://doctor:5050")
        self.services.doctor_enabled = os.getenv("DOCTOR_ENABLED", "true").lower() == "true"
        
        self.services.unstructured_url = os.getenv("UNSTRUCTURED_URL", "http://unstructured-service:8880")
        self.services.unstructured_enabled = os.getenv("UNSTRUCTURED_ENABLED", "true").lower() == "true"
        
        self.services.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.services.redis_enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
    
    def _load_processing_config(self):
        """Load processing configuration from environment"""
        self.processing.default_batch_size = int(os.getenv("DEFAULT_BATCH_SIZE", "100"))
        self.processing.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "1000"))
        self.processing.concurrent_workers = int(os.getenv("CONCURRENT_WORKERS", "4"))
        
        self.processing.api_rate_limit = float(os.getenv("API_RATE_LIMIT", "2.0"))
        self.processing.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.processing.retry_delay = float(os.getenv("RETRY_DELAY", "1.0"))
        
        self.processing.deduplication_enabled = os.getenv("DEDUPLICATION_ENABLED", "true").lower() == "true"
        self.processing.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    
    def _load_logging_config(self):
        """Load logging configuration from environment"""
        self.logging.level = os.getenv("LOG_LEVEL", "INFO")
        self.logging.file_path = os.getenv("LOG_FILE")
        self.logging.max_file_size_mb = int(os.getenv("LOG_MAX_SIZE_MB", "100"))
        self.logging.backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        self.logging.console_output = os.getenv("LOG_CONSOLE", "true").lower() == "true"
        self.logging.json_format = os.getenv("LOG_JSON", "false").lower() == "true"
    
    def _load_security_config(self):
        """Load security configuration from environment"""
        self.security.api_key_required = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
        self.security.enable_rate_limiting = os.getenv("RATE_LIMITING_ENABLED", "true").lower() == "true"
        self.security.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
        
        # Parse allowed origins
        if origins := os.getenv("ALLOWED_ORIGINS"):
            self.security.allowed_origins = [origin.strip() for origin in origins.split(",")]
    
    def _load_path_config(self):
        """Load path configuration from environment"""
        self.data_directory = os.getenv("DATA_DIRECTORY", "./data")
        self.log_directory = os.getenv("LOG_DIRECTORY", "./logs")
        self.temp_directory = os.getenv("TEMP_DIRECTORY", "/tmp")
        self.config_directory = os.getenv("CONFIG_DIRECTORY", "./config")
    
    def validate(self) -> Dict[str, List[str]]:
        """Validate all configuration and return any issues"""
        all_issues = {}
        
        # Validate individual components
        component_validators = [
            ('database', self.database),
            ('services', self.services),
            ('processing', self.processing),
            ('logging', self.logging),
            ('security', self.security)
        ]
        
        for component_name, component in component_validators:
            if hasattr(component, 'validate'):
                issues = component.validate()
                if issues:
                    all_issues[component_name] = issues
        
        # Global validation
        global_issues = []
        
        # Validate environment-specific requirements
        if self.environment == "production":
            if not self.services.courtlistener_api_key:
                global_issues.append("CourtListener API key required for production")
            
            if self.debug:
                global_issues.append("Debug should not be enabled in production")
        
        # Validate paths
        for path_name, path_value in [
            ("data_directory", self.data_directory),
            ("log_directory", self.log_directory),
            ("temp_directory", self.temp_directory),
            ("config_directory", self.config_directory)
        ]:
            path = Path(path_value)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    global_issues.append(f"Cannot create directory: {path_value}")
        
        if global_issues:
            all_issues['global'] = global_issues
        
        return all_issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return dataclasses.asdict(self)
    
    def get_masked_dict(self) -> Dict[str, Any]:
        """Get settings as dictionary with sensitive data masked"""
        data = self.to_dict()
        
        # Mask sensitive fields
        sensitive_fields = [
            ('database', 'password'),
            ('services', 'courtlistener_api_key'),
        ]
        
        for component, field in sensitive_fields:
            if component in data and field in data[component] and data[component][field]:
                data[component][field] = "***MASKED***"
        
        return data
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"


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
            for component, component_issues in issues.items():
                for issue in component_issues:
                    warnings.warn(f"Configuration issue - {component}: {issue}")
    
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = None
    return get_settings()


def override_settings(**kwargs) -> Settings:
    """Override specific settings (useful for testing)"""
    settings = get_settings()
    
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
        else:
            warnings.warn(f"Unknown setting: {key}")
    
    return settings


def validate_current_settings() -> bool:
    """Validate current settings and log any issues"""
    settings = get_settings()
    issues = settings.validate()
    
    if issues:
        print("Configuration validation issues found:")
        for component, component_issues in issues.items():
            print(f"\n{component.upper()}:")
            for issue in component_issues:
                print(f"  - {issue}")
        return False
    else:
        print("Configuration validation passed")
        return True


# Environment-specific setting helpers

def is_production() -> bool:
    """Check if running in production"""
    return get_settings().is_production()


def is_development() -> bool:
    """Check if running in development"""
    return get_settings().is_development()


def get_database_url() -> str:
    """Get database connection URL"""
    return get_settings().database.url


def get_service_url(service_name: str) -> Optional[str]:
    """Get URL for a specific service"""
    services = get_settings().services
    service_urls = {
        'courtlistener': services.courtlistener_base_url,
        'haystack': services.haystack_url,
        'doctor': services.doctor_url,
        'unstructured': services.unstructured_url,
        'redis': services.redis_url
    }
    
    return service_urls.get(service_name)


def get_processing_limits() -> Dict[str, Any]:
    """Get processing configuration limits"""
    processing = get_settings().processing
    return {
        'max_batch_size': processing.max_batch_size,
        'max_file_size_mb': processing.max_file_size_mb,
        'max_retries': processing.max_retries,
        'concurrent_workers': processing.concurrent_workers
    }


# Configuration templates for different environments

def get_production_template() -> Dict[str, Any]:
    """Get recommended production configuration template"""
    return {
        'environment': 'production',
        'debug': False,
        'database': {
            'max_connections': 50,
            'connection_timeout': 30
        },
        'processing': {
            'concurrent_workers': 8,
            'max_batch_size': 500,
            'api_rate_limit': 1.0
        },
        'logging': {
            'level': 'INFO',
            'json_format': True,
            'console_output': False
        },
        'security': {
            'api_key_required': True,
            'enable_rate_limiting': True,
            'rate_limit_per_minute': 60
        }
    }


def get_development_template() -> Dict[str, Any]:
    """Get recommended development configuration template"""
    return {
        'environment': 'development',
        'debug': True,
        'database': {
            'max_connections': 10,
            'connection_timeout': 30
        },
        'processing': {
            'concurrent_workers': 2,
            'max_batch_size': 50,
            'api_rate_limit': 0.5
        },
        'logging': {
            'level': 'DEBUG',
            'json_format': False,
            'console_output': True
        },
        'security': {
            'api_key_required': False,
            'enable_rate_limiting': False
        }
    }