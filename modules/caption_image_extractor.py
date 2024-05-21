import re
import fitz  # Import the PyMuPDF library
import io
import math
import numpy as np
import os

def scrape(filePath):
    results = []  # Stores (text, bounding box) tuples
    page_numbers = []

    # Open the PDF file safely using 'with' statement
    with fitz.open(filePath) as pdf:
        for j, page in enumerate(pdf):  # Use enumerate to get page index
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:  # Check if 'lines' key exists
                    for line in block['lines']:
                        for span in line['spans']:
                            results.append((span['text'], span['bbox']))
                            page_numbers.append(j)

    return results, page_numbers

def figures(path):
    text_to_analyse, pages = scrape(path)  # Call scrape only once to get both text and pages
    page_list = []
    matches_list = []

    # Combine the patterns for "Fig." and "Figure" into a single regex pattern

    pattern = re.compile(r'^\s*Fig(?:ure)?\.?\s*\d+\s*', re.IGNORECASE)

    for i, word in enumerate(text_to_analyse):
        if pattern.match(word[0]):
            matches_list.append(text_to_analyse[i:i+100])  # Capture next 100 elements
            page_list.append(pages[i])

    return matches_list, page_list

def bounding_box(figure):
    # Iterate over the list of figures, stopping before the last to avoid IndexError
    for i in range(len(figure) - 1):
        # Extract right-most x and y coordinates of the current figure
        right_x, right_y = figure[i][1][2], figure[i][1][3]
        # Extract left-most x and y coordinates of the next figure
        left_x, left_y = figure[i + 1][1][0], figure[i + 1][1][1]

        # Check if the figures are sufficiently apart from each other
        if abs(right_x - left_x) > 20 and abs(left_y - right_y) > 5:
            # If conditions are met, return the current index
            return i

    # If no such pair is found, return the last index or another appropriate value
    return len(figure) - 1

def captions(path):
    lista, pages = figures(path)
    full_words = []
    bbox = []
    for i in range(0, len(lista)):
        full_word = []
        #print(lista[i][0])
        figure = lista[i]
        page = pages[i]
        bbox.append(lista[i][0][1])
        #print(bbox)
        indx = bounding_box(figure)
        j = 0
        word_buffer = ''  # Temporary variable to accumulate characters
        for word in figure:
            j += 1
            if j <= int(indx + 1):
                # Check if the last character of the word_buffer is a hyphen
                if word_buffer.endswith('-'):
                    word_buffer = word_buffer[:-1] + word[0]  # Remove hyphen and append next part of the word directly
                else:
                    if word_buffer and not word_buffer.endswith(' '):
                        word_buffer += ' '  # Adds a space if the last character isn't a space
                    word_buffer += word[0]
        full_word.append(word_buffer)  # Append the last word
        full_words.append((full_word, page))
    return full_words, bbox

def extract_images_with_xref(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # Dictionary to store extracted images with their xref as key
    images_with_xref = []

    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)

        # Get images on the page
        images = page.get_images(full=True)
        for img_index, img_info in enumerate(images):
            xref = img_info[0]  # xref of the imag
            bbox=page.get_image_bbox(img_info)
            if xref not in images_with_xref:
                images_with_xref.append([xref,bbox,page_number])

    # Close the PDF document
    pdf_document.close()

    return images_with_xref


def distance_np(p1, p2):
    return np.sqrt(np.sum((p2 - p1) ** 2))

def image_captions_matcher(captions, images):
    xrefs = []
    resulting_captions = []
    used_xrefs = set()  # Initialize set to track used xrefs

    for i in range(len(captions[0])):
        current_caption = captions[0][i]
        current_caption_bbox = np.array(captions[1][i])
        current_page = captions[0][i][1]
        caption_center = np.array([(current_caption_bbox[0] + current_caption_bbox[2]) / 2,
                                   (current_caption_bbox[1] + current_caption_bbox[3]) / 2])

        min_distance = np.inf
        min_xref = None

        for j in range(len(images)):
            current_xref = images[j][0]
            if current_page == images[j][2] and current_xref not in used_xrefs:  # Skip if xref is already used
                current_image_bbox = np.array(images[j][1])

                # Calculate distances between caption center and image corners
                current_distance = np.min([
                    distance_np(caption_center, current_image_bbox[:2]),  # Top left corner
                    distance_np(caption_center, np.array([current_image_bbox[2], current_image_bbox[1]])),  # Top right corner
                    distance_np(caption_center, np.array([current_image_bbox[0], current_image_bbox[3]])),  # Bottom left corner
                    distance_np(caption_center, current_image_bbox[2:])  # Bottom right corner
                ])

                if current_distance < min_distance:
                    min_distance = current_distance
                    min_xref = current_xref

        if min_xref is not None:
            used_xrefs.add(min_xref)  # Mark this xref as used to avoid reassociation
            xrefs.append(min_xref)
            resulting_captions.append(current_caption)

    return xrefs, resulting_captions


def extract_and_display_images(pdf_path):
    legenda = image_captions_matcher(captions(pdf_path), extract_images_with_xref(pdf_path))
    xref_list = legenda[0]
    legenda = legenda[1]
    i = 0
    results=[]
    for xref in xref_list:
        if i < len(legenda):
            i += 1
        results.append([xref,legenda[i-1][0]])
    return results
    
def extract_images_by_xref(pdf_path):
    doc = fitz.open(pdf_path)
    output_folder = "static/extracted_images"
    os.makedirs(output_folder, exist_ok=True)  # Ensure the output folder exists
    captions=[]
    image_index = 1  # Initialize the image index counter
    references=extract_and_display_images(pdf_path)
    for ref in references:
        xref = ref[0]  # Assuming each reference contains an xref as the first item
        caption=ref[1]
        image = doc.extract_image(xref)  # Extract the image using xref
        image_bytes = image["image"]  # Get the image bytes
        
        # Save the image
        image_filename = os.path.join(output_folder, f"{image_index}.png")
        with open(image_filename, "wb") as img_file:
            img_file.write(image_bytes)
        image_index += 1  # Increment the counter for each image
        captions.append(caption)
    doc.close()
    return captions