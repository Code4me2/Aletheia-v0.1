"""
Environment management for enhanced court document processor

Handles environment-specific configurations and feature flags.
"""
import os
from enum import Enum
from typing import Dict, Any, Optional


class EnvironmentType(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Environment:
    """Environment configuration manager"""
    
    def __init__(self, env_type: Optional[str] = None):
        self.env_type = EnvironmentType(env_type or os.getenv("ENVIRONMENT", "development"))
        self._feature_flags = self._load_feature_flags()
    
    def _load_feature_flags(self) -> Dict[str, bool]:
        """Load feature flags based on environment"""
        base_flags = {
            # Enhanced processing features
            "enhanced_flp_integration": True,
            "doctor_service_integration": True,
            "advanced_deduplication": True,
            "performance_monitoring": True,
            
            # Experimental features
            "concurrent_processing": self.env_type != EnvironmentType.PRODUCTION,
            "advanced_caching": True,
            "detailed_logging": self.env_type in [EnvironmentType.DEVELOPMENT, EnvironmentType.TESTING],
            
            # Service integrations
            "haystack_integration": True,
            "unstructured_integration": True,
            
            # Security features
            "api_authentication": self.env_type == EnvironmentType.PRODUCTION,
            "request_validation": True,
            "rate_limiting": self.env_type == EnvironmentType.PRODUCTION,
        }
        
        # Override with environment variables
        for flag_name in base_flags.keys():
            env_var = f"FEATURE_{flag_name.upper()}"
            if env_value := os.getenv(env_var):
                base_flags[flag_name] = env_value.lower() == "true"
        
        return base_flags
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self._feature_flags.get(feature_name, False)
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get all feature flags"""
        return self._feature_flags.copy()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.env_type == EnvironmentType.DEVELOPMENT
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.env_type == EnvironmentType.TESTING
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.env_type == EnvironmentType.STAGING
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.env_type == EnvironmentType.PRODUCTION
    
    def get_service_config(self) -> Dict[str, Any]:
        """Get environment-specific service configuration"""
        if self.is_production:
            return {
                "timeouts": {
                    "doctor": 120,
                    "courtlistener": 60,
                    "haystack": 60,
                    "unstructured": 120,
                },
                "retries": {
                    "max_attempts": 5,
                    "backoff_factor": 2.0,
                },
                "security": {
                    "verify_ssl": True,
                    "require_auth": True,
                },
            }
        elif self.is_staging:
            return {
                "timeouts": {
                    "doctor": 90,
                    "courtlistener": 45,
                    "haystack": 45,
                    "unstructured": 90,
                },
                "retries": {
                    "max_attempts": 3,
                    "backoff_factor": 1.5,
                },
                "security": {
                    "verify_ssl": True,
                    "require_auth": False,
                },
            }
        else:  # development/testing
            return {
                "timeouts": {
                    "doctor": 30,
                    "courtlistener": 15,
                    "haystack": 15,
                    "unstructured": 30,
                },
                "retries": {
                    "max_attempts": 2,
                    "backoff_factor": 1.0,
                },
                "security": {
                    "verify_ssl": False,
                    "require_auth": False,
                },
            }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get environment-specific logging configuration"""
        base_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": "INFO",
                },
            },
            "loggers": {
                "enhanced": {
                    "handlers": ["console"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "root": {
                "level": "WARNING",
                "handlers": ["console"],
            },
        }
        
        if self.is_development or self.is_testing:
            # More verbose logging for development
            base_config["handlers"]["console"]["formatter"] = "detailed"
            base_config["loggers"]["enhanced"]["level"] = "DEBUG"
            base_config["root"]["level"] = "INFO"
        
        if self.is_production:
            # Add file logging for production
            base_config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "/logs/enhanced_processor.log",
                "maxBytes": 100 * 1024 * 1024,  # 100MB
                "backupCount": 5,
                "formatter": "standard",
                "level": "INFO",
            }
            base_config["loggers"]["enhanced"]["handlers"].append("file")
        
        return base_config