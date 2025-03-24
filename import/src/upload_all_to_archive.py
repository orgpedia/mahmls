import datetime
import json
import os
import sys
import time
from pathlib import Path

import internetarchive as ia
import requests

# Constants
BatchSize = 50
FiveAndHalfHours = (5 * 60 * 60) + (30 * 60)  # 5 hours and 30 minutes in seconds


def request_pdf(url, pdf_file):
    """Download a PDF file from a URL and save it to the specified path."""
    downloaded, dt_str = False, None
    try:
        print(f"Downloading {url}")
        r = requests.get(url)
        if r.status_code == 200:
            with pdf_file.open("wb") as f:
                f.write(r.content)
            downloaded = True
            dt_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z%z")
        else:
            print(f"An error occurred while downloading {url} Status: {r.status_code}")
    except Exception as e:
        print(f"An exception occurred while downloading {url}: {e}")

    time.sleep(0.2)
    return downloaded, dt_str


def get_pdf_path(doc_info, pdfs_dir):
    """Get the path where the PDF should be stored."""
    name = doc_info["name"]
    pdf_file = pdfs_dir / name
    return pdf_file


def download_pdf(pdfs_dir, doc_info):
    """Download a PDF if it doesn't already exist."""
    url = doc_info["url"]
    pdf_file = get_pdf_path(doc_info, pdfs_dir)

    if pdf_file.exists():
        print(f"PDF already exists: {pdf_file}")
        return pdf_file, None
    else:
        if not pdf_file.parent.exists():
            pdf_file.parent.mkdir(parents=True, exist_ok=True)
            
        d_success, d_utc_str = request_pdf(url, pdf_file)
        return (pdf_file, d_utc_str) if d_success else (None, d_utc_str)


def upload_internet_archive(doc_info, pdfs_dir):
    """Upload a document to the Internet Archive."""
    name = doc_info["name"]
    doc_id = name.split(".")[0]  # Remove file extension
    
    # Create description for the document
    descriptions = []
    descriptions.append(f'<td style="vertical-align: top"><b>House</b>:</td> <td style="vertical-align: top">{doc_info["house"]}</td>')
    descriptions.append(f'<td style="vertical-align: top"><b>Document Type</b>:</td> <td style="vertical-align: top">{doc_info["doc_type"]}</td>')
    descriptions.append(f'<td style="vertical-align: top"><b>Session</b>:</td> <td style="vertical-align: top">{doc_info["session"]}</td>')
    descriptions.append(f'<td style="vertical-align: top"><b>Year</b>:</td> <td style="vertical-align: top">{doc_info["year"]}</td>')
    
    # Add list_num only for UnstarredQuestions
    if doc_info["doc_type"] == "UnstarredQuestions" and "list_num" in doc_info:
        descriptions.append(f'<td style="vertical-align: top"><b>List Number</b>:</td> <td style="vertical-align: top">{doc_info["list_num"]}</td>')
    
    # Add date only for StarredQuestions
    if doc_info["doc_type"] == "StarredQuestions" and "date" in doc_info:
        descriptions.append(f'<td style="vertical-align: top"><b>Date</b>:</td> <td style="vertical-align: top">{doc_info["date"]}</td>')
    
    descriptions.append(f'<td style="vertical-align: top"><b>URL</b>:</td> <td style="vertical-align: top"><a href="{doc_info["url"]}">mls.org.in</a></td>')

    description = "<b>Maharashtra Legislature Secretariat Document</b>:<p>"
    description += "<table>\n<tr>" + "</tr>\n<tr>".join(descriptions) + "</tr>\n</table>\n"
    
    # Create metadata for the document
    title = f"Maharashtra Legislature: {doc_info['house']} - {doc_info['doc_type']} - {doc_info['year']}"
    if "session" in doc_info:
        title += f" - {doc_info['session']} Session"
    
    # Add list_num to title only for UnstarredQuestions
    if doc_info["doc_type"] == "UnstarredQuestions" and "list_num" in doc_info:
        title += f" - List {doc_info['list_num']}"
    
    # Add date to title only for StarredQuestions
    if doc_info["doc_type"] == "StarredQuestions" and "date" in doc_info:
        title += f" - Date {doc_info['date']}"
    
    # Create custom identifier
    # Use full names instead of codes
    house_name = doc_info["house"]
    doc_type_name = doc_info["doc_type"]
    
    # Add list_num or date to identifier based on doc_type
    identifier_suffix = ""
    if doc_info["doc_type"] == "UnstarredQuestions" and "list_num" in doc_info:
        identifier_suffix = f"-List{doc_info['list_num']}"
    elif doc_info["doc_type"] == "StarredQuestions" and "date" in doc_info:
        # Convert date to format without spaces or special characters
        date_str = doc_info["date"].replace(" ", "").replace("/", "").replace("-", "")
        identifier_suffix = f"-Date{date_str}"
    
    # Format: YEAR-HOUSE-SESSION-DOCTYPE-LIST_NUM/DATE
    session_name = doc_info.get("session", "General")
    identifier = f"{doc_info['year']}-{house_name}-{session_name}-{doc_type_name}{identifier_suffix}"
    
    metadata = {
        "collection": "maharashtramls",
        "mediatype": "texts",
        "title": title,
        "topics": "Maharashtra Legislature Secretariat Documents",
        "date": doc_info["year"],
        "creator": "Maharashtra Legislature Secretariat",
        "description": description,
        "subject": ["Maharashtra Legislature", doc_info["house"], doc_info["doc_type"]],
        "language": ["Marathi"],
        "house": doc_info["house"],
        "document_type": doc_info["doc_type"],
        "year": doc_info["year"],
        "url": doc_info["url"],
        "document_id": identifier,
    }
    
    if "session" in doc_info:
        metadata["session"] = doc_info["session"]
    
    # Add list_num only for UnstarredQuestions
    if doc_info["doc_type"] == "UnstarredQuestions" and "list_num" in doc_info:
        metadata["list_number"] = str(doc_info["list_num"])
    
    # Add date only for StarredQuestions
    if doc_info["doc_type"] == "StarredQuestions" and "date" in doc_info:
        metadata["date"] = doc_info["date"]
    
    ia_identifier = f"in.gov.maharashtra.mls.{identifier}"
    print(f"\tSaving on archive: {ia_identifier}")

    access_key = os.environ.get("IA_ACCESS_KEY", "")
    secret_key = os.environ.get("IA_SECRET_KEY", "")

    try:
        if access_key and secret_key:
            config = {"s3": {"access": access_key, "secret": secret_key}}
            item = ia.get_item(ia_identifier, config)
            if item.exists:
                archive_url = item.urls.details
                print(f"\tFound: {ia_identifier} {archive_url}")
                return archive_url, ia_identifier
            else:
                (pdf_path, download_date_utc) = download_pdf(pdfs_dir, doc_info)
                if pdf_path is not None and pdf_path.exists():
                    pdf_path = str(pdf_path)
                else:
                    print(f"\tDownload Failed: {ia_identifier}")
                    return None, None

            responses = item.upload(
                pdf_path,
                metadata=metadata,
                access_key=access_key,
                secret_key=secret_key,
                validate_identifier=True,
            )
        else:
            # Check if PDF exists locally
            pdf_path = get_pdf_path(doc_info, pdfs_dir)
            if not pdf_path.exists():
                (pdf_path, _) = download_pdf(pdfs_dir, doc_info)
                if pdf_path is None:
                    print(f"\tDownload Failed: {ia_identifier}")
                    return None, None
            
            item = ia.get_item(ia_identifier)
            responses = item.upload(str(pdf_path), metadata=metadata, validate_identifier=True)

    except Exception as e:
        print(f"Exception: {e}")
        return None, None

    archive_url = responses[0].url
    print(f"\tUploaded: {ia_identifier} {archive_url}")
    return archive_url, ia_identifier


