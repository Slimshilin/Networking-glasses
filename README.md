# Networking Glasses MVP

This project is a prototype for a "Networking Glasses" system. It processes static images containing QR codes, where each QR code represents an individual. The system identifies these individuals, retrieves their professional profiles (which include pre-calculated relevance scores and explanations), and then annotates the original image to highlight the most relevant people according to a predefined user persona (e.g., an event organizer).

## Key Features

*   **AI-Powered Data Generation**:
    *   Generates diverse professional profiles (e.g., students of various levels, recruiters, employees, alumni, professors) using a Chat API. The theme for profile generation is configurable (e.g., attendees of a career fair).
    *   Calculates relevance scores (0.0 to 1.0) and textual explanations for these profiles against a configurable system user bio using the Chat API. This relevance is pre-calculated and stored.
*   **Custom Sample Image Creation**:
    *   Utilizes user-provided photos of individuals (from `data/photos/`).
    *   Pairs each photo with a QR code (generated from profile IDs).
    *   Creates "person units" (photo with QR code overlaid).
    *   Arranges multiple such units onto a larger canvas to simulate group scenes for testing, with logic to avoid overlap of these units.
*   **QR Code Detection**: Employs `pyzbar` and `OpenCV` to detect and decode QR codes from input images.
*   **Relevance-Based Profile Ranking**: Ranks individuals identified via QR codes based on their pre-calculated relevance scores stored in `data/profile_relevance.json`.
*   **Rich Image Annotation**:
    *   Draws bounding boxes around detected QR codes. The box color dynamically changes (Red, Yellow, Green) based on the profile's relevance score.
    *   Displays detailed information next to the QR code: the person's name, relevance score, and their complete professional bio.
    *   Implements text wrapping and an intelligent placement strategy for annotations to minimize overlaps with other annotations and QR codes.
*   **Batch Image Processing**: The main application can process a single specified image or all images found within a designated directory.
*   **Configuration-Driven**: Core parameters, including API model details, system user bio, file paths, and generation quantities, are managed through a `config.json` file.

## Project Structure

```
Networking-glasses/
├── .git/                     # Git version control files (if applicable)
├── .gitignore                # Specifies intentionally untracked files for Git
├── assets/
│   ├── annotated_images/     # Output directory for images annotated by main.py
│   └── sample_test_images/   # Output directory for generated sample images from create_sample_images.py
├── data/
│   ├── base_profiles.json    # AI-generated core profiles (ID, name, title, bio)
│   ├── photos/               # **USER-PROVIDED**: Directory for individual photos (e.g., person1.jpg)
│   ├── profile_relevance.json# Profiles with AI-calculated relevance scores and explanations
│   └── qr_codes/             # Directory containing QR code images (PNGs) for each profile ID
├── src/
│   ├── __pycache__/          # Python bytecode cache
│   ├── annotate_image.py     # Handles drawing annotations on images
│   ├── create_sample_images.py# Generates sample scene images from person photos and QR codes
│   ├── detect_qr.py          # Detects and decodes QR codes from images
│   ├── main.py               # Main application script to run the full pipeline
│   ├── prepare_data.py       # Script for all data preparation steps (profile generation, QR generation, relevance scoring)
│   ├── score_relevance.py    # Loads profiles and ranks them based on pre-calculated relevance
│   └── utils.py              # Utility functions, primarily for loading/saving config.json
├── config.json               # Configuration file (auto-generated on first run if missing)
├── LICENSE                   # Project license file (if applicable)
├── README.md                 # This file
└── requirements.txt          # Python dependencies
```
*(Note: An `assets/sample_group.jpg` might exist if `config.json` points to it by default, but the primary workflow uses images from `assets/sample_test_images/` or user-specified paths.)*

## Setup

