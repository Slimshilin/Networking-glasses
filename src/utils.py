# src/utils.py

# This file is for shared helper functions, e.g., for configuration management,
# common I/O operations if needed, or other utilities used across modules.

# Example: Configuration loading (can be expanded)
import json
import os

DEFAULT_CONFIG = {
    "TOP_K_RESULTS": 3,
    "USER_BIO": "Dartmouth Computer Science sophomore actively seeking a challenging Software Engineering internship for Summer 2025. Proficient in Python, Java, and C++, with hands-on experience in web development (React, Node.js) through personal projects and coursework. Strong interest in machine learning and data analysis. Eager to contribute to innovative projects and learn from experienced engineers. Active member of the Dartmouth Coding Club, recently collaborated on developing a campus utility mobile application.",
    "PROFILES_JSON_PATH": "data/profile_relevance.json",
    "BASE_PROFILES_JSON_PATH": "data/base_profiles.json",
    "QR_CODES_DIR": "data/qr_codes/",
    "INPUT_IMAGE_PATH": "assets/sample_group.jpg", # Can be a file or a directory
    "OUTPUT_IMAGE_DIR": "assets/annotated_images/", # Changed from OUTPUT_IMAGE_PATH
    "NUM_PROFILES_TO_GENERATE": 20,
    "SAMPLE_IMAGES_DIR": "assets/sample_test_images/",
    "CHAT_MODEL_NAME": "anthropic.claude-3-7-sonnet-20250219"
}

CONFIG_FILE_PATH = "config.json"

def load_config() -> dict:
    """Loads configuration from a JSON file, falling back to defaults."""
    config = DEFAULT_CONFIG.copy() # Start with defaults

    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                user_config = json.load(f)
            
            # Handle transition from OUTPUT_IMAGE_PATH to OUTPUT_IMAGE_DIR
            if "OUTPUT_IMAGE_DIR" not in user_config and "OUTPUT_IMAGE_PATH" in user_config:
                legacy_output_path = user_config.pop("OUTPUT_IMAGE_PATH") # Remove old key
                derived_output_dir = os.path.dirname(legacy_output_path)
                if derived_output_dir: # If it was a path like "dir/file.jpg"
                    user_config["OUTPUT_IMAGE_DIR"] = derived_output_dir
                    print(f"Warning: Legacy key 'OUTPUT_IMAGE_PATH' ('{legacy_output_path}') found in {CONFIG_FILE_PATH}. "
                          f"Using its directory '{derived_output_dir}' for 'OUTPUT_IMAGE_DIR'. "
                          f"Please update {CONFIG_FILE_PATH} to use 'OUTPUT_IMAGE_DIR' directly.")
                else: # If it was like "file.jpg" or empty, dirname is empty. Default OUTPUT_IMAGE_DIR will be used.
                    print(f"Warning: Legacy key 'OUTPUT_IMAGE_PATH' ('{legacy_output_path}') found in {CONFIG_FILE_PATH} "
                          f"could not be reliably converted to a directory. "
                          f"Please set 'OUTPUT_IMAGE_DIR' in {CONFIG_FILE_PATH}.")
            
            config.update(user_config) # Apply user's config over defaults
            print(f"Loaded configuration from {CONFIG_FILE_PATH}")
        except Exception as e:
            print(f"Error loading {CONFIG_FILE_PATH}: {e}. Using default config values where applicable.")
    else:
        print(f"Config file {CONFIG_FILE_PATH} not found. Using default config and creating the file.")
        save_config(config, CONFIG_FILE_PATH) # Save the initial default config
    return config

def save_config(config: dict, path: str = CONFIG_FILE_PATH):
    """Saves the current configuration to a JSON file."""
    try:
        with open(path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Saved configuration to {path}")
    except Exception as e:
        print(f"Error saving config to {path}: {e}")

# Example of how to use it (optional, modules can call load_config() directly)
# current_config = load_config()

if __name__ == '__main__':
    # Test config loading
    print("--- Testing utils.py ---")
    # If config.json exists, delete it to test creation, then restore if needed (manual step for user)
    # For automated test, this section would be more complex.
    # For now, just load and print.
    
    # A simple test: load config and print it.
    # load_config() will create config.json with defaults if it doesn't exist.
    cfg = load_config()
    print("\nLoaded configuration for testing utils.py:")
    for key, value in cfg.items():
        print(f"  {key}: {value}")
    
    # If config.json was just created, this message is useful.
    if not os.path.exists(CONFIG_FILE_PATH): # This check is a bit late as load_config creates it.
                                           # It's more to inform the user that it *would have been* created.
        print(f"Note: {CONFIG_FILE_PATH} would have been created with default values if it was missing.")
    else:
        print(f"Found {CONFIG_FILE_PATH}. Values above are from this file, merged with defaults.")
    print("--- utils.py test finished ---")
