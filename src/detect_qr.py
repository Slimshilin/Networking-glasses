from typing import List, Dict, Tuple
import cv2
from pyzbar.pyzbar import decode

def detect_qr_codes(image_path: str) -> List[Dict[str, any]]:
    """
    Locate and decode all QR codes in an image.
    Returns list of {id: str, bbox: (x,y,w,h)}
    using pyzbar on grayscale OpenCV image.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Image not found or could not be read at {image_path}")
            return []
    except Exception as e:
        print(f"Error reading image at {image_path} with OpenCV: {e}")
        return []

    # Convert to grayscale (pyzbar works better with grayscale)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect QR codes
    decoded_objects = decode(gray_img)

    detections = []
    if not decoded_objects:
        print(f"No QR codes found in {image_path}")
        return []

    for obj in decoded_objects:
        # The data attribute of the DecodedObject is bytes, so decode to string
        try:
            qr_id = obj.data.decode('utf-8')
        except UnicodeDecodeError:
            print(f"Could not decode QR data to UTF-8: {obj.data}. Skipping this QR code.")
            continue
            
        # Get the bounding box
        rect = obj.rect
        bbox: Tuple[int, int, int, int] = (rect.left, rect.top, rect.width, rect.height)
        
        detections.append({
            "id": qr_id,
            "bbox": bbox
        })
        # print(f"Detected QR Code. ID: {qr_id}, BBox: {bbox}") # For debugging
        
    return detections

if __name__ == '__main__':
    # This is an example of how to use the function.
    # You'll need a sample image with QR codes in the specified path.
    # For example, if you have sample_qr_image.png in ../assets/
    # Ensure the QR codes in the image encode simple text IDs.

    # Create a dummy image for testing if you don't have one
    # This requires `qrcode` and `numpy` to be installed.
    # And assumes `generate_qr_codes` from the other module was run to create QR codes.
    
    # First, let's try to use the sample image specified in the PRD
    sample_image_path = "../assets/sample_group.jpg"
    print(f"Attempting to detect QR codes in: {sample_image_path}")

    # Check if the sample image exists
    import os
    if not os.path.exists(sample_image_path):
        print(f"Warning: Sample image {sample_image_path} not found.")
        print("Please place a sample image with QR codes at that location, or update the path.")
        print("As a placeholder, creating a dummy QR code image for testing: dummy_test_qr.png")
        
        # Create a dummy QR code for basic testing of this module
        try:
            import numpy as np
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data("test_id_123")
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            
            # Save it as a PNG that OpenCV can read
            # Convert PIL image to OpenCV format
            pil_image = img_qr
            numpy_image = np.array(pil_image)
            cv_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGBBGR) # Convert RGB to BGR for OpenCV

            dummy_image_path = "dummy_test_qr.png" # Save in current dir for simplicity
            cv2.imwrite(dummy_image_path, cv_image)
            print(f"Created dummy QR image: {dummy_image_path}")
            
            detected = detect_qr_codes(dummy_image_path)
            if detected:
                print(f"Successfully detected QR codes in dummy image: {detected}")
            else:
                print("Failed to detect QR codes in the dummy image. Check dependencies (pyzbar, opencv). ")
            os.remove(dummy_image_path) # Clean up dummy image

        except ImportError:
            print("Could not create dummy QR image. Please install qrcode and numpy: pip install qrcode numpy")
        except Exception as e:
            print(f"An error occurred while creating or processing the dummy QR image: {e}")

    else:
        # If sample_group.jpg exists
        detections = detect_qr_codes(sample_image_path)
        if detections:
            print(f"Detected {len(detections)} QR codes:")
            for det in detections:
                print(f"  ID: {det['id']}, Bounding Box: {det['bbox']}")
        else:
            print(f"No QR codes detected in {sample_image_path}.")
