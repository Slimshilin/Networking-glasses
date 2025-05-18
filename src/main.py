import os
import glob # For finding sample images
from typing import Optional, List # Import Optional and List for Python 3.9 compatibility
from src.utils import load_config
from src.detect_qr import detect_qr_codes
from src.score_relevance import load_profiles as load_profiles_for_scoring, rank_profiles # get_user_embedding removed
from src.annotate_image import annotate_image

# Load configuration
config = load_config()

PROFILES_JSON_PATH = config.get("PROFILES_JSON_PATH") # Should be data/profile_relevance.json
# QR_CODES_DIR = config.get("QR_CODES_DIR") # Not directly used by main processing pipeline anymore
CONFIG_INPUT_IMAGE_PATH = config.get("INPUT_IMAGE_PATH") # Path from config
SAMPLE_IMAGES_DIR = config.get("SAMPLE_IMAGES_DIR") # assets/sample_test_images/
OUTPUT_IMAGE_DIR = config.get("OUTPUT_IMAGE_DIR") # Updated from OUTPUT_IMAGE_PATH
TOP_K_RESULTS = config.get("TOP_K_RESULTS", 3)
# USER_BIO_FOR_MAIN = config.get("USER_BIO") # User bio for main is no longer needed for scoring
# NUM_PROFILES_TO_GENERATE = config.get("NUM_PROFILES_TO_GENERATE", 20) # Not for main.py anymore

def check_required_data_exists():
    """Checks if essential data files and directories exist, guides user if not."""
    data_ok = True
    if not PROFILES_JSON_PATH or not os.path.exists(PROFILES_JSON_PATH) or os.path.getsize(PROFILES_JSON_PATH) == 0:
        print(f"Error: Profiles data file ('{PROFILES_JSON_PATH}') not found or is empty.")
        print(f"Please run: python src/prepare_data.py")
        data_ok = False
    
    if not SAMPLE_IMAGES_DIR or not os.path.exists(SAMPLE_IMAGES_DIR) or not os.listdir(SAMPLE_IMAGES_DIR):
        print(f"Error: Sample images directory ('{SAMPLE_IMAGES_DIR}') not found or is empty.")
        print(f"Please run: python src/create_sample_images.py")
        data_ok = False
    else:
        # Check if there are actual image files
        image_files = glob.glob(os.path.join(SAMPLE_IMAGES_DIR, "*.png")) + \
                      glob.glob(os.path.join(SAMPLE_IMAGES_DIR, "*.jpg")) + \
                      glob.glob(os.path.join(SAMPLE_IMAGES_DIR, "*.jpeg"))
        if not image_files:
            print(f"Error: No images (.png, .jpg, .jpeg) found in sample images directory ('{SAMPLE_IMAGES_DIR}').")
            print(f"Please run: python src/create_sample_images.py")
            data_ok = False
            
    return data_ok

def get_input_image_paths() -> List[str]: # Renamed and changed return type
    """Determines the input image paths to use. 
    Returns a list of image paths.
    Priority:
    1. Configured INPUT_IMAGE_PATH (if it's a file).
    2. All images in INPUT_IMAGE_PATH (if it's a directory).
    3. All images in SAMPLE_IMAGES_DIR (if INPUT_IMAGE_PATH is not set/valid).
    """
    image_paths: List[str] = []
    image_extensions = ("*.png", "*.jpg", "*.jpeg")

    # 1. Try the path from config.json
    if CONFIG_INPUT_IMAGE_PATH:
        if os.path.isfile(CONFIG_INPUT_IMAGE_PATH):
            print(f"Using specific input image from config: {CONFIG_INPUT_IMAGE_PATH}")
            image_paths.append(CONFIG_INPUT_IMAGE_PATH)
            return image_paths
        elif os.path.isdir(CONFIG_INPUT_IMAGE_PATH):
            print(f"Using input directory from config: {CONFIG_INPUT_IMAGE_PATH}")
            for ext in image_extensions:
                image_paths.extend(glob.glob(os.path.join(CONFIG_INPUT_IMAGE_PATH, ext)))
            if image_paths:
                print(f"Found {len(image_paths)} images in {CONFIG_INPUT_IMAGE_PATH}.")
                return sorted(image_paths)
            else:
                print(f"Warning: No images found in configured directory: {CONFIG_INPUT_IMAGE_PATH}")
        else:
            print(f"Warning: Input path '{CONFIG_INPUT_IMAGE_PATH}' from config is not a valid file or directory.")

    # 2. If not found or not specified as a valid file/directory, try SAMPLE_IMAGES_DIR
    if not image_paths and SAMPLE_IMAGES_DIR and os.path.exists(SAMPLE_IMAGES_DIR):
        print(f"Searching for images in default sample directory: {SAMPLE_IMAGES_DIR}")
        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(SAMPLE_IMAGES_DIR, ext)))
        
        if image_paths:
            print(f"Found {len(image_paths)} images in {SAMPLE_IMAGES_DIR}.")
            return sorted(image_paths)
    
    if not image_paths:
        print(f"Error: No valid input images found.")
        print(f"Checked config path: '{CONFIG_INPUT_IMAGE_PATH}'")
        print(f"Checked sample directory: '{SAMPLE_IMAGES_DIR}'")
    return []

