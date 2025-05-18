import cv2
import os
from typing import List, Dict, Tuple, Optional # Optional for Python < 3.10
# from PIL import Image, ImageDraw, ImageFont # PIL can be better for complex text, but let's stick to cv2 for now if possible

# MAX_BIO_LINES = 4 # Limit number of bio lines to display to prevent huge text blocks - REMOVED

def get_color_for_relevance(score: float) -> Tuple[int, int, int]:
    """Returns a BGR color based on the relevance score (0.0 to 1.0).
       Gradient: Red (low) -> Yellow (mid) -> Green (high).
    """
    # Ensure score is clamped between 0 and 1
    score = max(0.0, min(1.0, score))

    if score <= 0.33:
        # Transition from Red to Yellow (Red at 0, Yellow towards 0.33)
        # For simplicity, let's use pure Red for the first third
        # r = 255
        # g = int(255 * (score / 0.33)) 
        # b = 0
        # return (b, g, r) # BGR
        return (0,0,255) # Pure Red for low scores
    elif score <= 0.66:
        # Transition from Yellow to Green (Yellow at 0.33, Green towards 0.66)
        # For simplicity, let's use pure Yellow for the middle third
        # r = int(255 * (1 - (score - 0.33) / 0.33))
        # g = 255
        # b = 0
        # return (b, g, r) # BGR
        return (0, 255, 255) # Pure Yellow for medium scores
    else:
        # Transition towards Green (Green at 0.66 and above)
        # For simplicity, let's use pure Green for high scores
        # r = 0
        # g = 255
        # b = int(255 * ((score - 0.66) / 0.34)) # scale to blue for a cyan-like green, or keep 0 for pure green
        # return (b, g, r) # BGR
        return (0, 255, 0) # Pure Green for high scores

def draw_multiline_text_with_background(
    image, 
    text_lines: List[str], 
    position: Tuple[int, int], 
    font: int, 
    font_scale: float, 
    font_color: Tuple[int, int, int], 
    font_thickness: int, 
    bg_color: Tuple[int, int, int],
    text_block_max_width: int # Max width for the text block background
    ) -> Tuple[int, int, int, int]: # Returns (x1, y1, x2, y2) of the drawn block
    """Draws multiple lines of text with a single background rectangle. Returns bounding box of the drawn area."""
    x, y = position
    line_height_with_spacing = 0
    actual_max_line_width = 0

    if not text_lines:
        return (x,y,x,y) # No text, no area

    sample_line_height = cv2.getTextSize("Tg", font, font_scale, font_thickness)[0][1]
    line_height_with_spacing = sample_line_height + 5 # 5px spacing between lines

    for i, line in enumerate(text_lines):
        (line_w, line_h), _ = cv2.getTextSize(line, font, font_scale, font_thickness)
        if line_w > actual_max_line_width:
            actual_max_line_width = line_w
    
    bg_width = min(actual_max_line_width, text_block_max_width)
    bg_height = len(text_lines) * line_height_with_spacing - 5 # -5 to remove trailing space from last line

    padding = 5
    bg_x1 = x - padding
    bg_y1 = y - padding
    bg_x2 = x + bg_width + padding
    bg_y2 = y + bg_height + padding
    
    cv2.rectangle(image, (bg_x1, bg_y1), (bg_x2, bg_y2), bg_color, cv2.FILLED)

    current_y = y + sample_line_height # Start y for first line, adjusted for baseline
    for line in text_lines:
        cv2.putText(image, line, (x, current_y), font, font_scale, font_color, font_thickness)
        current_y += line_height_with_spacing
    
    return (bg_x1, bg_y1, bg_x2, bg_y2) # Return actual bounding box of the drawn block

