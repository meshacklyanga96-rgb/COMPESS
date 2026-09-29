import os
import gzip
import shutil
import hashlib
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(_name_)
app.secret_key = "super_secret_key"

# Supported file extensions for MySQL and PostgreSQL backup artifacts
SUPPORTED_EXTENSIONS = ('.sql', '.lz4', '.gz', '.zst', '.manifest', '.conf')

def get_file_hash(filepath):
    """Calculates SHA-256 hash to guarantee zero data loss/corruption."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_integrity(original_path, compressed_path):
    """Decompresses file to a temporary location and verifies SHA-256 checksum match."""
    temp_decompressed = compressed_path + ".tmp_verify"
    try:
        # Decompress
        with gzip.open(compressed_path, 'rb') as f_in, open(temp_decompressed, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        
        # Hash match check
        original_hash = get_file_hash(original_path)
        decompressed_hash = get_file_hash(temp_decompressed)
        
        return original_hash == decompressed_hash
    except Exception as e:
        return False
    finally:
        if os.path.exists(temp_decompressed):
            os.remove(temp_decompressed)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_dir = request.form.get('input_dir')
        output_dir = request.form.get('output_dir')
        compress_level = int(request.form.get('compress_level', 6)) # 1 (fastest) to 9 (smallest)

        if not os.path.exists(input_dir):
            flash(f"Input directory '{input_dir}' does not exist.", "danger")
            return redirect(url_for('index'))

        os.makedirs(output_dir, exist_ok=True)
        results = []

        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.endswith(SUPPORTED_EXTENSIONS):
                    orig_path = os.path.join(root, file)
                    out_path = os.path.join(output_dir, f"{file}.gz")

                    try:
                        # 1. Measure original size
                        orig_size = os.path.getsize(orig_path)

                        # 2. Compress file using Gzip with chosen level
                        with open(orig_path, 'rb') as f_in, gzip.open(out_path, 'wb', compresslevel=compress_level) as f_out:
                            shutil.copyfileobj(f_in, f_out)

                        # 3. Measure compressed size & calculate space saved
                        comp_size = os.path.getsize(out_path)
                        space_saved = ((orig_size - comp_size) / orig_size * 100) if orig_size > 0 else 0

                        # 4. Verify Integrity (Decompress & Compare Hashes)
                        is_valid = verify_integrity(orig_path, out_path)

                        if not is_valid:
                            os.remove(out_path) # Clean up invalid file
                            results.append({
                                'file': file,
                                'status': 'Failed',
                                'error': 'Integrity Check Failed (Hash Mismatch)'
                            })
                        else:
                            results.append({
                                'file': file,
                                'status': 'Success',
                                'orig_size': f"{orig_size / 1024:.2f} KB",
                                'comp_size': f"{comp_size / 1024:.2f} KB",
                                'saved': f"{space_saved:.2f}%",
                                'verified': True
                            })

                    except Exception as e:
                        results.append({'file': file, 'status': 'Failed', 'error': str(e)})

        return render_template('index.html', results=results, input_dir=input_dir, output_dir=output_dir)

    return render_template('index.html', results=None)

if _name_ == '_main_':
    app.run(debug=True)