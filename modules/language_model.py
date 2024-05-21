import requests
system = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
user = "<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
bot = "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

ENDPOINT = "https://every-palestinian-info-composer.trycloudflare.com/api"

def get_prompt(user_msg):
    return {
        "prompt": f"{user_msg}",
        "use_story": "False", # Use the story from the KoboldAI UI, can be managed using other API calls (See /api for the documentation)
        "use_memory": "False", # Use the memnory from the KoboldAI UI, can be managed using other API calls (See /api for the documentation)
        "use_authors_note": "False", # Use the authors notes from the KoboldAI UI, can be managed using other API calls (See /api for the documentation)
        "use_world_info": "False", # Use the World Info from the KoboldAI UI, can be managed using other API calls (See /api for the documentation)
        "max_context_length": 8192, # How much of the prompt will we submit to the AI generator? (Prevents AI / memory overloading)
        "max_length": 256, # How long should the response be?
        "rep_pen": 1, # Prevent the AI from repeating itself
        "rep_pen_range": 2048, # The range to which to apply the previous
        "rep_pen_slope": 1, # This number determains the strength of the repetition penalty over time
        "temperature": 0, # How random should the AI be? In a low value we pick the most probable token, high values are a dice roll
        "tfs": 1, # Tail free sampling, https://www.trentonbricken.com/Tail-Free-Sampling/
        "top_a": 0, # Top A sampling , https://github.com/BlinkDL/RWKV-LM/tree/4cb363e5aa31978d801a47bc89d28e927ab6912e#the-top-a-sampling-method
        "top_k": 0, # Keep the X most probable tokens
        "top_p": 1, # Top P sampling / Nucleus Sampling, https://arxiv.org/pdf/1904.09751.pdf
        "typical": 1, # Typical Sampling, https://arxiv.org/pdf/2202.00666.pdf
        "sampler_order": [6,0,1,3,4,2,5], # Order to apply the samplers, our default in this script is already the optimal one. KoboldAI Lite contains an easy list of what the
        "stop_sequence": ["<|eot_id|><|start_header_id|>user<|end_header_id|>", "<|eot_id|><|start_header_id|>assistant<|end_header_id|>"], # When should the AI stop generating? In this example we stop when it tries to speak on behalf of the user.
        #"sampler_seed": 1337, # Use specific seed for text generation? This helps with consistency across tests.
        "singleline": "False", # Only return a response that fits on a single line, this can help with chatbots but also makes them less verbose
        "sampler_full_determinism": "False", # Always return the same result for the same query, best used with a static seed
        "frmttriminc": "True", # Trim incomplete sentences, prevents sentences that are unfinished but can interfere with coding and other non english sentences
        "frmtrmblln": "False", #Remove blank lines
        "quiet": "False" # Don't print what you are doing in the KoboldAI console, helps with user privacy
        }


def study_area_extractor(prompt,prompt_type):  # using a list to update conversation history is more memory efficient than constantly updating a string
    try:
        if prompt_type=="Abstract":
                    system_message = ("Instructions: Your task is to identify the main geographical locations that are critical to the research discussed in the abstract. "
                                    "These locations must be specifically mentioned as significant to the research and must be actual physical places that can be precisely geolocated on a map. "
                                    "Avoid listing broad areas, geological periods, or terms that describe time frames rather than places. "
                                    "If no specific locations are mentioned in the abstract, respond with 'No significant locations found.' "
                                    "Otherwise, provide only the names of these geographical locations, formatted in a list separated by semicolons, without including any other text, commentary, or explanation. "
                                    "Ensure each location name is separated clearly to facilitate easy parsing for use in API calls or database storage. Do not add any text beyond the location names.\n\n"
                                    "Expected Output Format Example: Specific Location 1; Specific Location 2; etc. If no locations are identified, output: No significant locations found.\n\n"
                                    "Please make sure to follow these instructions carefully to ensure the response meets the required format and includes no additional information, focusing exclusively on geographical locations."
                                    )

        elif prompt_type == "Body":
            system_message = ("""
You are an AI tasked with extracting the most geographically significant locations from geology research papers. Your responses must strictly follow these guidelines:

1. **Analyze the Text**: Read the provided text section to identify specific geographical locations of academic relevance.
   
2. **Identify Key Research Locations**:
   - Focus only on actual physical places that can be precisely geolocated on a map.
   - Do not include broad regions, geological periods, or terms describing time frames or geological formations.
   - Choose the least number of relevant locations that still cover the key academic significance, place great emphasis on choosing the least amount of locations.

3. **Format Locations**:
   - List each identified location using its most specific and widely recognized name.
   - Separate the locations with semicolons.

4. **Flag if No Locations**:
   - If no geographically significant locations are found, output exactly: "No significant locations."

5. **Output Only the Locations or Flag**:
   - Your response must contain only the names of the locations or the specified flag.
   - Do not include any additional text, commentary, explanations, or notes. 
   - Any extraneous text beyond the location names or the flag is strictly prohibited.

### Examples:

**Example 1**:
Input Text: "The study examines the geological features of the Himalayas, specifically focusing on Mount Everest and the Karakoram Range."
Output: "Mount Everest; Karakoram Range"

**Example 2**:
Input Text: "The paper does not mention any specific locations relevant to geological formations."
Output: "No significant locations"


**Output for the Model**:
- List of specific locations separated by semicolons.
- Choose the least number of relevant locations.
- If no locations are found, output: "No significant locations"
- Absolutely no other text should be included.
""")

        conversation_history = []
        # user_message=f"You are a geology phd student tasked with extracting the study location of a research paper by its abstract, you must answer strictly using this template according to how many locations you think should be recorded: 'Location 1: abc Location 2: edf etc' {extraido}"
        user_message=prompt

        fullmsg = system+system_message+user+user_message+bot # Add all of conversation history if it exists and add User and Bot names
        prompt = get_prompt(fullmsg) # Process prompt into KoboldAI API format
        response = requests.post(f"{ENDPOINT}/v1/generate", json=prompt) # Send prompt to API

        if response.status_code == 200:
            results = response.json()['results'] # Set results as JSON response
            text = results[0]['text'] # inside results, look in first group for section labeled 'text'
            response_text = text#.split('\n')[0].replace("  ", " ") # Optional, keep only the text before a new line, and replace double spaces with normal ones
            conversation_history.append(f"{fullmsg}{response_text}\n") # Add the response to the end of your conversation history
        else:
            print(response)

    except Exception as e:
        print(f"An error occurred: {e}")
    return response_text

