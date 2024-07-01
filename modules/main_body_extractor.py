import fitz  # PyMuPDF
import math
from modules.table_extractor import draw_boxes_and_extract_text

def open_pdf_document(file_path):
    """Open a PDF document for processing."""
    return fitz.open(file_path)

def extract_tables_bounding_boxes(file_path):
    """Extract bounding boxes for tables in the document."""
    return draw_boxes_and_extract_text(file_path, False,False)  # Enable highlighting

def map_tables_by_page(table_bounding_boxes):
    """Map tables to their respective pages for quick lookup."""
    tables_map = {}
    for box_info in table_bounding_boxes:
        rectangle, page_index = box_info[0], box_info[0][4]
        tables_map.setdefault(page_index, []).append(rectangle[:4])
    return tables_map

def calculate_ignorable_page_threshold(document):
    """Calculate the threshold beyond which pages should be ignored."""
    total_pages = document.page_count
    return math.ceil(total_pages - math.log(total_pages, 1.9))

def extract_text_excluding_tables_and_ignored_sections(document, tables_map, ignore_threshold):
    """Extract text while excluding specified tables and sections beyond a certain page threshold."""
    important_keywords = {"acknowledgements", "author contribution", "declarations", "references"}
    main_text, tables_text = [], []
    process_from_page = False
    stop_processing = False

    for index, page in enumerate(document):
        if stop_processing or index >= ignore_threshold:
            break

        words = page.get_text("words")  # This includes bounding boxes
        if index == 0 and any("abstract" in word_info[4].lower() for word_info in words):
            process_from_page = True
            continue

        if not process_from_page:
            continue

        for word_info in words:
            word, rect = word_info[4], fitz.Rect(word_info[:4])
            if any(keyword in word.lower() for keyword in important_keywords):
                stop_processing = True
                break

            if rect[1] < 40 or (tables_map.get(index) and any(fitz.Rect(table_area).contains(rect) for table_area in tables_map[index])):
                tables_text.append(word)
                continue

            main_text.append(word)

    return main_text, tables_text

def main_body_extractor(file_path):
    """Run the process to extract the main body and tables from a PDF document."""
    document = open_pdf_document(file_path)
    bounding_boxes = extract_tables_bounding_boxes(file_path)
    tables_page_map = map_tables_by_page(bounding_boxes)
    page_threshold_to_ignore = calculate_ignorable_page_threshold(document)
    main_text, tables_text = extract_text_excluding_tables_and_ignored_sections(document, tables_page_map, page_threshold_to_ignore)
    document.close()
    return main_text, tables_text
