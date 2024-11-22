import os
import subprocess
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

console = Console()

def get_processing_status(audio_file):
    """Check if file has been processed (has labels and description)"""
    base_name = Path(audio_file).stem
    labels_file = Path('./labels') / f"{base_name}_labels.txt"
    desc_file = Path('./descriptions') / f"{base_name}_description.txt"
    
    has_labels = labels_file.exists()
    has_desc = desc_file.exists() and desc_file.stat().st_size > 0
    
    if has_labels and has_desc:
        return "[green]DONE[/green]"
    elif has_labels or has_desc:
        return "[yellow]PARTIAL[/yellow]"
    return "[red]TODO[/red]"

def get_audio_duration(file_path):
    """Get duration of audio file in minutes:seconds format"""
    try:
        if str(file_path).lower().endswith('.mp3'):
            try:
                # First try with mutagen.mp3
                audio = MP3(file_path)
            except Exception as mp3_error:
                try:
                    # If MP3 fails, try with mutagen.File
                    audio = File(file_path)
                    if audio is None:
                        print(f"Warning: Could not read MP3 file {file_path}: {str(mp3_error)}")
                        return "--:--"
                except Exception as file_error:
                    print(f"Warning: Both MP3 and File readers failed for {file_path}")
                    return "--:--"
        elif str(file_path).lower().endswith('.wav'):
            try:
                audio = WAVE(file_path)
            except Exception as wave_error:
                print(f"Warning: Could not read WAV file {file_path}: {str(wave_error)}")
                return "--:--"
        else:
            return "--:--"
            
        duration = getattr(audio.info, 'length', None)
        if duration is None:
            return "--:--"
            
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except Exception as e:
        print(f"Warning: Could not read duration for {file_path}: {str(e)}")
        return "--:--"

def create_table(audio_files, page=1, per_page=10):
    """Creates a paginated rich table of audio files with status"""
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_files = audio_files[start_idx:end_idx]
    
    table = Table(title="Available Audio Files", box=box.ROUNDED)
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Filename", style="green")
    table.add_column("Duration", style="yellow")
    table.add_column("Type", style="blue")
    
    audio_dir = Path('./audio')
    for i, file in enumerate(current_files, start_idx + 1):
        file_path = audio_dir / file
        duration = get_audio_duration(file_path)
        status = get_processing_status(file)
        file_type = file_path.suffix.upper()[1:]  # Remove dot and uppercase
        table.add_row(str(i), status, file, duration, file_type)
    
    total_pages = (len(audio_files) + per_page - 1) // per_page
    if total_pages > 1:
        table.caption = f"Page {page} of {total_pages} (use 'n' for next, 'p' for previous)"
    
    return table, total_pages

def create_menu():
    """Creates a rich menu panel"""
    menu_text = """
[cyan]1.[/cyan] Process Audio File (Edit Labels & Description)
[cyan]2.[/cyan] Edit Labels Only
[cyan]3.[/cyan] Edit Description Only
[cyan]q.[/cyan] Quit
    """
    return Panel(menu_text, title="🎵 Actions", border_style="blue", box=box.ROUNDED)

def get_file_info(audio_file):
    """Get comprehensive file information"""
    file_path = Path('./audio') / audio_file
    try:
        if file_path.suffix.lower() == '.mp3':
            audio = MP3(file_path)
            info = {
                'format': 'MP3',
                'bitrate': f"{int(audio.info.bitrate / 1000)}kbps",
                'sample_rate': f"{int(audio.info.sample_rate / 1000)}kHz",
                'duration': get_audio_duration(file_path)
            }
        elif file_path.suffix.lower() == '.wav':
            audio = WAVE(file_path)
            info = {
                'format': 'WAV',
                'channels': audio.info.channels,
                'sample_rate': f"{int(audio.info.sample_rate / 1000)}kHz",
                'duration': get_audio_duration(file_path)
            }
        else:
            info = {'format': 'Unknown'}
        return info
    except Exception as e:
        print(f"Warning: Could not read file info for {file_path}: {str(e)}")
        return {'format': 'Error'}

def display_current_file(audio_file):
    """Creates a panel showing current file info"""
    file_info = get_file_info(audio_file)
    
    info = Text()
    info.append("File: ", style="blue")
    info.append(audio_file, style="green")
    info.append("\n\nFormat: ", style="blue")
    info.append(file_info.get('format', 'Unknown'), style="yellow")
    
    if 'duration' in file_info:
        info.append("\nDuration: ", style="blue")
        info.append(file_info['duration'], style="yellow")
    
    if 'bitrate' in file_info:
        info.append("\nBitrate: ", style="blue")
        info.append(file_info['bitrate'], style="yellow")
    
    if 'sample_rate' in file_info:
        info.append("\nSample Rate: ", style="blue")
        info.append(file_info['sample_rate'], style="yellow")
    
    desc_file = Path('./descriptions') / f"{Path(audio_file).stem}_description.txt"
    if desc_file.exists():
        with open(desc_file) as f:
            content = f.read()
            current_desc = content.split('description:\n')[1].split('genre-tags:')[0].strip()
            current_tags = content.split('genre-tags:')[1].split('processed:')[0].strip()
            
        info.append("\n\nDescription: ", style="blue")
        info.append(current_desc or "None", style="yellow")
        info.append("\nGenre Tags: ", style="blue")
        info.append(current_tags or "None", style="yellow")
    
    return Panel(info, title="Current File Info", border_style="green", box=box.ROUNDED)
