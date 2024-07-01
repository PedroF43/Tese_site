import os 
import fitz 
import time
import re
import unicodedata
from unidecode import unidecode
from modules.language_model import study_area_extractor
from modules.main_body_extractor import main_body_extractor
from modules.abstract_extractor import abstract_extractor



def find_text_surrounding_keywords(text, keywords, window=1200):
    # Create a single pattern that matches any of the keywords
    keyword_pattern = r'\b(?:' + '|'.join(map(re.escape, keywords)) + r')\b'
    
    # Find all matches along with their start and end indices
    matches = [(match.group(0), match.start(), match.end()) for match in re.finditer(keyword_pattern, text, flags=re.IGNORECASE)]
    
    # Collect contexts and track start and end indices
    contexts = []
    for keyword, start, end in matches:
        # Calculate start and end points ensuring they are within the bounds of the text
        start_context = max(0, start - window)
        end_context = min(len(text), end + window)
        
        # Store the contexts with their indices
        context_text = text[start_context:end_context]
        contexts.append((start_context, end_context, context_text))
    
    # Merge overlapping contexts
    if contexts:
        # Sort contexts by their start index
        contexts.sort()
        merged_contexts = [contexts[0]]
        
        for current_context in contexts[1:]:
            last_context = merged_contexts[-1]
            # Check if the current context overlaps with the last one in the merged list
            if current_context[0] <= last_context[1]:
                # Merge the contexts by extending the end of the last context
                merged_contexts[-1] = (last_context[0], max(last_context[1], current_context[1]), text[last_context[0]:max(last_context[1], current_context[1])])
            else:
                merged_contexts.append(current_context)
        
        # Combine all merged contexts into a single string
        combined_contexts = " ".join([context[2] for context in merged_contexts]).replace('\n', ' ')
        return combined_contexts
    else:
        print("No keywords found.")
        return ""

def normalize_unicode_characters(text):
    # Normalize to NFKD form which separates base characters from diacritics and other marks
    normalized_string = unicodedata.normalize('NFKD', text)
    # Encode to ASCII bytes, ignoring errors, then decode back to string
    ascii_string = normalized_string.encode('ascii', 'ignore').decode('ascii')
    return ascii_string

def split_text_into_parts_by_word_count(text, words_per_part, overlap_percentage=0.1):
    # Normalize and remove non-ASCII characters from the input string
    sanitized_string = normalize_unicode_characters(text)
    words = sanitized_string.split()
    
    # Adjust the part size and overlap based on the number of words and desired words per part
    k = words_per_part
    overlap = int(k * overlap_percentage)
    
    parts = []
    index = 0  # Start index for each part

    while index < len(words):
        # Calculate end index, ensuring it does not exceed the length of the word list
        end_index = index + k if (index + k <= len(words)) else len(words)
        
        parts.append(' '.join(words[index:end_index]))
        
        # Update the start index for the next part, adjusting by overlap
        # This check prevents the last segment from overlapping past the list if near the end
        if end_index == len(words):
            break
        index += (k - overlap)

    return parts


def location_parser(resulting_parts,pdf_path):
    output=[]
    abstract=abstract_extractor(pdf_path)
    abstract=" ".join(abstract)
    for parts in resulting_parts:
        parts=str(abstract)+str(parts)
        output.append(study_area_extractor(parts,"Body"))
    return output

def normalize_location_name(name):
    # Normalize by removing parentheses, special characters, and converting to lower case
    name = re.sub(r'\(.*?\)|[^\w\s]', '', name).lower()
    # Remove common words and descriptors
    descriptors = {}
    words = name.split()
    filtered_words = [word for word in words if word not in descriptors]
    return ' '.join(filtered_words)

def split_entries(data_list):
    """Split entries in a list by semicolon and flatten the result into a single list."""
    new_list = []
    for item in data_list:
        # Split each item by semicolon and extend the new_list with the results
        new_list.extend(item.split('; '))
    return new_list

def process_location_tuples(data):
    # Start with the first tuple's locations as the initial set of unique locations
    if data==[]:
        return []
    unique_locations = [data[0]]

    # Iterate over the rest of the tuples
    for current_tuple in data[1:]:
        current_locations = current_tuple.split('; ')
        new_unique_locations = []

        for location in current_locations:
            # Normalize current location
            normalized_current_location = normalize_location_name(location)
            is_similar = False

            # Check against all previously accepted locations
            for unique_location in unique_locations:
                normalized_unique_location = normalize_location_name(unique_location)

                # Check if the normalized current location is a substring of any unique location
                if normalized_current_location in normalized_unique_location or normalized_unique_location in normalized_current_location:
                    is_similar = True
                    break

            # If not similar to any, add to new unique locations
            if not is_similar:
                new_unique_locations.append(location)
        
        # Update the list of unique locations with newly added locations
        unique_locations.extend(new_unique_locations)
    unique_locations=split_entries(unique_locations)
    return unique_locations

keywords = ["location", "location map", "located", "study area", "latitude", "longitude", 
            "geographic location", "geographical location", "geographical setting", 
            "geological map", "region", "division", "district", "county", "village", 
            "town", "province", "Geological Settings"]

def extract_research_locations_from_body(pdf_path):
    text, table_text = main_body_extractor(pdf_path)
    words_per_part=2500
    text= " ".join(text)
    text=re.sub(r'- ',"",text) # Remove hypenated words in line breaks
    surrounding_text = find_text_surrounding_keywords(text, keywords)
    resulting_parts = split_text_into_parts_by_word_count(surrounding_text, words_per_part)
    start_time = time.time()
    locations = location_parser(resulting_parts,pdf_path)
    llm_time = time.time() - start_time


    resulting_unique_locations = process_location_tuples(locations)

    return resulting_unique_locations,llm_time

def convert_to_ascii(text):
    """Convert Unicode text to ASCII."""
    return unidecode(text)

def count_occurrences(pdf_path, search_terms):
    """Count occurrences of search terms in a PDF file, returning only those with counts greater than zero, sorted by count."""
    document = fitz.open(pdf_path)
    occurrences = {term: 0 for term in search_terms}  # Initialize dictionary to count occurrences
    page_num=len(document)
    for page in document:
        text = page.get_text("text")
        ascii_text = convert_to_ascii(text)

        for term in search_terms:
            ascii_term = convert_to_ascii(term)
            occurrences[term] += ascii_text.lower().count(ascii_term.lower())

    document.close()
    
    # Filter out terms with zero occurrences and sort the dictionary by count in descending order
    sorted_occurrences = sorted(occurrences.items(), key=lambda item: item[1], reverse=True)
    return dict(sorted_occurrences),page_num

def process_all_pdfs(directory,verbosity):
    occurrences=[]
    """Process all PDF files in the specified directory and print occurrences of search terms."""
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(directory, filename)
            locations,llm_time=extract_research_locations_from_body(pdf_path)
            frequency,page_num = count_occurrences(pdf_path, locations)
            occurrences.append(frequency)
            if verbosity=="v":
                print(f"Processed {filename} with {page_num} pages in {llm_time:.2f} seconds.")
    return occurrences