def get_text_block_dimensions(
    text_lines: List[str],
    font: int,
    font_scale: float,
    font_thickness: int,
    text_block_max_width: int
) -> Tuple[int, int]:
    """Calculates the width and height of a multiline text block with background."""
    if not text_lines:
        return 0, 0

    actual_max_line_width = 0
    sample_line_height = cv2.getTextSize("Tg", font, font_scale, font_thickness)[0][1]
    line_height_with_spacing = sample_line_height + 5

    for line in text_lines:
        (line_w, _), _ = cv2.getTextSize(line, font, font_scale, font_thickness)
        if line_w > actual_max_line_width:
            actual_max_line_width = line_w
    
    bg_width = min(actual_max_line_width, text_block_max_width)
    bg_height = len(text_lines) * line_height_with_spacing - 5 # -5 for trailing space
    
    padding = 5
    return bg_width + (2 * padding), bg_height + (2 * padding)


def check_overlap(rect1: Tuple[int, int, int, int], rect2: Tuple[int, int, int, int]) -> bool:
    """Checks if two rectangles (x1, y1, x2, y2) overlap."""
    x1_1, y1_1, x2_1, y2_1 = rect1
    x1_2, y1_2, x2_2, y2_2 = rect2
    # Check for non-overlap
    if x1_1 >= x2_2 or x2_1 <= x1_2 or y1_1 >= y2_2 or y2_1 <= y1_2:
        return False
    return True

