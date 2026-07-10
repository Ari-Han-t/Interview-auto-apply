from abc import ABC, abstractmethod
from typing import BinaryIO

class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file_name: str, file_data: BinaryIO, content_type: str) -> str:
        """Uploads a file and returns its URL/path"""
        pass

    @abstractmethod
    def download_file(self, file_url: str) -> bytes:
        """Downloads a file and returns its content bytes"""
        pass

    @abstractmethod
    def delete_file(self, file_url: str) -> bool:
        """Deletes a file"""
        pass