def get_confirmation(prompt_text):
    """Get yes/no confirmation with colored options"""
    return Confirm.ask(prompt_text, show_default=True, default=True)

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_user_input(prompt_text):
    """Get user input with rich formatting"""
    return Prompt.ask(prompt_text)

def create_apple_script(labels_path):
    """
    Creates an AppleScript to automate Audacity label import with corrected menu hierarchy
    """
    return f'''
    tell application "Audacity"
        activate
    end tell
    
    delay 0.5
    
    tell application "System Events"
        tell process "Audacity"
            -- Click File menu
            click menu item "Import" of menu 1 of menu bar item "File" of menu bar 1
            
            -- Click Labels... in the submenu
            delay 0.5
            click menu item "Labels..." of menu 1 of menu item "Import" of menu 1 of menu bar item "File" of menu bar 1
        end tell
    end tell
    
    delay 1
    
    tell application "System Events"
        keystroke "G" using {{command down, shift down}}
        delay 0.5
        keystroke "{labels_path}"
        delay 0.5
        keystroke return
        delay 0.5
        keystroke return
    end tell
    '''

def open_in_audacity(audio_file):
    """
    Opens an audio file and its corresponding labels file in Audacity
    """
    # Get the full paths
    audio_path = os.path.abspath(audio_file)
    labels_path = os.path.abspath(f"./labels/{os.path.basename(audio_file)}_labels.txt")
    
    if not os.path.exists(labels_path):
        print(f"Labels file not found: {labels_path}")
        return False
        
    try:
        if sys.platform == 'darwin':  # macOS
            # First, open the audio file
            subprocess.Popen(['open', '-a', 'Audacity', audio_path])
            time.sleep(2)  # Give Audacity time to open
            
            # Create and execute AppleScript for labels import
            apple_script = create_apple_script(labels_path)
            with open('/tmp/audacity_script.scpt', 'w') as f:
                f.write(apple_script)
            
            subprocess.run(['osascript', '/tmp/audacity_script.scpt'])
            os.remove('/tmp/audacity_script.scpt')  # Clean up
            
        elif sys.platform == 'win32':  # Windows
            subprocess.Popen(['start', 'Audacity.exe', audio_path], shell=True)
            print("\nAutomatic label import not supported on Windows.")
            print(f"Please manually import labels from: {labels_path}")
            
        else:  # Linux
            subprocess.Popen(['audacity', audio_path])
            print("\nAutomatic label import not supported on Linux.")
            print(f"Please manually import labels from: {labels_path}")
        
        print(f"\nAudio file opened in Audacity: {audio_path}")
        print(f"Labels file location: {labels_path}")
        
        if sys.platform != 'darwin':
            print("\nTo import labels manually in Audacity:")
            print("1. File > Import > Labels...")
            print(f"2. Navigate to: {labels_path}")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    
def create_description_file(audio_file):
    """Creates or updates a description file for an audio file"""
    desc_dir = Path('./descriptions')
    desc_dir.mkdir(exist_ok=True)
    
    base_name = Path(audio_file).stem
    desc_file = desc_dir / f"{base_name}_description.txt"
    
    if not desc_file.exists():
        with open(desc_file, 'w') as f:
            f.write("description:\ngenre-tags:\nprocessed: true")
    return desc_file

def update_processing_status(audio_file):
    """Updates the processing status in the description file"""
    desc_file = create_description_file(audio_file)
    
    with open(desc_file, 'r') as f:
        content = f.read()
    
    if 'processed:' not in content:
        content += '\nprocessed: true'
    
    with open(desc_file, 'w') as f:
        f.write(content)
        
def edit_description(audio_file):
    """Manages the description editing process for an audio file"""
    desc_file = create_description_file(audio_file)
    
    with open(desc_file) as f:
        content = f.read()
        current_desc = content.split('description:\n')[1].split('genre-tags:')[0].strip()
        tags_section = content.split('genre-tags:\n')[1]
        current_tags = tags_section.split('processed:')[0].strip()
    
    print(f"\nWorking on: {audio_file}")
    
    print(f"\nCurrent description: {current_desc}")
    new_desc = input("Enter new description as a single line (press Enter to keep current): ").strip()
    if not new_desc:
        new_desc = current_desc
    
    print(f"\nCurrent genre tags: {current_tags}")
    new_tags = input("Enter new genre tags as a comma separated list (press Enter to keep current): ").strip()
    if not new_tags:
        new_tags = current_tags
    
    with open(desc_file, 'w') as f:
        f.write(f"description:\n{new_desc}\ngenre-tags:\n{new_tags}\nprocessed: true")
    
    return True

