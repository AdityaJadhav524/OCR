import os
import glob
import json
import hashlib
import sys

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_manifest.py <directory>")
        sys.exit(1)
        
    target_dir = sys.argv[1]
    pdfs = glob.glob(os.path.join(target_dir, "*.pdf"))
    
    manifest = {}
    for pdf in pdfs:
        filename = os.path.basename(pdf)
        manifest[filename] = sha256_file(pdf)
        
    out_path = os.path.join(target_dir, "benchmark_manifest.json")
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Manifest written to {out_path} with {len(manifest)} files.")

if __name__ == '__main__':
    main()
