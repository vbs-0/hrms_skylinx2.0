import os
import zipfile

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        # Exclude large/temporary directories
        dirs[:] = [d for d in dirs if d not in ['venv', '.git', '__pycache__', '.idea', '.vscode', '.gemini', 'node_modules']]
        for file in files:
            if file.endswith('.pyc') or file.endswith('.pyo') or file.endswith('.db.sqlite3-journal'):
                continue
            filePath = os.path.join(root, file)
            relPath = os.path.relpath(filePath, path)
            ziph.write(filePath, relPath)

def main():
    src_dir = r"E:\HRMS13\hrms_skylinx2.0-13.0.0.beta\hrms_skylinx2.0-13.0.0.beta"
    target_zip = r"E:\HRMS13\hrms_skylinx_sandeep_modified.zip"
    
    print(f"Starting compression of: {src_dir}")
    print(f"Output will be saved to: {target_zip}")
    
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipdir(src_dir, zipf)
        
    print("Compression successfully completed!")

if __name__ == "__main__":
    main()