def upload_all_internet_archive(documents_json_file, archive_json_file, pdfs_dir):
    """Upload all documents to the Internet Archive."""
    # Read documents.json
    documents = json.loads(documents_json_file.read_text())
    
    # Read archive.json if it exists
    archive_infos = json.loads(archive_json_file.read_text()) if archive_json_file.exists() else []
    
    # Create archive_old.json.gz if needed
    archive_old_json_file = archive_json_file.parent / f'{archive_json_file.stem}_old{archive_json_file.suffix}'
    if archive_json_file.exists() and not archive_old_json_file.exists():
        # Save current archive.json as archive_old.json
        archive_old_json_file.write_text(archive_json_file.read_text())
        print(f"Created backup: {archive_old_json_file}")
    
    # Get list of documents already uploaded to archive
    archive_ids = set(a.get("document_id", "") for a in archive_infos)
    
    print(f'Existing documents in archive: {len(archive_ids)}')
    
    # Find documents not yet uploaded
    new_docs = [doc for doc in documents if doc["name"].split(".")[0] not in archive_ids]
    
    print(f"*** New documents to upload: {len(new_docs)}")
    
    # Create pdfs_dir if it doesn't exist
    pdfs_dir.mkdir(exist_ok=True)
    
    start_time = time.time()
    for idx, doc in enumerate(new_docs):
        doc_id = doc["name"].split(".")[0]
        print(f"*** Uploading {doc_id} [{idx+1}/{len(new_docs)}]")
        
        archive_url, identifier = upload_internet_archive(doc, pdfs_dir)
        if archive_url:
            doc["archive_url"] = archive_url
            doc["identifier"] = identifier
            doc["upload_success"] = True
            print(f"\t**Success: {archive_url}\n")
        else:
            doc["upload_success"] = False
            print("\t!!Failed\n")
        
        archive_infos.append(doc)
        
        if (idx + 1) % BatchSize == 0:  # Save after every BatchSize uploads
            archive_json_file.write_text(json.dumps(archive_infos, indent=2))
            print('>>> Written Files <<<')
        
        if (time.time() - start_time) > FiveAndHalfHours:
            archive_json_file.write_text(json.dumps(archive_infos, indent=2))
            print('>>> Leaving as ran out of time')
            break
    
    # Final save
    if new_docs:
        archive_json_file.write_text(json.dumps(archive_infos, indent=2))
        print('>>> Final save completed <<<')


def main():
    """Main function to handle command line arguments and start the upload process."""
    if len(sys.argv) != 4:
        print("Usage: python upload_all_to_archive.py <documents_json_file> <archive_json_file> <pdfs_dir>")
        sys.exit(1)
    
    documents_json_file = Path(sys.argv[1])
    archive_json_file = Path(sys.argv[2])
    pdfs_dir = Path(sys.argv[3])
    
    upload_all_internet_archive(documents_json_file, archive_json_file, pdfs_dir)


if __name__ == "__main__":
    main()
