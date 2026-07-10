import os
from typing import BinaryIO
from app.core.interfaces.storage import StorageProvider

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "data/uploads"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def upload_file(self, file_name: str, file_data: BinaryIO, content_type: str) -> str:
        file_path = os.path.join(self.base_dir, file_name)
        # Ensure directories exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(file_data.read())
        return file_path

    def download_file(self, file_url: str) -> bytes:
        if not os.path.exists(file_url):
            raise FileNotFoundError(f"File {file_url} not found.")
        with open(file_url, "rb") as f:
            return f.read()

    def delete_file(self, file_url: str) -> bool:
        if os.path.exists(file_url):
            os.remove(file_url)
            return True
        return False
