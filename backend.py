import os
import zipfile
import hashlib
import time
import tempfile
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = "backup_compressor_secret_key"

# Configuration Directories
BASE_DIR = os.path.dirname(os.path.abspath(_file_))
INPUT_DIR = os.path.join(BASE_DIR, "input_backups")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_backups")

# Ensure required directories exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Allowed database backup extensions
SUPPORTED_EXTENSIONS = ('.sql', '.lz4', '.gz', '.zst', '.manifest', '.conf')

def compute_sha256(file_path):
    """Calculates SHA-256 checksum of a file for data integrity verification."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def compress_and_verify(input_filepath, output_filepath, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6):
    """
    Compresses a file into a ZIP archive, decompresses it to a temp dir,
    and compares SHA-256 hashes to guarantee 100% data integrity.
    """
    orig_hash = compute_sha256(input_filepath)
    orig_size = os.path.getsize(input_filepath)
    filename = os.path.basename(input_filepath)

    start_time = time.time()
    
    # 1. Compress
    with zipfile.ZipFile(output_filepath, 'w', compression=compress_type, compresslevel=compresslevel) as zipf:
        zipf.write(input_filepath, arcname=filename)
    
    elapsed_time = round(time.time() - start_time, 3)
    compressed_size = os.path.getsize(output_filepath)
    
    # Calculate storage space saved
    bytes_saved = orig_size - compressed_size
    space_saved_percent = round((bytes_saved / orig_size) * 100, 2) if orig_size > 0 else 0.0

    # 2. Decompress and Verify Integrity
    integrity_verified = False
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(output_filepath, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        extracted_filepath = os.path.join(temp_dir, filename)
        extracted_hash = compute_sha256(extracted_filepath)
        
        if orig_hash == extracted_hash:
            integrity_verified = True

    return {
        "filename": filename,
        "original_size": orig_size,
        "compressed_size": compressed_size,
        "space_saved_percent": space_saved_percent,
        "execution_time": elapsed_time,
        "verified": integrity_verified
    }

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    
    # List available supported files in input directory
    all_files = os.listdir(INPUT_DIR)
    supported_files = [f for f in all_files if f.lower().endswith(SUPPORTED_EXTENSIONS)]

    if request.method == "POST":
        selected_compression = request.form.get("algo", "deflate")
        comp_level = int(request.form.get("level", 6))

        # Map compression algorithm choice
        if selected_compression == "lzma":
            comp_type = zipfile.ZIP_LZMA
            comp_level = None  # LZMA handles level internally in zipfile module
        elif selected_compression == "bzip2":
            comp_type = zipfile.ZIP_BZIP2
        else:
            comp_type = zipfile.ZIP_DEFLATED

        if not supported_files:
            flash("No supported backup files found in the input directory.", "warning")
            return redirect(url_for("index"))

        for filename in supported_files:
            input_path = os.path.join(INPUT_DIR, filename)
            output_archive_name = f"{filename}.zip"
            output_path = os.path.join(OUTPUT_DIR, output_archive_name)

            try:
                res = compress_and_verify(input_path, output_path, compress_type=comp_type, compresslevel=comp_level)
                results.append(res)
            except Exception as e:
                results.append({
                    "filename": filename,
                    "error": str(e),
                    "verified": False
                })

    return render_template("index.html", files=supported_files, results=results, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR)

if _name_ == "_main_":
    app.run(debug=True, port=5000)