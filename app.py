from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit  # Import SocketIO and emit
from werkzeug.utils import secure_filename

import shutil
import os
import threading

# Import your modules here
from modules.abstract_extractor import abstract_extractor
from modules.coordinates_extractor import process_all_pdfs_in_folder
from modules.caption_image_extractor import extract_images_by_xref
from modules.table_extractor import draw_boxes_and_extract_text
from modules.metada_simple_extraction import api_pdf_metada
from tese_script import process_all_pdfs
app = Flask(__name__)
socketio = SocketIO(app)  # Initialize SocketIO with Flask app

UPLOAD_FOLDER = 'uploaded_papers'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'png', 'jpg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

cords = {}  # Stores coordinates results and statuses
abst = {}   # Stores abstracts results and statuses
meta = {}
figs = {}
tabs={}
figs_desc={}
locs={}
user_count = 0  # Initialize user count

@socketio.on('connect')
def handle_connect():
    global user_count
    user_count += 1
    emit('user count update', {'count': user_count}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global user_count
    user_count -= 1
    emit('user count update', {'count': user_count}, broadcast=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def background_processing_task(filename, upload_folder, extract_types):
    file_path = os.path.join(upload_folder, filename)
    
    def list_extracted_images(directory):
        """List all image filenames from the specified directory."""
        extracted_image_files = []
        if os.path.exists(directory):
            for f in os.listdir(directory):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    extracted_image_files.append(f)
        return extracted_image_files
    try:
        if "Locations" in extract_types:
            locations=process_all_pdfs(f"{upload_folder}","")
            # Specify the directory where images are extracted
            locs[filename] = {'status': 'Processed', 'data': locations[0]}

        if  "Author_Title_Keywords_Doi" in extract_types:
            metadata=api_pdf_metada(f"{upload_folder}/{filename}")
            meta[filename]= {'status': 'Processed', 'data': metadata}


        if "Tables" in extract_types:
            draw_boxes_and_extract_text(f"{upload_folder}/{filename}",False,True)
            # Specify the directory where images are extracted
            extracted_tables = list_extracted_images("static/tables")
            tabs[filename] = {'status': 'Processed', 'data': extracted_tables}

        if "Figures" in extract_types:
            figs_description=extract_images_by_xref(f"{upload_folder}/{filename}")
            # Specify the directory where images are extracted
            extracted_images = list_extracted_images("static/extracted_images")
            figs[filename] = {'status': 'Processed', 'data': extracted_images}
            figs_desc[filename] = {'status': 'Processed', 'data': figs_description}

        if 'Coordinates' in extract_types:
            coordinates = process_all_pdfs_in_folder(upload_folder)
            cords[filename] = {'status': 'Processed', 'data': coordinates[0]}

        if 'Abstract' in extract_types:
            abstract = abstract_extractor(f"uploaded_papers/{filename}")
            abstract = " ".join(abstract)  # If abstract is a list of strings, concatenate into a single string
            abst[filename] = {'status': 'Processed', 'data': abstract}

        # Remove the original file after processing
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # Handle errors gracefully and delete the file if possible
        if os.path.exists(file_path):
            os.remove(file_path)
        cords[filename] = {'status': 'Error', 'message': str(e)}
        abst[filename] = {'status': 'Error', 'message': str(e)}
        figs[filename] = {'status': 'Error', 'message': str(e)}
        tabs[filename] = {'status': 'Error', 'message': str(e)}
        figs_desc[filename] = {'status': 'Error', 'message': str(e)}
        locs[filename] = {'status': 'Error', 'message': str(e)}
        meta[filename] = {'status': 'Error', 'message': str(e)}
        print(meta[filename])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        global extract_types
        extract_types = request.form.getlist('extract_type')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            thread = threading.Thread(target=background_processing_task, args=(filename, UPLOAD_FOLDER, extract_types))
            thread.start()
            return redirect(url_for('processing', filename=filename))
        else:
            return "Invalid file type or no file selected", 400
    return render_template('index.html', user_count=user_count)

@app.route('/processing')
def processing():
    filename = request.args.get('filename')

    return render_template('processing.html', filename=filename,extract_types=extract_types)

@app.route('/check_status')
def check_status():
    filename = request.args.get('filename')
    locs_status=locs.get(filename, {'status': 'Not started', 'message': 'Processing has not started yet.'})
    coord_status = cords.get(filename, {'status': 'Not started', 'message': 'Processing has not started yet.'})
    abst_status = abst.get(filename, {'status': 'Not started', 'message': 'Processing has not started yet.'})
    figs_status = figs.get(filename, {'status': 'Not started', 'message': 'Processing has not started yet.'})
    tabs_status= tabs.get(filename, {'status': 'Not started', 'message': 'Processing has not started yet.'})
    meta_status=meta.get(filename, {'status': 'Not started', 'message': 'Processing has not started yet.'})
   # print(coord_status,abst_status,figs_status,tabs_status,locs_status)
    return jsonify({'filename': filename, 'Coordinates': coord_status, 'Abstract': abst_status,'Figures' : figs_status,'Tables': tabs_status,'Locations': locs_status,'Author_Title_Keywords_Doi': meta_status})

@app.route('/reset-data', methods=['Get','POST'])
def reset_data():
    global cords, abst,figs,figs_desc,tabs,locs,meta
    cords = {}  # Reset coordinates dictionary
    meta = {}
    abst = {}   # Reset abstract dictionary
    figs= {}
    figs_desc={}
    tabs={}
    locs={}

    # Path to the directory to remove
    directory_path_figs = "static/extracted_images"
    directory_path_tables = "static/tables"
    # Check if the directory exists
    if os.path.exists(directory_path_figs):
        # Remove the entire directory tree
        shutil.rmtree(directory_path_figs)

    if os.path.exists(directory_path_tables):
        # Remove the entire directory tree
        shutil.rmtree(directory_path_tables)
    
    return redirect(url_for('index'))  # Redirect back to the initial form page

@app.route('/uploaded')
def uploaded():
    filename = request.args.get('filename')
    if filename:
        results = {
            'status': 'Not started',
            'abstract': '',
            'coordinates': [],
            'Figures': [],  # Ensure this key exists to avoid key errors
            'Figures_desc': [],
            'Tables': [],
            'Locations': [],
            'Meta': []
        }

        # Update coordinates if available
        if filename in locs and 'data' in locs[filename]:
            results['Locations'] = locs[filename]['data']
            results['status'] = locs[filename].get('status', 'Processed')

        if filename in cords and 'data' in cords[filename]:
            results['coordinates'] = cords[filename]['data']
            results['status'] = cords[filename].get('status', 'Processed')

        # Update abstract if available
        if filename in abst and 'data' in abst[filename]:
            results['abstract'] = abst[filename]['data']
            results['status'] = abst[filename].get('status', 'Processed')

        # Update figures if available
        if filename in figs and 'data' in figs[filename]:
            results['Figures'] = figs[filename]['data']
            results['status'] = figs[filename].get('status', 'Processed')
        
        if filename in figs_desc and 'data' in figs_desc[filename]:
            results['Figures_desc']=figs_desc[filename]['data']
            results['status'] = figs_desc[filename].get('status', 'Processed')

        if filename in tabs and 'data' in tabs[filename]:
            results['Tables'] = tabs[filename]['data']
            results['status'] = tabs[filename].get('status', 'Processed')

        if filename in meta and 'data' in meta[filename]:
            results['Meta'] = meta[filename]['data']
            results['status'] = meta[filename].get('status', 'Processed')
        # Pass the images explicitly as a separate variable if needed or use directly from 'message'
        print(results)
        return render_template('uploaded.html', message=results)
    



if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) 
