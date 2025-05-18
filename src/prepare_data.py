import os
import json
from typing import List, Dict
import httpx # Keep for OpenAI client
from openai import OpenAI # Keep for OpenAI client
from faker import Faker # Ensure Faker is imported for fallback
import qrcode
import uuid
from src.utils import load_config
from tqdm import tqdm # Import tqdm

# Initialize Faker - only for fallback if AI completely fails for names, or not at all
# fake = Faker() 

# Dartmouth Chat API details - will be used for chat completion later
# It's good practice to load the API key from an environment variable
DARTMOUTH_CHAT_API_KEY = os.getenv("DARTMOUTH_CHAT_API_KEY")
if not DARTMOUTH_CHAT_API_KEY:
    print("Warning: DARTMOUTH_CHAT_API_KEY environment variable not set. AI profile generation and relevance scoring will fail or use placeholders.")

# API client for potential chat completion
# This setup is for a standard OpenAI-compatible API.
# You MAY need to adjust base_url or other parameters for Dartmouth's specific Chat API.
http_client_chat = httpx.Client()
chat_api = OpenAI(
    base_url="https://chat.dartmouth.edu/api", # Assuming chat completions are at the same base
    api_key=DARTMOUTH_CHAT_API_KEY,
    http_client=http_client_chat
)

