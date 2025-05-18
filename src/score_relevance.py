import json
import os
# import numpy as np # No longer needed for cosine similarity here
# from sklearn.metrics.pairwise import cosine_similarity # No longer needed
from typing import List, Dict, Tuple

# Dartmouth Chat API related imports are no longer needed here as relevance is pre-calculated
# import httpx 
# from openai import OpenAI

# DARTMOUTH_CHAT_API_KEY = os.getenv("DARTMOUTH_CHAT_API_KEY")
# http_client_relevance = httpx.Client()
# api_relevance = OpenAI(
#     base_url="https://chat.dartmouth.edu/api",
#     api_key=DARTMOUTH_CHAT_API_KEY,
#     http_client=http_client_relevance
# )
# USER_BIO_PLACEHOLDER = "..." # No longer needed

def load_profiles(path: str) -> Dict[str, Dict]:
    """Reads profiles file (e.g., profile_relevance.json) into dict keyed by id."""
    profiles_dict = {}
    try:
        with open(path, 'r') as f:
            profiles_list = json.load(f)
        for profile in profiles_list:
            if "id" in profile:
                # Ensure essential fields for ranking and annotation are present
                if "relevance" not in profile:
                    print(f"Warning: Profile ID {profile['id']} missing 'relevance' field. Assigning 0.0.")
                    profile['relevance'] = 0.0 
                if "name" not in profile:
                     print(f"Warning: Profile ID {profile['id']} missing 'name' field. Using ID as name.")
                     profile['name'] = profile['id']
                # relevance_explanation is optional for scoring but good to check if expected
                if "relevance_explanation" not in profile:
                    profile['relevance_explanation'] = "N/A"
                profiles_dict[profile["id"]] = profile
            else:
                print(f"Warning: Profile found without an ID in {path}. Skipping: {profile.get('name', 'N/A')}")
    except FileNotFoundError:
        print(f"Error: Profiles file not found at {path}. Returning empty dictionary.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {path}. Returning empty dictionary.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while loading profiles from {path}: {e}")
        return {}
    return profiles_dict

# get_embedding_for_scorer function is removed as it's no longer needed.
# get_user_embedding function is removed as it's no longer needed for runtime scoring.

def rank_profiles(
    # user_emb: List[float], # No longer needed
    detected_ids: List[str],
    all_profiles_data: Dict[str, Dict],
    top_k: int
) -> List[Tuple[str, float]]: # Returns list of (id, relevance_score)
    """Ranks profiles based on pre-calculated relevance scores."""
    # if not user_emb: # Check removed
    #     print("User embedding is empty. Cannot rank profiles.")
    #     return []
    if not detected_ids:
        print("No detected IDs provided. Nothing to rank.")
        return []
    if not all_profiles_data:
        print("Profiles data is empty. Cannot rank.")
        return []

    candidate_profiles_with_scores = []
    for pid in detected_ids:
        if pid in all_profiles_data:
            profile = all_profiles_data[pid]
            # The 'relevance' field is expected to be directly in the profile data
            if "relevance" in profile:
                candidate_profiles_with_scores.append((pid, float(profile["relevance"])))
            else:
                print(f"Warning: Profile ID {pid} found but has no 'relevance' score. Skipping.")
        else:
            print(f"Warning: Detected profile ID {pid} not found in loaded profiles data. Skipping.")

    if not candidate_profiles_with_scores:
        print("No candidate profiles with relevance scores to rank.")
        return []

    # Sort by relevance score in descending order
    candidate_profiles_with_scores.sort(key=lambda x: x[1], reverse=True)

    return candidate_profiles_with_scores[:top_k]


if __name__ == '__main__':
    print("Testing score_relevance.py with pre-calculated relevance...")

    # Load configuration to get the path for profile_relevance.json
    from src.utils import load_config # Import here for testing scope
    config = load_config()
    PROFILES_JSON_PATH = config.get("PROFILES_JSON_PATH") # Should be data/profile_relevance.json
    TOP_K_RESULTS = config.get("TOP_K_RESULTS", 3)

    if not PROFILES_JSON_PATH:
        print("Error: PROFILES_JSON_PATH not set in config. Cannot run test.")
        exit()

    # 1. Load profiles (these should have pre-calculated relevance)
    print(f"Loading profiles from {PROFILES_JSON_PATH}...")
    profiles_data = load_profiles(PROFILES_JSON_PATH)
    if not profiles_data:
        print(f"No profiles loaded. Make sure {PROFILES_JSON_PATH} exists and is populated (run prepare_data.py).")
        exit()
    print(f"Loaded {len(profiles_data)} profiles.")

    # 2. Simulate some detected QR code IDs (these should be keys in profiles_data)
    detected_profile_ids = list(profiles_data.keys())[:5] # Take up to 5 IDs for testing
    if not detected_profile_ids:
        print("No profile IDs available from profiles file to simulate detection. Cannot test ranking.")
        exit()
    print(f"Simulating detection of QR IDs: {detected_profile_ids}")

    # 3. Rank Profiles using pre-calculated scores
    print(f"Ranking profiles (top {TOP_K_RESULTS})...")
    top_ranked_profiles = rank_profiles(detected_profile_ids, profiles_data, TOP_K_RESULTS)

    if top_ranked_profiles:
        print(f"\nTop {len(top_ranked_profiles)} ranked profiles:")
        for profile_id, score in top_ranked_profiles:
            profile_details = profiles_data.get(profile_id, {})
            profile_name = profile_details.get("name", "Unknown Name")
            explanation = profile_details.get("relevance_explanation", "N/A")
            print(f"  ID: {profile_id}, Name: {profile_name}, Score: {score:.2f}")
            print(f"    Explanation: {explanation}")
    else:
        print("No profiles were ranked. Check previous steps and warnings.")

    print("\nscore_relevance.py test completed.")
