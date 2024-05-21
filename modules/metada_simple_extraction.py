
import fitz  # PyMuPDF
import requests

def extract_pdf_metadata(pdf_file_path):
    metadata_dict = {}

    # Open the PDF file using fitz
    with fitz.open(pdf_file_path) as doc:
        # Access the metadata of the PDF
        meta = doc.metadata
        metadata_dict['Author'] = meta.get('author', 'N/A')
        metadata_dict['Title'] = meta.get('title', 'N/A')
        metadata_dict['Keywords'] = meta.get('keywords', 'N/A')
        metadata_dict['DOI'] = meta.get('doi', 'N/A') if 'doi' in meta else 'N/A'

        # Clean metadata entries
        if len(metadata_dict['Title'].split()) < 2:
            metadata_dict['Title'] = 'N/A'
        if len(metadata_dict['Author'].split()) < 5:
            metadata_dict['Author'] = 'N/A'
        if len(metadata_dict['Keywords'].split()) < 2:
            metadata_dict['Keywords'] = 'N/A'

    return metadata_dict

def author_parser(authors):
    if not authors:
        return "No authors listed"
    # Simplify the parsing process to avoid unnecessary computations
    return ", ".join(f"{author['given']} {author['family']}" for author in authors)

def direct_crossref_api(search, email):
    url = f"https://api.crossref.org/works?query.title={search}&select=title,author,DOI&rows=1&mailto={email}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        items = data.get('message', {}).get('items', [])
        if items:
            item = items[0]
            title = item.get("title", ["No title provided"])[0]
            authors = author_parser(item.get("author", []))
            doi = item.get("DOI", "No DOI provided")
            return title, authors, doi
        else:
            return "No results found", "No authors", "No DOI"
    else:
        return "Error fetching data", "Error retrieving authors", "Error retrieving DOI"

    
def api_pdf_metada(pdf_file_path):
    result={}
    metadata=extract_pdf_metadata(pdf_file_path)
    if metadata['Keywords']!='N/A':
        keywords=metadata['Keywords']
    else:
        keywords=metadata['Keywords']
    keywords_list = keywords.split(';')
    metadata['Keywords']=keywords_list

    email_address='joao.pedro002009@gmail.com'
    title, authors, doi = direct_crossref_api(metadata["Title"], email_address)
    result['Title']=title
    result['Authors']=authors
    result['Keywords']=metadata['Keywords']
    result['DOI']=doi
    return result