1.  **Clone the Repository** (if you haven't already):
    ```bash
    git clone <repository_url>
    cd Networking-glasses
    ```

2.  **Python Environment**:
    A Python version of 3.9 or newer is recommended.
    Create a conda environment
    ```bash
    conda create -n network-glasses python=3.9
    conda activate network-glasses
    ```

3.  **Install Dependencies**:
    Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    For `pyzbar` (QR code detection), additional system libraries might be needed:
    ```bash
    # On Debian/Ubuntu Linux:
    sudo apt-get update && sudo apt-get install -y libzbar0 zbar-tools
    # On macOS (using Homebrew):
    # brew install zbar
    ```

4.  **Set Dartmouth Chat API Key**:
    The `src/prepare_data.py` script relies on a Chat API (like Dartmouth's) for generating profile content and relevance scores. This requires an API key. Set it as an environment variable:
    ```bash
    export DARTMOUTH_CHAT_API_KEY="your_actual_api_key_here"
    ```
    To make this setting persistent across terminal sessions, add the line to your shell's configuration file (e.g., `~/.bashrc`, `~/.zshrc`, or your Conda environment activation script). If this key isn't set, `prepare_data.py` will attempt to run but will likely use placeholder data for AI-generated content.

5.  **Populate `data/photos/` Directory**:
    The `src/create_sample_images.py` script needs source images of individuals to generate realistic test scenes.
    *   Ensure the `data/photos/` directory exists (create it if not).
    *   Add several `.jpg` or `.png` images of different people to this directory. These will be combined with QR codes.

6.  **Review Configuration (`config.json`)**:
    A `config.json` file will be automatically generated in the project root with default values the first time you run `src/prepare_data.py` or `src/main.py`.
    It's crucial to review and customize this file. Key parameters include:
    *   `USER_BIO`: The detailed bio of the system's user persona (e.g., an event organizer looking for specific types of people). This bio is used by the Chat API in `prepare_data.py` to calculate relevance scores.
    *   `CHAT_MODEL_NAME`: The specific model identifier for the Chat API (e.g., `"anthropic.claude-3-7-sonnet-20250219"`). Ensure this is compatible with your API provider.
    *   `NUM_PROFILES_TO_GENERATE`: The number of distinct professional profiles to generate.
    *   `INPUT_IMAGE_PATH`: For `main.py`, this can be a path to a single image file or a directory containing multiple images to process.
    *   `OUTPUT_IMAGE_DIR`: Specifies the directory where `main.py` will save the annotated images.
    *   Other paths: `PROFILES_JSON_PATH`, `BASE_PROFILES_JSON_PATH`, `QR_CODES_DIR`, `SAMPLE_IMAGES_DIR`.

## Usage Workflow

All commands should be executed from the root directory of the `Networking-glasses` project.

**Step 1: Prepare All Necessary Data**
This is the first and most crucial step. It generates profiles, QR codes, and relevance scores.
```bash
python src/prepare_data.py
```
This script performs the following sequence:
1.  **Generates Base Profiles**: Creates `NUM_PROFILES_TO_GENERATE` unique professional profiles using the Chat API. The profiles are designed based on a theme (e.g., "students and recent graduates attending a career fair for tech and finance internships") and include diverse roles. Results are saved to `data/base_profiles.json`.
2.  **Generates QR Codes**: For each profile in `data/base_profiles.json`, a unique QR code encoding the profile's ID is generated and saved as a PNG image in the `data/qr_codes/` directory.
3.  **Calculates Relevance**: Sends the `USER_BIO` (from `config.json`) and all generated base profiles to the Chat API. The API evaluates each profile's relevance to the `USER_BIO` and provides a numerical score (0.0-1.0) and a textual explanation.
4.  **Merges and Saves Final Data**: Combines the base profile information with the AI-generated relevance scores and explanations. The final, complete dataset is saved to `data/profile_relevance.json`.
    *   Progress bars (`tqdm`) will show the status of different generation and API interaction stages.
    *   If the `DARTMOUTH_CHAT_API_KEY` is missing or API calls fail, the script will use placeholder data for relevance.

**Step 2: Create Sample Test Images (Optional but Recommended)**
This script generates composite images that simulate real-world scenarios with multiple people (and their QR codes).
```bash
python src/create_sample_images.py
```
This script will:
1.  Check for photos in `data/photos/` and QR codes in `data/qr_codes/`.
2.  Create a set number of sample images (defined by `NUM_SAMPLE_IMAGES_TO_CREATE` in the script). For each image:
    *   It randomly selects a number of "persons" (e.g., 2-6, configurable within the script).
    *   For each selected person, it randomly pairs a photo from `data/photos/` with a QR code from `data/qr_codes/`.
    *   The person's photo is appropriately scaled, and their QR code is overlaid on the bottom half, creating a "person unit".
    *   These "person units" are then arranged on a new, larger canvas, with logic to avoid overlaps between units.
3.  The resulting composite images (e.g., `sample_image_1.png`) are saved to the directory specified by `SAMPLE_IMAGES_DIR` in `config.json` (default: `assets/sample_test_images/`).

**Step 3: Run the Main Processing and Annotation Pipeline**
This script takes an input image (or images), detects QR codes, looks up profiles, and generates annotated output images.
```bash
python src/main.py
```
The `main.py` script will:
1.  Verify that essential data files (`data/profile_relevance.json`) and image directories (e.g., `assets/sample_test_images/` if used as fallback) exist. It will provide guidance if data is missing.
2.  Determine the input image(s) to process based on `INPUT_IMAGE_PATH` in `config.json`:
    *   If it's a path to a single file, only that image is processed.
    *   If it's a path to a directory, all images within that directory are processed.
    *   If `INPUT_IMAGE_PATH` is invalid or not specified, it defaults to processing all images in the `SAMPLE_IMAGES_DIR` (e.g. `assets/sample_test_images/`).
3.  For each selected input image:
    *   **Detect QR Codes**: Identifies all QR codes in the image and extracts their encoded IDs.
    *   **Load Profiles**: Loads the complete profile data (including names, bios, and pre-calculated relevance scores/explanations) from `data/profile_relevance.json`.
    *   **Rank Profiles**: Ranks the detected individuals based on their relevance scores.
    *   **Annotate Image**: Creates an annotated version of the input image. For the top-ranked individuals:
        *   Bounding boxes are drawn around their QR codes, with colors (green, yellow, red) indicating relevance.
        *   Their name, relevance score, and full bio are displayed as text, with attempts to avoid visual clutter and overlap.
    *   **Save Output**: Saves the annotated image to the directory specified by `OUTPUT_IMAGE_DIR` in `config.json` (default: `assets/annotated_images/`), with a filename like `annotated_<original_filename>.png`.

## Script-by-Script Functional Overview

*   **`src/utils.py`**: Handles loading and saving of the `config.json` file, providing configuration settings to other modules.
*   **`src/prepare_data.py`**: The primary data generation script. It orchestrates AI-based profile creation, QR code image generation, and AI-based relevance assessment.
*   **`src/create_sample_images.py`**: Constructs complex sample scene images by combining user-provided photos with generated QR codes, arranging them on a canvas.
*   **`src/detect_qr.py`**: Contains functions to load an image and use `pyzbar` to find and decode all QR codes within it.
*   **`src/score_relevance.py`**: Loads profiles from `data/profile_relevance.json` and ranks a given list of detected profile IDs based on their stored relevance scores.
*   **`src/annotate_image.py`**: Responsible for all visual annotations on the output image, including drawing QR boxes, text (name, score, bio), handling text wrapping, and managing annotation placement to reduce overlap.
*   **`src/main.py`**: The main executable for the application. It ties together detection, scoring, and annotation for one or more input images.

## Important Notes

*   The effectiveness of the AI-generated profiles and relevance scoring is highly dependent on the quality of the prompts provided to the Chat API, the capabilities of the specified `CHAT_MODEL_NAME`, and the detail and clarity of the `USER_BIO` in `config.json`.
*   A valid `DARTMOUTH_CHAT_API_KEY` (or equivalent for your chosen API) is essential for the full functionality of `src/prepare_data.py`. Without it, AI-driven content generation and relevance scoring will use placeholders or fail.
*   Users **must** provide their own images in the `data/photos/` directory for the `src/create_sample_images.py` script to function correctly.
*   The application is designed for offline processing of static images. It does not involve real-time video processing.