# --- Phase 1A: Generate Base Profile Content using AI ---
def generate_ai_profile_contents(num_profiles: int, theme: str, model_name: str) -> List[Dict]:
    """
    Generates core content (name, title, bio) for fake profiles using the Chat API.
    Theme describes the type of profiles to generate (e.g., 'students at a tech and finance career fair').
    Returns a list of dicts, each with {"name", "title", "bio"}.
    """
    if not DARTMOUTH_CHAT_API_KEY:
        print("Error: DARTMOUTH_CHAT_API_KEY not set. Cannot perform AI profile generation.")
        return [] 

    print(f"\nAttempting to generate {num_profiles} profile contents using AI (model: {model_name}). Theme: {theme}...")
    
    system_prompt = f"""
    You are an AI assistant helping to create realistic fake professional profiles for a simulation.
    The profiles should be diverse and suitable for individuals attending a career fair focused on "{theme}".
    Roles to include: students (clearly specify level: Undergraduate, Master's, PhD, Postdoc), recruiters (from tech companies, finance firms, startups), current employees (e.g., Software Engineer, Data Analyst, Product Manager, Investment Banker - from various seniority levels), university alumni, university professors (relevant fields like CS, Economics, etc.), and event organizers/staff.

    For each profile, you MUST generate:
    1. "name": A realistic full name.
    2. "title": A plausible job title, student description with level, or role (e.g., "Software Engineer at TechGiant", "Master's Student in Computer Science", "Recruiter at FinServe Co.", "Professor of Economics", "Event Coordinator"). Consider the theme and requested roles.
    3. "bio": A short professional biography (2-4 sentences) highlighting skills, experiences, and aspirations relevant to the theme and their role. Make them distinct and compelling.

    You MUST return a single JSON string that is a list of exactly {num_profiles} objects. Each object in the list MUST follow this structure strictly:
    {{ "name": "Full Name", "title": "Professional Title/Role", "bio": "A compelling bio..." }}

    Example of a single profile object in your response list (ensure your output matches this structure for all items):
    {{ "name": "Dr. Eleanor Vance", "title": "Professor of Computer Science", "bio": "Researching advancements in AI and machine learning. Authored several papers on distributed systems. Keen to connect with industry professionals and students exploring these fields." }}
    {{ "name": "Michael Lee", "title": "Undergraduate Student in Business Analytics", "bio": "Third-year student passionate about data-driven decision making. Seeking an internship in business intelligence or data analysis for summer 202X. Proficient in SQL and Python." }}

    Ensure your entire output is a valid JSON list of these objects. Do not include any other text, explanations, or markdown formatting before or after the JSON list itself.
    """
    
    user_content = f"Please generate {num_profiles} distinct professional profiles based on the theme: '{theme}' and the diverse roles specified. Follow the JSON output format strictly."
    
    ai_generated_profile_data = []

    try:
        print("Sending request to Chat API for profile generation. This might take some time...")
        # Wrap single API call with a simple tqdm description if desired, though it's one operation
        # For true progress, API would need to support streaming or per-profile generation
        # For now, print statements mark start/end. tqdm can be used on processing results if it's a loop.
        response = chat_api.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.8, # Slightly higher temperature for more creative/varied profiles
            # max_tokens can be important here depending on the number of profiles and bio length
        )
        
        ai_response_content = response.choices[0].message.content
        print("Received profile generation response from Chat API.")
        # print("Raw AI Profile Response:\n", ai_response_content) # Uncomment for debugging

        if ai_response_content.startswith("```json"):
            ai_response_content = ai_response_content[len("```json"):].strip()
            if ai_response_content.endswith("```"):
                ai_response_content = ai_response_content[:-len("```")].strip()
        else: # If not wrapped in markdown, try to find JSON list directly
            first_brace = ai_response_content.find('[')
            last_brace = ai_response_content.rfind(']')
            if first_brace != -1 and last_brace != -1:
                ai_response_content = ai_response_content[first_brace:last_brace+1]
            else:
                print("Warning: Could not find JSON list delimiters in AI response for profiles.")

        ai_response_content = ai_response_content.strip()
        
        try:
            parsed_profiles = json.loads(ai_response_content)
            if not isinstance(parsed_profiles, list):
                raise ValueError("AI response for profiles was not a JSON list.")

            for item in tqdm(parsed_profiles, desc="Processing Generated Profile Contents", total=len(parsed_profiles)):
                if isinstance(item, dict) and "name" in item and "title" in item and "bio" in item:
                    ai_generated_profile_data.append({
                        "name": str(item["name"]),
                        "title": str(item["title"]),
                        "bio": str(item["bio"])
                    })
                else:
                    print(f"Warning: Skipping malformed profile item from AI response: {item}")
            
            if not ai_generated_profile_data:
                 print("Critical Warning: AI returned no validly structured profiles after parsing.")
                 # raise ValueError("AI returned no valid profiles.") # Or return empty and handle upstream
            elif len(ai_generated_profile_data) < num_profiles:
                 print(f"Warning: AI returned {len(ai_generated_profile_data)} valid profiles, but {num_profiles} were requested. Using what was returned.")

        except json.JSONDecodeError as e:
            print(f"Error: Could not decode JSON from AI profile response: {e}")
            print("AI response snippet for profiles: ", ai_response_content[:500])
            return [] 
        except ValueError as e:
            print(f"Error: AI profile response validation failed: {e}")
            return [] 
            
    except Exception as e:
        print(f"An error occurred during Chat API call for profile generation: {e}")
        return [] 
    
    return ai_generated_profile_data

def generate_base_profiles_data(num_to_generate: int, model_name: str, theme: str) -> List[Dict]:
    """Generates N fake profiles using AI (or fallback), adds unique IDs."""
    ai_profiles_core_data = generate_ai_profile_contents(num_to_generate, theme, model_name)
    
    final_profiles_with_ids = []
    if not ai_profiles_core_data: # AI generation failed or returned empty
        print("AI profile generation failed or yielded no data. Creating basic placeholder profiles.")
        faker_instance = Faker() # Instantiate Faker only if needed for fallback names
        for i in tqdm(range(num_to_generate), desc="Generating Fallback Profiles"):
            final_profiles_with_ids.append({
                "id": str(uuid.uuid4()),
                "name": faker_instance.name(), # Use Faker for fallback names
                "title": "Placeholder Title",
                "bio": f"This is a placeholder bio for profile {i+1} due to AI profile generation issues."
            })
    else:
        for core_profile in tqdm(ai_profiles_core_data, desc="Processing AI Profiles"):
            final_profiles_with_ids.append({
                "id": str(uuid.uuid4()), 
                "name": core_profile["name"],
                "title": core_profile["title"],
                "bio": core_profile["bio"]
            })
        
    print(f"Generated {len(final_profiles_with_ids)} base profiles (AI-assisted or fallback).")
    return final_profiles_with_ids

