from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General Settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Example service specific setting - uncomment and modify as needed
    # example_setting: str = Field(default="default_value", alias="EXAMPLE_SETTING")
    # another_api_key: str = Field(default=None, alias="ANOTHER_API_KEY")


# Instantiate settings early to catch configuration errors at startup
settings = Settings()

# Example usage (can be removed or kept for quick testing):
if __name__ == "__main__":
    print("Loaded settings:")
    print(f"  Log Level: {settings.log_level}")
    # Example: print(f"  Example Setting: {settings.example_setting}")
    # Example:
    # if settings.another_api_key:
    #     print(f"  Another API Key: {'*' * len(settings.another_api_key)}")
    print("\nModify this file (src/core/config.py) and your .env file to add your project's specific configurations.")
