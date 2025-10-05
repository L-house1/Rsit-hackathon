import os
import time
import earthaccess

DATASETS = {
    "ECO_L2T_LSTE": "002",   # ECOSTRESS L2 LSTE
    "SPL4SMGP": "008"        # SMAP L4 Global
}

# Ashburn, VA pilot
BOUNDING_BOX = (-77.7, 38.80, -77.2, 39.20)
TIME_RANGE = ("2023-07-01", "2023-08-31")
MAX_FILES = 3
DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hackathon_data"))

def robust_login():
    print("--- Authenticating with NASA Earthdata (.netrc) ---")
    try:
        auth = earthaccess.login(strategy="netrc")
        if getattr(auth, "authenticated", False):
            print("Authentication successful using .netrc")
            return True
        print("Authentication failed with .netrc")
        return False
    except Exception as e:
        print(f"Auth error: {e}")
        return False

def search_and_download(short_name: str, version: str):
    print(f"\n--- Processing: {short_name} v{version} ---")
    try:
        q = earthaccess.DataGranules().short_name(short_name).version(version)
        q = q.bounding_box(*BOUNDING_BOX).temporal(*TIME_RANGE)
        results = q.get(page_size=MAX_FILES)
        if not results:
            print(f"NO_RESULTS:{short_name}")
            return []

        downloaded = []
        for attempt in range(3):
            try:
                downloaded = earthaccess.download(results, local_path=DOWNLOAD_DIR)
                break
            except Exception as e:
                wait = 2 ** (attempt + 1)
                print(f"Download attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)

        h5_files = [f for f in downloaded if str(f).endswith((".h5", ".hdf5"))]
        print(f"Found: {len(results)} granules")
        print(f"Downloaded: {len(h5_files)} files")
        print(f"Saved to: {DOWNLOAD_DIR}")
        for f in h5_files:
            print(f" - {os.path.basename(str(f))}")
        return h5_files
    except Exception as e:
        print(f"Unexpected error for {short_name}: {e}")
        return []

def main():
    if not robust_login():
        print("Authentication failed. Exiting.")
        return

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"Download directory ready: {DOWNLOAD_DIR}")

    total = 0
    for short_name, version in DATASETS.items():
        files = search_and_download(short_name, version)
        total += len(files)

    print(f"\n=== Summary ===")
    print(f"Total new HDF5 files: {total}")
    if total < 1:
        print("No files downloaded. Consider adjusting BOUNDING_BOX/TIME_RANGE/MAX_FILES and rerun.")

if __name__ == "__main__":
    main()