def save_profiles_to_json(profiles: List[Dict], path: str):
    """Writes profiles to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(profiles, f, indent=4)
    print(f"Saved {len(profiles)} profiles to {path}")

def generate_qr_codes_for_profiles(profiles: List[Dict], out_dir: str):
    """Outputs one PNG per profile.id in out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    generated_count = 0
    print(f"Generating QR codes in {out_dir}...")
    for profile in tqdm(profiles, desc="Generating QR Codes"):
        profile_id = profile.get("id")
        if not profile_id:
            print(f"Skipping QR code generation for profile due to missing ID: {profile.get('name')}")
            continue
        
        qr_data = profile_id
        img = qrcode.make(qr_data)
        file_path = os.path.join(out_dir, f"{profile_id}.png")
        try:
            img.save(file_path)
            generated_count +=1
        except Exception as e:
            print(f"Error saving QR code for ID {profile_id} to {file_path}: {e}")
    if generated_count > 0:
        print(f"Generated {generated_count} QR codes in {out_dir}")

# --- Phase 2: Calculate Relevance using Chat Completion ---

def get_relevance_with_chat_completion(user_bio: str, profiles_to_evaluate: List[Dict], model_name: str) -> List[Dict]:
    """
    Uses Dartmouth Chat Completion API to get relevance scores and explanations for profiles.
    Returns a list of dicts, each with {"id", "relevance", "relevance_explanation"}.
    """
    if not DARTMOUTH_CHAT_API_KEY:
        print("Error: DARTMOUTH_CHAT_API_KEY not set. Cannot perform AI relevance scoring.")
        # Return profiles with placeholder relevance if API key is missing
        return [{"id": p["id"], "relevance": 0.0, "relevance_explanation": "API key missing, relevance not calculated."} for p in profiles_to_evaluate]

    print(f"\nAttempting to get relevance scores for {len(profiles_to_evaluate)} profiles using model: {model_name}...")
    
    # Construct the prompt
    # This prompt needs to be very specific about the output format.
    profiles_json_for_prompt = json.dumps([{"id": p["id"], "bio": p["bio"]} for p in profiles_to_evaluate], indent=2)
    
    system_prompt = f"""
    You are an AI assistant helping an event organizer identify relevant people.
    Your task is to evaluate a list of professional profiles based on their bio and compare them to the event organizer's bio.
    For each profile, you must provide a relevance score and a brief explanation.
    
    The event organizer's bio is: "{user_bio}"
    
    You will be given a JSON list of profiles, each with an "id" and a "bio".
    You MUST return a single JSON string that is a list of objects. Each object in the list MUST contain:
    1. "id": The original id of the profile.
    2. "relevance": A numerical relevance score from 0.0 (not relevant) to 1.0 (highly relevant).
    3. "relevance_explanation": A short (1-2 sentence) explanation for the score.
    
    Example of a single profile object in your response list:
    {{ "id": "some-uuid-string", "relevance": 0.85, "relevance_explanation": "This person's expertise in AI aligns well with the organizer's interests." }}
    
    Ensure your entire output is a valid JSON list of these objects.
    """
    
    user_content = f"Please evaluate the following profiles:\n{profiles_json_for_prompt}"

    all_relevance_data = []
    
    try:
        print("Sending request to Chat API. This might take a moment...")
        # Similar to profile generation, this is a single batch call.
        # tqdm here reflects the single operation.
        response = chat_api.chat.completions.create(
            model=model_name, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2,
            # response_format={ "type": "json_object" }, # Use if API supports forcing JSON output
        )
        
        ai_response_content = response.choices[0].message.content
        print("Received response from Chat API.")
        # print("Raw AI Response:\n", ai_response_content) # Uncomment for debugging

        # Attempt to parse the JSON response
        # The AI might sometimes return a JSON string wrapped in backticks or with leading/trailing text.
        # Basic cleaning attempt:
        if ai_response_content.startswith("```json"):
            ai_response_content = ai_response_content[7:] # Remove ```json
            if ai_response_content.endswith("```"):
                ai_response_content = ai_response_content[:-3] # Remove trailing ```
        ai_response_content = ai_response_content.strip()

        try:
            parsed_relevance_list = json.loads(ai_response_content)
            if not isinstance(parsed_relevance_list, list):
                raise ValueError("AI response was not a JSON list.")

            # Validate structure of each item
            valid_items_count = 0
            for item in tqdm(parsed_relevance_list, desc="Processing Relevance Scores", total=len(parsed_relevance_list)):
                if isinstance(item, dict) and "id" in item and "relevance" in item and "relevance_explanation" in item:
                    all_relevance_data.append({
                        "id": item["id"],
                        "relevance": float(item["relevance"]),
                        "relevance_explanation": str(item["relevance_explanation"])
                    })
                    valid_items_count += 1
                else:
                    print(f"Warning: Skipping malformed item from AI response: {item}")
            
            if valid_items_count != len(profiles_to_evaluate):
                print(f"Warning: AI returned {valid_items_count} valid relevance entries, but {len(profiles_to_evaluate)} were expected.")
                print("Missing entries will have placeholder relevance.")
                # Add placeholders for missing IDs
                returned_ids = {item["id"] for item in all_relevance_data}
                for p_eval in profiles_to_evaluate:
                    if p_eval["id"] not in returned_ids:
                        all_relevance_data.append({
                            "id": p_eval["id"], 
                            "relevance": 0.0, 
                            "relevance_explanation": "Relevance data not returned by AI."
                        })

        except json.JSONDecodeError as e:
            print(f"Error: Could not decode JSON from AI response: {e}")
            print("AI response was: ", ai_response_content)
            # Fallback: assign placeholder relevance to all if parsing fails
            all_relevance_data = [{"id": p["id"], "relevance": 0.0, "relevance_explanation": "AI response parsing failed."} for p in profiles_to_evaluate]
        
    except Exception as e:
        print(f"An error occurred during Chat API call or processing: {e}")
        # Fallback: assign placeholder relevance to all if API call fails
        all_relevance_data = [{"id": p["id"], "relevance": 0.0, "relevance_explanation": f"Chat API error: {e}"} for p in profiles_to_evaluate]

    return all_relevance_data