def run_image_processing_pipeline(input_image: str, output_image: str):
    """Runs the main image processing pipeline: detect, score, annotate."""
    print(f"--- Running Image Processing Pipeline for {input_image} ---")

    # 1. Detect QR Codes
    print("Step 1: Detecting QR codes...")
    detections = detect_qr_codes(input_image)
    if not detections:
        print(f"No QR codes detected in {input_image}. Exiting pipeline.")
        return
    print(f"Detected {len(detections)} QR codes.")
    detected_ids = [det["id"] for det in detections]

    # 2. Load Profiles Data (with pre-calculated relevance)
    print("\nStep 2: Loading profiles data...")
    all_profiles_data = load_profiles_for_scoring(PROFILES_JSON_PATH)
    if not all_profiles_data:
        print(f"No profiles data loaded from {PROFILES_JSON_PATH}. Ensure profiles exist. Exiting pipeline.")
        return
    print(f"Loaded {len(all_profiles_data)} profiles from store.")

    # 3. Get User Embedding - REMOVED (relevance is pre-calculated)
    # print("\nStep 3: Getting user embedding...")
    # user_embedding = get_user_embedding(user_bio) # user_bio no longer needed here for scoring
    # if not user_embedding:
    #     print("Warning: Could not get user embedding. Ranking might not be effective.")

    # 4. Rank Profiles (using pre-calculated relevance)
    print("\nStep 3: Ranking detected profiles...") # Step number adjusted
    ranked_results = rank_profiles(detected_ids, all_profiles_data, TOP_K_RESULTS)
    if not ranked_results:
        print("No profiles were ranked. This could be due to no matching IDs, missing relevance scores, or other issues.")
    else:
        print(f"Top {len(ranked_results)} ranked profiles:")
        for r_id, r_score in ranked_results:
            profile_details = all_profiles_data.get(r_id, {})
            profile_name = profile_details.get("name", "Unknown")
            explanation = profile_details.get("relevance_explanation", "N/A")
            print(f"  ID: {r_id}, Name: {profile_name}, Score: {r_score:.2f}")
            print(f"    Explanation: {explanation}")

    # 5. Annotate Image
    if ranked_results:
        print("\nStep 4: Annotating image with ranked profiles...") # Step number adjusted
        annotate_image(
            input_image_path=input_image,
            output_image_path=output_image,
            ranked_profiles=ranked_results, 
            all_detections=detections,    
            profiles_data=all_profiles_data
        )
    else:
        print("\nSkipping image annotation as no profiles were ranked.")

    print(f"--- Image Processing Pipeline Completed. Check {output_image} if annotations were made ---")

if __name__ == "__main__":
    print("--- Networking Glasses MVP Application ---")
    # Check if necessary data files exist before proceeding
    if not check_required_data_exists():
        print("\nEssential data missing. Please run the data preparation scripts as instructed above.")
        print("Exiting application.")
        exit()
    
    input_images_to_process = get_input_image_paths()
    
    if not input_images_to_process:
        print("\nCould not determine any input images to process. Exiting application.")
        exit()

    # Ensure output directory exists
    if OUTPUT_IMAGE_DIR:
        os.makedirs(OUTPUT_IMAGE_DIR, exist_ok=True)
        print(f"Annotated images will be saved to: {OUTPUT_IMAGE_DIR}")
    else:
        print("Error: OUTPUT_IMAGE_DIR is not defined in config. Cannot save annotated images.")
        exit()

    print(f"\nFound {len(input_images_to_process)} image(s) to process.")

    for input_image_path in input_images_to_process:
        print(f"\nStarting image processing for: {input_image_path}")
        
        img_name, img_ext = os.path.splitext(os.path.basename(input_image_path))
        # Ensure OUTPUT_IMAGE_DIR is used for the output path construction
        final_output_image_path = os.path.join(OUTPUT_IMAGE_DIR, f"annotated_{img_name}{img_ext}")
        
        run_image_processing_pipeline(
            input_image=input_image_path, 
            output_image=final_output_image_path
        )

    print(f"\nApplication finished. Processed {len(input_images_to_process)} image(s).") 