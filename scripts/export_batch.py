import os
import shutil
import webbrowser
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Confirm
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

console = Console()

SCOPES = ['https://www.googleapis.com/auth/drive.file']
PARENT_FOLDER_ID = '1venfIOyo5BeQPiXnUJhTRLV4N2y_lszQ'
LABELS_FOLDER_ID = '1G4P-ltl0O0Q5wd0HPxjlVwjkR7M0pYb6'
DESCRIPTIONS_FOLDER_ID = '1q2RErYYsrCPGM-2aqIZCLS7ylqm_wyUQ'

def get_google_drive_service():
    """Gets Google Drive service using service account credentials."""
    try:
        # Path to your service account credentials JSON file
        SERVICE_ACCOUNT_FILE = './secrets/service-account.json'
        
        # Create credentials using service account
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        # Build and return the service
        return build('drive', 'v3', credentials=credentials)
        
    except Exception as e:
        console.print(f"[red]Error setting up Google Drive service: {str(e)}[/red]")
        raise

def create_folder_if_not_exists(service, folder_name, parent_id=None):
    """Creates a folder in Google Drive if it doesn't exist."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    results = service.files().list(q=query).execute()
    items = results.get('files', [])
    
    if not items:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0]['id']

def upload_to_drive(service, file_path, folder_id):
    """Uploads a file to Google Drive in the specified folder."""
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(
        file_path,
        mimetype='text/plain',
        resumable=True
    )
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    return file.get('id')

def get_folder_url(folder_id):
    """Returns the Google Drive URL for a folder."""
    return f"https://drive.google.com/drive/folders/{folder_id}"

def cleanup_directories():
    """Cleans up audio, labels, and descriptions directories."""
    try:
        # Clean up audio directory
        audio_path = Path('./audio')
        for audio_file in audio_path.glob('*'):
            if audio_file.suffix.lower() in ['.mp3', '.wav']:
                audio_file.unlink()
        
        # Clean up labels directory
        labels_path = Path('./labels')
        for label_file in labels_path.glob('*_labels.txt'):
            label_file.unlink()
            
        # Clean up descriptions directory
        desc_path = Path('./descriptions')
        for desc_file in desc_path.glob('*_description.txt'):
            desc_file.unlink()
            
        return True
    except Exception as e:
        console.print(f"[red]Error during cleanup: {str(e)}[/red]")
        return False

def export_batch():
    """Main function to handle batch export and cleanup."""
    try:
        # Initialize Google Drive service
        with console.status("[bold yellow]Connecting to Google Drive...") as status:
            service = get_google_drive_service()
            
        # Export labels and descriptions
        labels_path = Path('./labels')
        desc_path = Path('./descriptions')
        
        with Progress() as progress:
            # Upload label files
            label_files = list(labels_path.glob('*_labels.txt'))
            label_task = progress.add_task("[cyan]Uploading labels...", total=len(label_files))
            
            for label_file in label_files:
                upload_to_drive(service, str(label_file), LABELS_FOLDER_ID)
                progress.update(label_task, advance=1)
                
            # Upload description files
            desc_files = list(desc_path.glob('*_description.txt'))
            desc_task = progress.add_task("[cyan]Uploading descriptions...", total=len(desc_files))
            
            for desc_file in desc_files:
                upload_to_drive(service, str(desc_file), DESCRIPTIONS_FOLDER_ID)
                progress.update(desc_task, advance=1)
        
        # Get folder URLs
        labels_url = get_folder_url(LABELS_FOLDER_ID)
        descriptions_url = get_folder_url(DESCRIPTIONS_FOLDER_ID)
        
        console.print(Panel(
            "[yellow]Please verify the uploaded files in your browser.[/yellow]\n"
            f"[blue]Labels folder:[/blue] {labels_url}\n"
            f"[blue]Descriptions folder:[/blue] {descriptions_url}\n\n"
            "[green]Files uploaded:[/green]\n"
            f"  - Labels: {len(label_files)}\n"
            f"  - Descriptions: {len(desc_files)}",
            title="Verify Uploads",
            border_style="yellow"
        ))
        
        # Open both folders in browser
        webbrowser.open(labels_url)
        webbrowser.open(descriptions_url)
        
        if Confirm.ask("\n✓ Have you verified the files are uploaded correctly?"):
            # Cleanup after verification
            with console.status("[bold yellow]Cleaning up local files...") as status:
                if cleanup_directories():
                    console.print(Panel(
                        "[green]Batch export completed successfully![/green]\n"
                        "✓ Files uploaded to Google Drive\n"
                        "✓ Local files cleaned up",
                        title="Export Complete",
                        border_style="green"
                    ))
                    return True
                else:
                    console.print(Panel(
                        "[red]Error during cleanup![/red]\n"
                        "[yellow]Files were uploaded but local cleanup failed.[/yellow]",
                        title="Warning",
                        border_style="red"
                    ))
                    return False
        else:
            console.print(Panel(
                "[yellow]Export cancelled. Local files preserved.[/yellow]",
                title="Export Cancelled",
                border_style="yellow"
            ))
            return False
            
    except Exception as e:
        console.print(Panel(
            f"[red]Error during export: {str(e)}[/red]",
            title="Error",
            border_style="red"
        ))
        return False

if __name__ == "__main__":
    export_batch()