def merge_profile_data(base_profiles: List[Dict], relevance_data: List[Dict]) -> List[Dict]:
    """Merges base profile info with relevance data."""
    merged_profiles = []
    relevance_map = {r["id"]: r for r in relevance_data}
    
    for bp in tqdm(base_profiles, desc="Merging Profile Data"):
        profile_id = bp["id"]
        merged_profile = bp.copy()
        if profile_id in relevance_map:
            merged_profile["relevance"] = relevance_map[profile_id].get("relevance", 0.0)
            merged_profile["relevance_explanation"] = relevance_map[profile_id].get("relevance_explanation", "N/A")
        else:
            # This case should ideally be handled by placeholders in get_relevance_with_chat_completion
            merged_profile["relevance"] = 0.0
            merged_profile["relevance_explanation"] = "Relevance data missing for this ID."
        merged_profiles.append(merged_profile)
    return merged_profiles

# --- Main execution for prepare_data.py (Updated) ---
if __name__ == "__main__":
    print("--- Starting Data Preparation Process ---")
    
    # Load configuration from utils.py
    app_config = load_config()
    USER_BIO_FOR_RELEVANCE = app_config.get("USER_BIO")
    NUM_PROFILES = app_config.get("NUM_PROFILES_TO_GENERATE", 20)
    BASE_PROFILES_PATH = app_config.get("BASE_PROFILES_JSON_PATH")
    QR_CODES_OUTPUT_DIR = app_config.get("QR_CODES_DIR")
    FINAL_PROFILES_WITH_RELEVANCE_PATH = app_config.get("PROFILES_JSON_PATH")
    CHAT_MODEL = app_config.get("CHAT_MODEL_NAME")
    PROFILE_GENERATION_THEME = "students and recent graduates attending a career fair for tech and finance internships"

    print("\n--- Phase 1: Generating Base Profiles and QR Codes ---")
    phase_pbar = tqdm(total=3, desc="Data Preparation Phases") # Overall progress for phases
    
    if os.path.exists(BASE_PROFILES_PATH) and os.path.getsize(BASE_PROFILES_PATH) > 0:
        print(f"Found existing base profiles at {BASE_PROFILES_PATH}. Loading them.")
        with open(BASE_PROFILES_PATH, 'r') as f:
            base_profiles = json.load(f)
        if len(base_profiles) != NUM_PROFILES:
            print(f"Warning: Existing base profiles count ({len(base_profiles)}) differs from configured NUM_PROFILES_TO_GENERATE ({NUM_PROFILES}). Re-generating.")
            base_profiles = generate_base_profiles_data(NUM_PROFILES, CHAT_MODEL, PROFILE_GENERATION_THEME)
            save_profiles_to_json(base_profiles, BASE_PROFILES_PATH)
        
        if not os.listdir(QR_CODES_OUTPUT_DIR) or any(p["id"] not in [f.split('.')[0] for f in os.listdir(QR_CODES_OUTPUT_DIR)] for p in base_profiles):
             print(f"QR codes directory {QR_CODES_OUTPUT_DIR} is empty or seems inconsistent. Regenerating QR codes.")
             generate_qr_codes_for_profiles(base_profiles, QR_CODES_OUTPUT_DIR)
        else:
            print(f"QR codes seem to exist and match base profiles in {QR_CODES_OUTPUT_DIR}. Skipping QR regeneration.")
    else:
        print(f"{BASE_PROFILES_PATH} not found or empty. Generating new base profiles and QR codes.")
        base_profiles = generate_base_profiles_data(NUM_PROFILES, CHAT_MODEL, PROFILE_GENERATION_THEME)
        if base_profiles:
            save_profiles_to_json(base_profiles, BASE_PROFILES_PATH)
            generate_qr_codes_for_profiles(base_profiles, QR_CODES_OUTPUT_DIR)
        else:
            print("Error: No base profiles generated. Halting.")
            exit()
    phase_pbar.update(1) # Phase 1 complete
    phase_pbar.set_description("Phase 1 Complete")
    print("--- Base Profile and QR Code Generation/Loading Complete ---")
    
    print("\n--- Phase 2: Calculating Profile Relevance via Chat API ---")
    if not base_profiles:
        print("Error: Cannot proceed to relevance calculation as base profiles are not available.")
        exit()
    if not USER_BIO_FOR_RELEVANCE:
        print("Error: USER_BIO not found in configuration. Cannot calculate relevance.")
        exit()

    relevance_results = get_relevance_with_chat_completion(USER_BIO_FOR_RELEVANCE, base_profiles, CHAT_MODEL)
    phase_pbar.update(1) # Phase 2 complete
    phase_pbar.set_description("Phase 2 Complete")
    
    print("\n--- Phase 3: Merging and Saving Final Profiles with Relevance ---")
    final_profiles = merge_profile_data(base_profiles, relevance_results)
    save_profiles_to_json(final_profiles, FINAL_PROFILES_WITH_RELEVANCE_PATH)
    phase_pbar.update(1) # Phase 3 complete
    phase_pbar.set_description("Data Preparation Finished")
    phase_pbar.close()
    print(f"Saved final profiles with relevance to {FINAL_PROFILES_WITH_RELEVANCE_PATH}")

    print("\n--- Data Preparation Process Finished ---")
    print(f"IMPORTANT: If Chat API calls failed or returned unexpected results, check logs and {FINAL_PROFILES_WITH_RELEVANCE_PATH}.")
    print("Ensure DARTMOUTH_CHAT_API_KEY is set and CHAT_MODEL_NAME in config.json is correct for Dartmouth's API.") 