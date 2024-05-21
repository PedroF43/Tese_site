import fitz  # PyMuPDF
import re
import os

def find_and_highlight_NE_pairs(pdf_path):
    doc = fitz.open(pdf_path)
    ne_pair_regex = r'([NESW]*\s*?\d{1,3})\°\s*(\d{1,2})\′\s*(\d{1,2})\″\s*([NESW]*)'
    Lat_long_pair_regex = r'Lat\.?\s*([-−−]?\d+\.\d+)\s*,?\s*Long\.?\s*([-−−]?\d+\.\d+)'
    coords=[]
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        processed_text = re.sub(r'[\u2013\u2014\u2015]', '-', text)
        processed_text = processed_text.replace('\n', ' ')
        
        found_pairs = re.findall(ne_pair_regex, processed_text, flags=re.IGNORECASE)
        if found_pairs==[]:
            found_pairs = re.findall(Lat_long_pair_regex, processed_text, flags=re.IGNORECASE)
            if found_pairs!=[]:
                for pair in found_pairs:
                    lat, lon = pair
                    coords.append([lat,lon])
        else:
            joined_pairs = [found_pairs[i] + found_pairs[i+1] for i in range(0, len(found_pairs), 2)]
            for pair in joined_pairs:
                pair=str(pair)
                letters = re.findall(r'[A-Z]', pair)
                numbers = re.findall(r'\d+', pair)
                first_coordinate=[letters[0],numbers[0:3]]
                second_coordinate=[letters[1],numbers[3:]]
                first_coordinate=dms_to_decimal(first_coordinate)
                second_coordinate=dms_to_decimal(second_coordinate)
                coords.append([first_coordinate,second_coordinate])
    return coords
def dms_to_decimal(coordinates):
    degrees=coordinates[1][0]
    minutes=coordinates[1][1]
    seconds=coordinates[1][2]
    direction=coordinates[0]
    decimal = int(degrees) + (int(minutes) / 60) + (int(seconds) / 3600)
    if direction in ['S', 'W']:
        decimal *= -1
    return round(decimal, 6)

def process_all_pdfs_in_folder(folder_path):
    coords_list=[]
    for filename in os.listdir(folder_path):
        pdf_path = os.path.join(folder_path, filename)
        coords=find_and_highlight_NE_pairs(pdf_path)
        if coords!=[]:
            coords_list.append(coords)
        else:
            coords_list.append(["N/A"])
    return coords_list