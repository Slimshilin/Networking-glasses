import os
import random
from PIL import Image, ImageOps # Pillow for image manipulation, ImageOps for padding
from src.utils import load_config
from typing import List, Optional, Tuple

# --- Configuration for Sample Image Generation ---
PHOTOS_DIR = "data/photos/"
QR_CODES_DIR_CONFIG_KEY = "QR_CODES_DIR" # Key to get QR codes directory from main config
SAMPLE_IMAGES_OUTPUT_DIR_CONFIG_KEY = "SAMPLE_IMAGES_DIR" # Key for output dir from main config

NEW_CANVAS_WIDTH = 1200
NEW_CANVAS_HEIGHT = 700
CANVAS_BG_COLOR = (240, 240, 240) # Light gray for main canvas

PERSON_PHOTO_SCALE_TO_QR_WIDTH_FACTOR = 2.0 
QR_DISPLAY_SIZE = (80, 80) # Target display size for QR codes

MIN_PERSONS_PER_IMAGE = 2
MAX_PERSONS_PER_IMAGE = 6
NUM_SAMPLE_IMAGES_TO_CREATE = 5

MIN_SPACING_BETWEEN_PERSON_UNITS = 30
MAX_PLACEMENT_ATTEMPTS_PERSON_UNIT = 100

def get_asset_paths(asset_dir: str) -> List[str]:
    """Lists available image files (jpg, png, jpeg) from the specified directory."""
    if not os.path.isdir(asset_dir):
        print(f"Warning: Asset directory not found: {asset_dir}")
        return []
    supported_extensions = (".jpg", ".jpeg", ".png")
    return sorted([ # Sort for deterministic behavior if needed, though random.sample is used later
        os.path.join(asset_dir, f)
        for f in os.listdir(asset_dir)
        if f.lower().endswith(supported_extensions)
    ])