def create_export_apple_script(labels_path):
    """Creates AppleScript to export labels from Audacity, with Select All before export"""
    return f'''
    tell application "Audacity"
        activate
    end tell

    delay 1
    
    tell application "System Events"
        tell process "Audacity"
            -- Select All content first
            keystroke "a" using {{command down}}
            delay 0.5  -- Ensure selection completes
            
            click menu bar item "File" of menu bar 1
            delay 0.5

            click menu item "Export Other" of menu "File" of menu bar 1
            delay 0.5

            click menu item "Export Labels..." of menu 1 of menu item "Export Other" of menu "File" of menu bar 1
        end tell
    end tell

    delay 1

    tell application "System Events"
        keystroke "G" using {{command down, shift down}}
        delay 0.5
        keystroke "{labels_path}"
        delay 0.5
        keystroke return
        delay 0.5
        keystroke return
        delay 0.5

        -- Handle Replace dialog
        tell application "System Events"
            -- Hit "Tab" and then "Space" to press "Replace"
            keystroke tab
            delay 0.5
            keystroke space
            delay 0.5
        end tell

        delay 1

        tell process "Audacity"
            -- Close Audacity without saving
            click menu bar item "File" of menu bar 1
            delay 0.5
            click menu item "Close Project" of menu "File" of menu bar 1
            delay 0.5
            tell application "System Events"
                -- Use "Shift+Tab" and then "Space" to close without saving
                key code 48 using shift down -- Shift + Tab
                delay 0.5
                keystroke space
                delay 0.5
            end tell
        end tell
    end tell
    '''
    
def export_labels(labels_path):
    """Exports labels from Audacity back to file"""
    try:
        if sys.platform == 'darwin':
            apple_script = create_export_apple_script(labels_path)
            with open('/tmp/audacity_export_script.scpt', 'w') as f:
                f.write(apple_script)
            
            subprocess.run(['osascript', '/tmp/audacity_export_script.scpt'])
            os.remove('/tmp/audacity_export_script.scpt')
            return True
    except Exception as e:
        console.print(f"[red]Error exporting labels: {str(e)}[/red]")
        return False
    
def process_audio_file(audio_file, audio_dir, action):
    """Process a single audio file with labels and descriptions"""
    clear_screen()
    console.print(display_current_file(audio_file))
    
    if action in ['1', '2']:
        # First show the status while opening Audacity
        with console.status("[bold yellow]Opening in Audacity...", spinner="dots"):
            success = open_in_audacity(os.path.join(audio_dir, audio_file))
            time.sleep(2)  # Give Audacity time to open
        
        # After Audacity is opened, clear the status and show the prompt
        if success:
            console.print("\n")  # Add some spacing
            if get_confirmation("\n✏️  Have you finished editing labels?"):
                labels_path = os.path.abspath(f"./labels/{os.path.basename(audio_file)}_labels.txt")
                with console.status("[bold yellow]Exporting updated labels...", spinner="dots"):
                    if export_labels(labels_path):
                        update_processing_status(audio_file)
    
    if action in ['1', '3']:
        console.print("\n[bold yellow]Editing description...[/bold yellow]")
        if edit_description(audio_file):
            update_processing_status(audio_file)
        

def main():
    audio_dir = Path('./audio')
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith(('.mp3', '.wav'))]
    
    if not audio_files:
        console.print(Panel("[red]No audio files found in ./audio directory[/red]", 
                          title="Error", border_style="red", box=box.ROUNDED))
        return
    
    page = 1
    per_page = 10
    
    while True:
        try:
            clear_screen()
            console.print(Panel("🎧 Audio Processing Tool", style="bold blue", box=box.ROUNDED))
            
            table, total_pages = create_table(audio_files, page, per_page)
            console.print(table)
            console.print(create_menu())
            
            action = Prompt.ask("\nChoose an action", choices=['1', '2', '3', 'q', 'n', 'p'])
            
            if action.lower() == 'q':
                console.print("\n\n[green]Session Completed![/green]\n\n\n")
                break
            
            if action == 'n' and page < total_pages:
                page += 1
                continue
            elif action == 'p' and page > 1:
                page -= 1
                continue
            elif action in ['n', 'p']:
                continue
            
            file_num = Prompt.ask("Enter file number")
            if file_num.lower() == 'q':
                break
            
            file_index = int(file_num) - 1
            if 0 <= file_index < len(audio_files):
                process_audio_file(audio_files[file_index], audio_dir, action)
                if get_confirmation("\n➡️  Process another file?"):
                    continue
                else:
                    console.print("\n\n[green]Session Completed![/green]\n\n\n")
                break
            else:
                console.print(Panel("[red]Invalid file number![/red]", 
                                  title="Error", border_style="red", box=box.ROUNDED))
                
        except ValueError:
            console.print(Panel("[red]Please enter a valid number![/red]", 
                              title="Error", border_style="red", box=box.ROUNDED))
        except KeyboardInterrupt:
            console.print("\n\n[green]Session Completed![/green]\n\n\n")
            break
        except Exception as e:
            console.print(Panel(f"[red]Error: {str(e)}[/red]", 
                              title="Error", border_style="red", box=box.ROUNDED))

if __name__ == "__main__":
    main()