import requests
import hashlib
import os
from urllib.parse import urlparse
from typing import Set, Optional

class FileDownloader:
    """
    A class to handle file downloads with built-in precautions,
    duplicate file detection, and header checks.
    """

    def __init__(self, download_directory: str = "Fetched_Images"):
        """
        Initializes the downloader.

        Args:
            download_directory: The directory to save downloaded files.
        """
        self.download_directory = download_directory
        self.downloaded_hashes: Set[str] = set()
        # Create the download directory if it doesn't exist
        os.makedirs(self.download_directory, exist_ok=True)

    def _calculate_hash(self, filepath: str, block_size: int = 65536) -> Optional[str]:
        """
        Calculates the SHA256 hash of a file. This is used as a unique identifier
        for duplicate detection.

        Args:
            filepath: The path to the file.
            block_size: The size of chunks to read for hashing.

        Returns:
            The SHA256 hash as a hex string, or None if an error occurs.
        """
        sha256 = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    sha256.update(block)
        except IOError as e:
            print(f"Error reading file to calculate hash: {e}")
            return None
        return sha256.hexdigest()

    def _get_filename(self, headers: dict, url: str) -> str:
        """
        Extracts a filename from HTTP headers or generates one from the URL.

        Args:
            headers: The dictionary of HTTP response headers.
            url: The original URL of the file.

        Returns:
            A sanitized filename string.
        """
        content_disposition = headers.get('Content-Disposition')
        if content_disposition:
            # Look for a filename in the Content-Disposition header
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('\"\'')
                return filename

        # If no filename in headers, generate one from the URL path
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        if not filename or '.' not in filename:
            # Default to a generic name if a proper one can't be extracted
            return "downloaded_file.jpg"

        return filename

    def download_file(self, url: str) -> None:
        """
        Downloads a file from a given URL with precautions.

        Args:
            url: The URL of the file to download.
        """
        print(f"\n--- Processing URL: {url} ---")
        try:
            # Step 1: Check HTTP headers for precautions
            # Use a HEAD request to get headers without downloading the full content
            head_response = requests.head(url, timeout=5)
            head_response.raise_for_status()

            headers = head_response.headers
            print(f"[+] Found `Content-Type`: {headers.get('Content-Type')}")
            print(f"[+] Found `Content-Length`: {headers.get('Content-Length')}")
            print(f"[+] Found `Content-Disposition`: {headers.get('Content-Disposition')}")
            
            # Precaution 1: Verify Content-Type
            content_type = headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                print(f"[-] Precautionary warning: Expected an image, but got '{content_type}'. Skipping download.")
                return

            # Precaution 2: Check for excessively large file size (e.g., > 20 MB)
            content_length_str = headers.get('Content-Length', '0')
            content_length = int(content_length_str) if content_length_str.isdigit() else 0
            if content_length > 20 * 1024 * 1024:
                print(f"[-] Precautionary warning: File size ({content_length} bytes) is too large. Skipping download.")
                return

            # Precaution 3: Get a sanitized filename
            filename = self._get_filename(headers, url)
            
            # A simple check for dangerous file extensions
            if filename.endswith(('.exe', '.bat', '.sh', '.js')):
                print(f"[-] Precautionary warning: The file '{filename}' has a potentially dangerous extension. Skipping download.")
                return

            filepath = os.path.join(self.download_directory, filename)

            # Step 2: Download the file
            print(f"[+] Headers OK. Proceeding with download...")
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            # Save the file in a temporary location to check for duplicates
            temp_filepath = f"{filepath}.temp"
            with open(temp_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Step 3: Prevent duplicate images by checking hash
            file_hash = self._calculate_hash(temp_filepath)
            if file_hash in self.downloaded_hashes:
                print(f"[+] Duplicate image detected! Deleting the file.")
                os.remove(temp_filepath)
                return
            else:
                self.downloaded_hashes.add(file_hash)
                # If not a duplicate, rename the temp file to the final name
                os.rename(temp_filepath, filepath)
                print(f"[+] Successfully fetched and saved: {filename}")
                print(f"[+] Image saved to {filepath}")

        except requests.exceptions.RequestException as e:
            print(f"[-] Connection error: {e}")
        except Exception as e:
            print(f"[-] An unexpected error occurred: {e}")

def main():
    """
    Main function to run the FileDownloader demonstration.
    """
    print("Welcome to the Ubuntu Image Fetcher\n")
    print("This program will fetch Ubuntu images from the provided URLs.")
    downloader = FileDownloader()

    # Note: These are example URLs. The code will handle various scenarios.
    urls_to_test = [
        "https://images.pexels.com/photos/14421190/pexels-photo-14421190.jpeg", # A valid image
        "https://images.pexels.com/photos/33668617/pexels-photo-33668617.jpeg", # Another valid image
        "https://images.pexels.com/photos/14421190/pexels-photo-14421190.jpeg", # A duplicate of the first one
        "https://exam.com/not_an_image_file.txt", # Will be rejected due to wrong Content-Type
        "https://exam.com/script.js", # Will be rejected due to dangerous file extension
    ]

    for url in urls_to_test:
        downloader.download_file(url)

if __name__ == "__main__":
    main()
