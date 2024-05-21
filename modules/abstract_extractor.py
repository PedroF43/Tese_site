import fitz  # PyMuPDF

def extract_abstract_words_and_bboxes(file_path):
    # Open the provided PDF file
    document = fitz.open(file_path)
    text=[]
    # Get the first page of the document
    page = document[0]
    
    # Extract words and their bounding boxes
    words = page.get_text("words")
    
    # Find the index where the word 'Abstract' occurs
    abstract_start_index = next((i for i, word in enumerate(words) if 'Abstract' in word[4]), None)

    if abstract_start_index is None:
        print("No 'Abstract' found in the first page.")
        document.close()
        return []

    # Collect all words and their bboxes after 'Abstract'
    abstract_words_and_bboxes = []
    for word in words[abstract_start_index+1:]:
        abstract_words_and_bboxes.append((word[:4]))  # word[4] is the text, word[:4] is the bbox
        text.append(word[4])
    # Close the document
    document.close()

    return text,abstract_words_and_bboxes

def bbox_calculator(bbox):
    for i in range(len(bbox) - 1):
        # Extract right-most x and y coordinates of the current bbox
        right_x, right_y = bbox[i][2], bbox[i][3]
        # Extract left-most x and y coordinates of the next bbox
        left_x, left_y = bbox[i + 1][0], bbox[i + 1][1]

        # Check if the bboxs are sufficiently apart from each other
        if abs(right_x - left_x) > 20 and abs(left_y - right_y) > 5:
            # If conditions are met, return the current index
            return i
# If no such pair is found, return the last index or another appropriate value
    return len(bbox) - 1

def abstract_extractor(file_path):
    text,all_words_bbox = extract_abstract_words_and_bboxes(file_path)
    indx=bbox_calculator(all_words_bbox)
    return (text[:indx+1])
