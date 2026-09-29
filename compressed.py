import os
import hashlib
import gzip
import shutil
import time

# Directory Setup
INPUT_DIR = "sample_10mb"
OUTPUT_DIR = "sample_5mb"
ALLOWED_EXTENSIONS = ('.sql', '.lz4', '.gz', '.zst', '.manifest', '.conf')

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_file_hash(filepath):
    """Calculates SHA-256 hash to verify data integrity."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def compress_gzip(src_path, dest_path):
    """Compresses file using Gzip."""
    with open(src_path, 'rb') as f_in:
        with gzip.open(dest_path, 'wb', compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)

def decompress_gzip(src_path, dest_path):
    """Decompresses Gzip file for validation."""
    with gzip.open(src_path, 'rb') as f_in:
        with open(dest_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

def process_backups():
    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith(ALLOWED_EXTENSIONS):
            continue
            
        src_file = os.path.join(INPUT_DIR, filename)
        compressed_file = os.path.join(OUTPUT_DIR, f"{filename}.gz")
        decompressed_file = os.path.join(OUTPUT_DIR, f"temp_{filename}")
        
        # 1. Store original checksum & size
        original_hash = get_file_hash(src_file)
        original_size = os.path.getsize(src_file)
        
        # 2. Measure Compression Time & Execute
        start_compress = time.time()
        compress_gzip(src_file, compressed_file)
        compress_time = time.time() - start_compress
        
        compressed_size = os.path.getsize(compressed_file)
        ratio = (1 - (compressed_size / original_size)) * 100 if original_size > 0 else 0
        
        # 3. Integrity Verification (Decompress & Compare Hashes)
        decompress_gzip(compressed_file, decompressed_file)
        decompressed_hash = get_file_hash(decompressed_file)
        
        is_valid = (original_hash == decompressed_hash)
        
        # Cleanup temporary file used for testing
        if os.path.exists(decompressed_file):
            os.remove(decompressed_file)
            
        # 4. Display Results
        print(f"File: {filename}")
        print(f"  Original Size:   {original_size / 1024:.2f} KB")
        print(f"  Compressed Size: {compressed_size / 1024:.2f} KB ({ratio:.2f}% reduction)")
        print(f"  Compression Time: {compress_time:.4f} sec")
        print(f"  Integrity Match:  {'SUCCESS (No Data Loss)' if is_valid else 'FAILED'}\n")

if __name__ == "_main_":
    process_backups()