def annotate_image(
    input_image_path: str,
    output_image_path: str,
    ranked_profiles: List[Tuple[str, float]], # List of (id, score)
    all_detections: List[Dict],            # List of {id: str, bbox: (x,y,w,h)}
    profiles_data: Dict[str, Dict]         # Dict of {id: {name, bio, ...}}
):
    """
    Draws green rectangles and writes "Name (score)" and Bio at each bbox for ranked profiles.
    Attempts to place text to avoid overlaps.
    Saves result to output_path.
    """
    try:
        image = cv2.imread(input_image_path)
        if image is None:
            print(f"Error: Could not read image from {input_image_path}")
            return
    except Exception as e:
        print(f"Error loading image {input_image_path} with OpenCV: {e}")
        return

    img_h, img_w = image.shape[:2]
    detections_map = {det["id"]: det for det in all_detections if "id" in det and "bbox" in det}
    occupied_regions: List[Tuple[int, int, int, int]] = [] # List of (x1, y1, x2, y2) for text blocks

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.35
    font_color = (0, 0, 0)      # Black
    font_thickness = 1
    # box_color = (0, 255, 0)    # Green - Will be dynamic now
    box_thickness = 2
    text_bg_color = (250, 250, 240) # Off-white/Light beige background for text
    text_block_max_width = 250 # Slightly increased max width for potentially longer bios
    qr_box_padding = 5 # Padding around QR code for text placement

    for profile_id, score in ranked_profiles:
        if profile_id not in detections_map:
            continue
        
        detection = detections_map[profile_id]
        bbox = detection["bbox"]
        qr_x, qr_y, qr_w, qr_h = bbox

        # Draw QR bounding box first, with color based on relevance
        dynamic_box_color = get_color_for_relevance(score)
        cv2.rectangle(image, (qr_x, qr_y), (qr_x + qr_w, qr_y + qr_h), dynamic_box_color, box_thickness)
        # Add QR box to occupied regions to avoid drawing text over it (optional, but good for clarity)
        # occupied_regions.append((qr_x, qr_y, qr_x + qr_w, qr_y + qr_h))


        profile_info = profiles_data.get(profile_id)
        name_to_display = profile_info.get("name", profile_id) if profile_info else profile_id
        bio_to_display = profile_info.get("bio", "Bio not available.") if profile_info else "Bio not available."

        lines_for_annotation = []
        lines_for_annotation.append(f"Name: {name_to_display}")
        lines_for_annotation.append(f"Score: {score:.2f}")
        
        bio_words = bio_to_display.split(' ')
        current_bio_line = "Bio:"
        bio_line_count = 0
        for word in bio_words:
            # REMOVED: MAX_BIO_LINES check here, we display full bio
            # if bio_line_count >= MAX_BIO_LINES: 
            #     if not current_bio_line.endswith("..."):
            #         current_bio_line = current_bio_line.rstrip() + "..."
            #     break 
            
            test_line = f"{current_bio_line} {word}".strip()
            (line_w, _), _ = cv2.getTextSize(test_line, font, font_scale, font_thickness)
            
            if line_w > text_block_max_width and current_bio_line != "Bio:":
                lines_for_annotation.append(current_bio_line)
                current_bio_line = word
                # bio_line_count += 1 # No longer strictly tracking for MAX_BIO_LINES
                # REMOVED: MAX_BIO_LINES check during word addition
                # if bio_line_count >= MAX_BIO_LINES and word:
                #      current_bio_line = word[:text_block_max_width//10] + "..." 
                #      break
            else:
                current_bio_line = test_line
        
        if current_bio_line:
            lines_for_annotation.append(current_bio_line)

        # Calculate expected dimensions of the text block
        text_w, text_h = get_text_block_dimensions(lines_for_annotation, font, font_scale, font_thickness, text_block_max_width)
        
        if text_w == 0 or text_h == 0: continue # No text to draw

        # Candidate positions (relative to QR code)
        # Order of preference: Right, Left, Below, Above
        candidate_positions = [
            (qr_x + qr_w + qr_box_padding, qr_y),                               # Right
            (qr_x - text_w - qr_box_padding, qr_y),                             # Left
            (qr_x, qr_y + qr_h + qr_box_padding),                               # Below
            (qr_x, qr_y - text_h - qr_box_padding),                             # Above
            (qr_x + qr_w // 2 - text_w // 2, qr_y + qr_h + qr_box_padding),      # Centered Below
            (qr_x + qr_w // 2 - text_w // 2, qr_y - text_h - qr_box_padding),    # Centered Above
        ]
        
        best_pos: Optional[Tuple[int, int]] = None

        for cand_x, cand_y in candidate_positions:
            # Ensure candidate position is within image boundaries
            # Adjust for text block starting point (top-left of background)
            # The draw_multiline_text_with_background uses (x,y) as the start for actual text,
            # background is drawn with padding around it.
            # For collision, we need the background's bounding box.
            padding_for_bg = 5 # from draw_multiline_text_with_background
            cand_bg_x1 = cand_x - padding_for_bg
            cand_bg_y1 = cand_y - padding_for_bg
            cand_bg_x2 = cand_x + text_w - padding_for_bg # text_w already includes 2*padding
            cand_bg_y2 = cand_y + text_h - padding_for_bg # text_h already includes 2*padding


            if cand_bg_x1 < 0 or cand_bg_y1 < 0 or cand_bg_x2 > img_w or cand_bg_y2 > img_h:
                continue # Out of bounds

            candidate_rect = (cand_bg_x1, cand_bg_y1, cand_bg_x2, cand_bg_y2)
            is_overlapping = False
            for occupied_rect in occupied_regions:
                if check_overlap(candidate_rect, occupied_rect):
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                best_pos = (cand_x, cand_y)
                break
        
        # Fallback if no non-overlapping position is found
        if best_pos is None:
            # Default to right of QR, slightly offset down to reduce initial overlap chance with previous QR box
            # This is a simple fallback, could be made smarter
            best_pos_x = qr_x + qr_w + qr_box_padding
            best_pos_y = qr_y + 5 # slight offset
            
            # Clamp to image boundaries
            if best_pos_x + text_w - 5 > img_w: # -5 for padding
                best_pos_x = img_w - text_w + 5
            if best_pos_y + text_h - 5 > img_h:
                best_pos_y = img_h - text_h + 5
            if best_pos_x < 5 : best_pos_x = 5
            if best_pos_y < 5 : best_pos_y = 5 # Ensure some padding from top for y
            best_pos = (best_pos_x, best_pos_y)


        final_text_x, final_text_y = best_pos
        
        # Ensure final y_start is not negative if drawing from top.
        # draw_multiline_text_with_background places text starting from (final_text_x, final_text_y + first_line_height_approx)
        # but background from (final_text_x - padding, final_text_y - padding)
        # So, ensure final_text_y - padding >= 0
        bg_padding = 5 
        if final_text_y - bg_padding < 0:
            final_text_y = bg_padding 
        if final_text_x - bg_padding < 0:
            final_text_x = bg_padding


        drawn_rect = draw_multiline_text_with_background(
            image, lines_for_annotation, (final_text_x, final_text_y),
            font, font_scale, font_color, font_thickness, 
            text_bg_color, text_block_max_width
        )
        occupied_regions.append(drawn_rect)

    try:
        output_dir = os.path.dirname(output_image_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cv2.imwrite(output_image_path, image)
        print(f"Annotated image saved to {output_image_path}")
    except Exception as e:
        print(f"Error saving annotated image to {output_image_path}: {e}")

# Keep the __main__ block for testing if you have it, or add a simplified one
if __name__ == '__main__':
    # This is a simplified test setup. You might need to adjust paths or create dummy data.
    print("Testing annotate_image.py with overlap avoidance...")
    
    # Create a dummy input image
    DUMMY_INPUT_IMAGE_PATH = "dummy_annotate_input.png"
    DUMMY_OUTPUT_IMAGE_PATH = "dummy_annotate_output_overlap_test.png"
    import numpy as np
    test_image = np.full((768, 1024, 3), (220, 220, 220), dtype=np.uint8) # Light gray background
    cv2.putText(test_image, "Test Image for Annotations", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
    cv2.imwrite(DUMMY_INPUT_IMAGE_PATH, test_image)

    # Dummy data for testing
    dummy_profiles_data = {
        "id1": {"name": "Alice Wonderland", "bio": "Loves to explore digital landscapes and build amazing things with code. Python and AI enthusiast."},
        "id2": {"name": "Bob The Builder", "bio": "Constructing robust software solutions. Expert in cloud infrastructure and DevOps practices."},
        "id3": {"name": "Charlie Brown", "bio": "Good grief! Navigating the complexities of modern software development. Always learning."},
        "id4": {"name": "Diana Prince", "bio": "Championing user-centric design and accessibility in all applications. Advocate for inclusive tech."},
        "id5": {"name": "Edward Elric", "bio": "Equivalent exchange in software: effort for quality. Specializing in full-metal... err, full-stack development."}
    }
    dummy_ranked_profiles = [("id1", 0.95), ("id2", 0.88), ("id3", 0.75), ("id4", 0.92), ("id5", 0.80)]
    dummy_all_detections = [
        {"id": "id1", "bbox": (100, 100, 80, 80)},
        {"id": "id2", "bbox": (120, 120, 70, 70)}, # Intentionally overlapping QR slightly for test
        {"id": "id3", "bbox": (400, 300, 90, 90)},
        {"id": "id4", "bbox": (600, 150, 85, 85)},
        {"id": "id5", "bbox": (50, 500, 75, 75)},
    ]

    annotate_image(
        DUMMY_INPUT_IMAGE_PATH,
        DUMMY_OUTPUT_IMAGE_PATH,
        dummy_ranked_profiles,
        dummy_all_detections,
        dummy_profiles_data
    )
    print(f"Annotation test completed. Check {DUMMY_OUTPUT_IMAGE_PATH}")

    # Test with a slightly more crowded scenario
    DUMMY_OUTPUT_CROWDED_PATH = "dummy_annotate_output_crowded_test.png"
    dummy_all_detections_crowded = [
        {"id": "id1", "bbox": (50, 50, 60, 60)},
        {"id": "id2", "bbox": (70, 70, 60, 60)}, 
        {"id": "id3", "bbox": (90, 90, 60, 60)},
        {"id": "id4", "bbox": (200, 200, 60, 60)},
        {"id": "id5", "bbox": (220, 220, 60, 60)},
    ]
    annotate_image(
        DUMMY_INPUT_IMAGE_PATH,
        DUMMY_OUTPUT_CROWDED_PATH,
        dummy_ranked_profiles, # Use same profiles and ranking
        dummy_all_detections_crowded,
        dummy_profiles_data
    )
    print(f"Crowded annotation test completed. Check {DUMMY_OUTPUT_CROWDED_PATH}")

    # Cleanup dummy file
    # os.remove(DUMMY_INPUT_IMAGE_PATH) 
    # User might want to inspect it
    print(f"Dummy input image kept at {DUMMY_INPUT_IMAGE_PATH} for inspection.")