def create_person_qr_unit(
    person_photo_path: str, 
    qr_code_path: str, 
    qr_target_display_size: Tuple[int, int],
    scale_factor: float
    ) -> Optional[Image.Image]:
    """
    Creates a single visual unit: a person's photo with their QR code overlaid.
    The person's photo is scaled relative to the QR code's width.
    The QR code is placed in the bottom half, horizontally centered.
    """
    try:
        person_img = Image.open(person_photo_path).convert("RGB")
    except Exception as e:
        print(f"Error: Could not open person photo {person_photo_path}: {e}")
        return None

    try:
        qr_img_raw = Image.open(qr_code_path).convert("RGBA")
        qr_img_resized = qr_img_raw.resize(qr_target_display_size, Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Error: Could not open or resize QR code {qr_code_path}: {e}")
        return None

    # Scale person photo based on QR code width
    scaled_person_width = int(qr_target_display_size[0] * scale_factor)
    
    # Maintain aspect ratio for person photo
    person_w_orig, person_h_orig = person_img.size
    aspect_ratio = person_h_orig / person_w_orig
    scaled_person_height = int(scaled_person_width * aspect_ratio)

    try:
        person_img_scaled = person_img.resize((scaled_person_width, scaled_person_height), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Error: Could not resize person photo {person_photo_path}: {e}")
        return None

    # Create the unit canvas, same size as the scaled person photo
    unit_canvas = person_img_scaled.copy() # Start with the person's photo as the base

    # Calculate QR code position on this unit_canvas
    # Horizontally center the QR code
    qr_pos_x = (scaled_person_width - qr_target_display_size[0]) // 2
    # Place QR code in the bottom half, e.g., starting at 60% of the height
    # Ensure it doesn't go off the bottom edge.
    qr_pos_y = int(scaled_person_height * 0.60) 
    if qr_pos_y + qr_target_display_size[1] > scaled_person_height:
        qr_pos_y = scaled_person_height - qr_target_display_size[1] # Place it at the bottom edge
    if qr_pos_y < 0 : qr_pos_y = 0 # Ensure it's not above top if photo is tiny

    # Paste QR code onto the unit_canvas (person's scaled photo)
    unit_canvas.paste(qr_img_resized, (qr_pos_x, qr_pos_y), qr_img_resized if qr_img_resized.mode == 'RGBA' else None)
    
    return unit_canvas

def create_group_scene_image(person_qr_units: List[Image.Image], output_path: str):
    """
    Arranges multiple 'person_qr_unit' images onto a larger canvas.
    """
    if not person_qr_units:
        print("Warning: No person_qr_units provided to create_group_scene_image. Skipping.")
        return

    scene_canvas = Image.new('RGB', (NEW_CANVAS_WIDTH, NEW_CANVAS_HEIGHT), CANVAS_BG_COLOR)
    placed_unit_bboxes = []

    for unit_img in person_qr_units:
        unit_w, unit_h = unit_img.size
        placed = False
        for _ in range(MAX_PLACEMENT_ATTEMPTS_PERSON_UNIT):
            pos_x = random.randint(0, NEW_CANVAS_WIDTH - unit_w)
            pos_y = random.randint(0, NEW_CANVAS_HEIGHT - unit_h)
            
            current_bbox = (pos_x, pos_y, pos_x + unit_w, pos_y + unit_h)
            overlap = False
            for placed_bbox in placed_unit_bboxes:
                # Check for overlap with spacing
                if not (
                    current_bbox[2] + MIN_SPACING_BETWEEN_PERSON_UNITS < placed_bbox[0] or
                    current_bbox[0] - MIN_SPACING_BETWEEN_PERSON_UNITS > placed_bbox[2] or
                    current_bbox[3] + MIN_SPACING_BETWEEN_PERSON_UNITS < placed_bbox[1] or
                    current_bbox[1] - MIN_SPACING_BETWEEN_PERSON_UNITS > placed_bbox[3]
                ):
                    overlap = True
                    break
            
            if not overlap:
                scene_canvas.paste(unit_img, (pos_x, pos_y))
                placed_unit_bboxes.append(current_bbox)
                placed = True
                break
        
        if not placed:
            print(f"Warning: Could not place a person_qr_unit of size {unit_img.size} without overlap after attempts.")

    try:
        scene_canvas.save(output_path)
        print(f"Successfully created group scene image: {output_path}")
    except Exception as e:
        print(f"Error saving group scene image to {output_path}: {e}")

if __name__ == "__main__":
    print("--- Starting Sample Test Image Generation Process (Person Units) ---")
    app_config = load_config()
    
    qr_codes_input_dir = app_config.get(QR_CODES_DIR_CONFIG_KEY)
    sample_images_output_dir = app_config.get(SAMPLE_IMAGES_OUTPUT_DIR_CONFIG_KEY)

    if not qr_codes_input_dir or not sample_images_output_dir:
        print(f"Error: Config keys '{QR_CODES_DIR_CONFIG_KEY}' or '{SAMPLE_IMAGES_OUTPUT_DIR_CONFIG_KEY}' not found. Exiting.")
        exit()

    all_qr_code_paths = get_asset_paths(qr_codes_input_dir)
    all_person_photo_paths = get_asset_paths(PHOTOS_DIR)

    if not all_qr_code_paths:
        print(f"Error: No QR codes found in '{qr_codes_input_dir}'. Run prepare_data.py. Exiting.")
        exit()
    if not all_person_photo_paths:
        print(f"Error: No person photos found in '{PHOTOS_DIR}'. Please add photos. Exiting.")
        exit()
    
    print(f"Found {len(all_qr_code_paths)} QR codes and {len(all_person_photo_paths)} person photos.")

    os.makedirs(sample_images_output_dir, exist_ok=True)
    print(f"Sample images will be saved to: {sample_images_output_dir}")

    # Manage unique pairing: Create a list of available (photo_path, qr_path) unique pairs
    # Shuffle both lists to ensure random pairing if one list is longer than the other
    # random.shuffle(all_person_photo_paths) # No longer needed here, sampling is random
    # random.shuffle(all_qr_code_paths)
    
    # num_available_unique_pairs = min(len(all_person_photo_paths), len(all_qr_code_paths))
    
    # if num_available_unique_pairs == 0:
    #     print("Error: Cannot create pairs as either photos or QR codes are missing. Exiting.")
    #     exit()

    # print(f"Will be able to create up to {num_available_unique_pairs} unique person-QR units.")

    # Create a pool of unique (photo_path, qr_code_id) pairs
    # QR code ID is filename without extension
    # unique_pairs_pool = [] # This complex pooling and popping logic is removed
    # for i in range(num_available_unique_pairs):
    #     qr_id = os.path.splitext(os.path.basename(all_qr_code_paths[i]))[0]
    #     unique_pairs_pool.append((all_person_photo_paths[i], all_qr_code_paths[i], qr_id))


    for i_img in range(NUM_SAMPLE_IMAGES_TO_CREATE):
        num_persons_for_this_image = random.randint(MIN_PERSONS_PER_IMAGE, MAX_PERSONS_PER_IMAGE)
        
        # Ensure enough unique photos and QRs for THIS image
        if len(all_person_photo_paths) < num_persons_for_this_image or len(all_qr_code_paths) < num_persons_for_this_image:
            print(f"Warning: Not enough unique photos ({len(all_person_photo_paths)}) or QR codes ({len(all_qr_code_paths)}) to select {num_persons_for_this_image} distinct persons for image {i_img+1}.")
            num_persons_for_this_image = min(len(all_person_photo_paths), len(all_qr_code_paths))
            if num_persons_for_this_image == 0:
                print(f"Skipping image {i_img+1} as no photos or QR codes are available for pairing.")
                continue
            print(f"Adjusting to {num_persons_for_this_image} persons for this image.")

        # Select unique photos and QR codes for the current image
        try:
            selected_photo_paths = random.sample(all_person_photo_paths, num_persons_for_this_image)
            selected_qr_code_paths = random.sample(all_qr_code_paths, num_persons_for_this_image)
        except ValueError as e:
            print(f"Error sampling photos/QRs for image {i_img+1} (requested {num_persons_for_this_image}): {e}. Skipping this image.")
            continue

        if not selected_photo_paths or not selected_qr_code_paths:
            print(f"Skipping image {i_img+1} as no photo or QR code paths could be selected.")
            continue
            
        current_person_qr_units = []
        print(f"\nCreating sample image {i_img+1}/{NUM_SAMPLE_IMAGES_TO_CREATE} with {num_persons_for_this_image} persons...")

        actual_qr_ids_in_image = [] # To store the QR IDs actually used in this image
        for idx in range(num_persons_for_this_image):
            person_photo_p = selected_photo_paths[idx]
            qr_code_p = selected_qr_code_paths[idx]
            qr_id_val = os.path.splitext(os.path.basename(qr_code_p))[0] # Get ID from QR filename
            
            unit = create_person_qr_unit(
                person_photo_path=person_photo_p, 
                qr_code_path=qr_code_p,
                qr_target_display_size=QR_DISPLAY_SIZE,
                scale_factor=PERSON_PHOTO_SCALE_TO_QR_WIDTH_FACTOR
            )
            if unit:
                current_person_qr_units.append(unit)
                actual_qr_ids_in_image.append(qr_id_val) # Keep track of the QR ID
        
        if not current_person_qr_units:
            print(f"Could not create any person-QR units for image {i_img+1}. Skipping.")
            continue

        # The output filename should somehow reflect the QR IDs it contains for easier mapping later
        # For now, just a generic name. This could be improved by storing metadata.
        # Example: sample_image_1_qrs_id1_id2_id3.png
        # For simplicity now, let's keep the old naming and rely on detection.
        output_file_name = f"sample_image_{i_img+1}.png"
        output_file_path = os.path.join(sample_images_output_dir, output_file_name)
        
        create_group_scene_image(current_person_qr_units, output_file_path)
        # Store a mapping of image filename to the QR IDs it contains
        # This is crucial for main.py if we want to avoid re-detecting QR from these specific images
        # For now, main.py will still detect them. This metadata can be an enhancement.
        # Example: with open(os.path.join(sample_images_output_dir, f"sample_image_{i_img+1}_metadata.json"), 'w') as mf:
        #    json.dump({"filename": output_file_name, "qr_ids": actual_qr_ids_in_image}, mf, indent=4)


    print("\n--- Sample Test Image Generation Process Finished ---") 