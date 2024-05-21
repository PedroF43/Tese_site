import fitz  # PyMuPDF
import re
from collections import defaultdict
import os

def find_table_lines_and_header(pdf_path):
    pattern = re.compile(r'^Table \d\s*$')
    with fitz.open(pdf_path) as doc:
        line_coordinates = []
        table_coordinates = []

        for page in doc:
            drawings = page.get_drawings()
            blocks = page.get_text("dict")["blocks"]
            
            for b in blocks:
                if b['type'] == 0:
                    for line in b["lines"]:
                        for span in line["spans"]:
                            if pattern.fullmatch(span['text']):
                                table_coordinates.append([span['text'], span['bbox'][1], page.number])

            for drawing in drawings:
                for item in drawing['items']:
                    if item[0] in ('re', 'l'):
                        line_bbox = fitz.Rect(item[1:5]) if item[0] == 'l' else fitz.Rect(item[1])
                        line_bbox += (-1, -1, 1, 1)
                        if 50 < line_bbox[1] < 720 and abs(line_bbox[1] - line_bbox[3]) < 10:
                            line_coordinates.append([line_bbox, page.number])
        return line_coordinates, table_coordinates

def define_table_values(line_coordinates,table_coordinates):
    lines_by_page=[]
    lines_append_buffer=[]
    for table in table_coordinates:
        lines_append_buffer=[]
        for line in line_coordinates:
            if table[2]==line[1]:
                lines_append_buffer.append([table,line])
        if lines_append_buffer:
            lines_by_page.append(lines_append_buffer)
    grouped_tables = defaultdict(list)
    
    for table_and_lines in lines_by_page:
        table=table_and_lines[0][0]
        grouped_tables[table[-1]].append(table)
    table_boundaries=[]
    for page_number_keys in grouped_tables:
        groups=[]
        output_values=grouped_tables[page_number_keys]
        output_values = sorted(output_values, key=lambda output_values: output_values[1])
        for i,elem in enumerate(output_values):
            if i+1<len(output_values):
                groups.append((elem[1], output_values[i+1][1]))
            else:
                groups.append((elem[1], float('inf')))
        table_boundaries.append([groups,page_number_keys])
    return table_boundaries,lines_by_page

def separate_appropriate_lines_into_tables(table_boundaries,lines_by_page):
    i=0
    final_bbox=[]
    for coords in table_boundaries:
        page_num=coords[1]
        for group in coords[0]:
            bbox=[]
            for j in range(len(lines_by_page[i])):
                if group[0]<lines_by_page[i][j][1][0][1]<group[1]:
                    bbox.append(lines_by_page[i][j][1][0])
            final_bbox.append([bbox,page_num])
            i+=1
    return final_bbox


def complete_tables_bbox(rectangles):
    final_rectangles=[]
    final_tables=[]
    if not rectangles:
        return []
    for i in range(len(rectangles)):
        current_rectangles=rectangles[i][0]
        page_num=rectangles[i][1]
        current_rectangles=sorted(current_rectangles, key=lambda rect: (rect[1], rect[0]))
    # Grouping the rectangles
        grouped_rectangles = []
        current_group = [current_rectangles[0]]

        for current in current_rectangles[1:]:
            # Compare current rectangle y-coordinate with the last one in the current group
            if abs(current[1] - current_group[-1][1]) <= 3:
                current_group.append(current)
            else:
                grouped_rectangles.append(current_group)
                current_group = [current]
        
        # Append the last group if not empty
        if current_group:
            grouped_rectangles.append(current_group)
        complete_lines=[]
        for rect in grouped_rectangles:
            x0,x1=rect[0][:2]
            y0,y1=rect[-1][2:]
            complete_line=[x0,x1,y0,y1]
            complete_lines.append(complete_line)
        final_rectangles.append(complete_lines)
        for table in final_rectangles:
            complete_tables=[]
            x0,x1=table[0][:2]
            y0,y1=table[-1][2:]
            complete_table=[x0,x1,y0,y1,page_num]
            complete_tables.append(complete_table)
        final_tables.append(complete_tables)    
    return final_tables


def draw_boxes_and_extract_text(pdf_path, highlight,save_image):
    line_coordinates, table_coordinates = find_table_lines_and_header(pdf_path)
    doc = fitz.open(pdf_path)
    table_boundaries, lines_by_page = define_table_values(line_coordinates, table_coordinates)
    bboxes = separate_appropriate_lines_into_tables(table_boundaries, lines_by_page)
    refined_boxes = complete_tables_bbox(bboxes)

    # Ensure the output folder exists
    output_folder = "static/tables"
    os.makedirs(output_folder, exist_ok=True)

    if highlight:
        for i, box in enumerate(refined_boxes):
            x0, y0, x1, y1, page_number = box[0]
            page = doc[page_number]  # Adjust for zero-based indexing of pages
            rect = fitz.Rect(x0, y0, x1, y1)
            # Draw a rectangle on the page
            page.draw_rect(rect, color=(1, 0, 0), width=1.5)

            # Increase image quality by specifying a higher resolution
    if save_image:
        for i, box in enumerate(refined_boxes):
            x0, y0, x1, y1, page_number = box[0]
            page = doc[page_number]  # Adjust for zero-based indexing of pages

            x0, y0, x1, y1 = x0-1, y0-1, x1-1, y1-1
            rect=fitz.Rect(x0, y0, x1, y1)

            zoom = 3  # Increase the zoom factor to enhance image quality
            mat = fitz.Matrix(zoom, zoom)  # Create a transformation matrix for the zoom
            pix = page.get_pixmap(matrix=mat, clip=rect)

            image_path = os.path.join(output_folder, f"table_{i + 1}.png")
            pix.save(image_path)

    doc.close()
    return refined_boxes

