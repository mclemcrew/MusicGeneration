#!/usr/bin/env python3

import io
import json
import shutil
from pathlib import Path
import select
import subprocess as sp
import sys
from typing import Dict, Tuple, Optional, IO
import os
import time
import torch
from tqdm import tqdm

class BatchStemSeparator:
    def __init__(self, input_path: str, output_path: str, batch_size: int = 5):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.batch_size = batch_size
        self.extensions = ["mp3", "wav", "ogg", "flac"]
        self.mp3 = True
        self.mp3_rate = 320
        self.float32 = False
        self.int24 = False
        
        # Progress tracking file
        self.progress_file = self.output_path / "progress.json"
        self.processed_files = self.load_progress()
        
        # Create output directory if it doesn't exist
        self.output_path.mkdir(parents=True, exist_ok=True)

    def load_progress(self) -> set:
        """Load the set of already processed files."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return set(json.load(f))
        return set()

    def save_progress(self):
        """Save the current progress."""
        with open(self.progress_file, 'w') as f:
            json.dump(list(self.processed_files), f)

    def find_files(self, in_path: Path) -> list:
        """Find all unprocessed audio files with supported extensions."""
        files = []
        for file in in_path.iterdir():
            if (file.suffix.lower().lstrip(".") in self.extensions and 
                file.name not in self.processed_files):
                files.append(file)
        return files

    def _copy_process_streams(self, process: sp.Popen):
        """Handle process output streaming."""
        def raw(stream: Optional[IO[bytes]]) -> IO[bytes]:
            assert stream is not None
            if isinstance(stream, io.BufferedIOBase):
                stream = stream.raw
            return stream

        p_stdout, p_stderr = raw(process.stdout), raw(process.stderr)
        stream_by_fd: Dict[int, Tuple[IO[bytes], IO[str]]] = {
            p_stdout.fileno(): (p_stdout, sys.stdout),
            p_stderr.fileno(): (p_stderr, sys.stderr),
        }
        fds = list(stream_by_fd.keys())

        while fds:
            ready, _, _ = select.select(fds, [], [])
            for fd in ready:
                p_stream, std = stream_by_fd[fd]
                raw_buf = p_stream.read(2 ** 16)
                if not raw_buf:
                    fds.remove(fd)
                    continue
                buf = raw_buf.decode()
                std.write(buf)
                std.flush()

    def separate_batch(self, model_name: str, temp_output: Path, files: list) -> bool:
        """Run separation for a batch of files."""
        cmd = ["python3", "-m", "demucs.separate", 
               "-o", str(temp_output), 
               "-n", model_name,
               "--mps" if torch.backends.mps.is_available() else ""]  # Use MPS backend on M-series chips
        
        if self.mp3:
            cmd += ["--mp3", f"--mp3-bitrate={self.mp3_rate}"]
        if self.float32:
            cmd += ["--float32"]
        if self.int24:
            cmd += ["--int24"]

        file_paths = [str(f) for f in files]
        if not file_paths:
            return True

        print(f"Processing batch with {model_name}:")
        print('\n'.join(file_paths))
        
        try:
            p = sp.Popen(cmd + file_paths, stdout=sp.PIPE, stderr=sp.PIPE)
            self._copy_process_streams(p)
            p.wait()
            return p.returncode == 0
        except Exception as e:
            print(f"Error processing batch: {e}")
            return False

    def organize_stems_for_file(self, temp_dir: Path, filename: str):
        """Organize stems for a single file."""
        try:
            model_output_ft = temp_dir / "htdemucs_ft" / filename
            model_output_6s = temp_dir / "htdemucs_6s" / filename
            
            if not model_output_ft.exists() or not model_output_6s.exists():
                return False

            # Create output directory named after the audio file
            output_dir = self.output_path / filename
            output_dir.mkdir(parents=True, exist_ok=True)

            # Copy stems from htdemucs_ft
            for stem in ['bass', 'drums', 'vocals']:
                stem_path = model_output_ft / f"{stem}.mp3"
                if stem_path.exists():
                    shutil.copy2(stem_path, output_dir / f"{stem}.mp3")

            # Copy stems from htdemucs_6s
            for stem in ['other', 'guitar', 'piano']:
                stem_path = model_output_6s / f"{stem}.mp3"
                if stem_path.exists():
                    shutil.copy2(stem_path, output_dir / f"{stem}.mp3")

            return True
        except Exception as e:
            print(f"Error organizing stems for {filename}: {e}")
            return False

    def process_batch(self, batch: list, temp_dir: Path):
        """Process a batch of files through both models."""
        print(f"\nProcessing batch of {len(batch)} files...")
        
        # Process with first model
        if not self.separate_batch("htdemucs_ft", temp_dir, batch):
            print("Failed to process batch with htdemucs_ft")
            return False

        # Process with second model
        if not self.separate_batch("htdemucs_6s", temp_dir, batch):
            print("Failed to process batch with htdemucs_6s")
            return False

        # Organize stems for each file in the batch
        for file in batch:
            if self.organize_stems_for_file(temp_dir, file.stem):
                self.processed_files.add(file.name)
                self.save_progress()
            else:
                print(f"Failed to organize stems for {file.name}")

        return True

    def process(self):
        """Run the complete separation and organization process."""
        files = self.find_files(self.input_path)
        if not files:
            print("No unprocessed files found.")
            return

        print(f"Found {len(files)} files to process")
        
        # Process files in batches
        for i in range(0, len(files), self.batch_size):
            batch = files[i:i + self.batch_size]
            
            # Create temporary directory for this batch
            temp_dir = Path(f"temp_separation_batch_{i}")
            temp_dir.mkdir(exist_ok=True)

            try:
                print(f"\nProcessing batch {i//self.batch_size + 1} of {(len(files)-1)//self.batch_size + 1}")
                self.process_batch(batch, temp_dir)
            except Exception as e:
                print(f"Error processing batch: {e}")
            finally:
                # Clean up temporary files
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        print("\nProcessing complete!")
        print(f"Successfully processed {len(self.processed_files)} files")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process audio files using multiple Demucs models")
    parser.add_argument("input_path", help="Directory containing input audio files")
    parser.add_argument("output_path", help="Directory for output stems")
    parser.add_argument("--batch-size", type=int, default=5, 
                      help="Number of files to process in each batch")
    
    args = parser.parse_args()
    
    separator = BatchStemSeparator(args.input_path, args.output_path, args.batch_size)
    separator.process()