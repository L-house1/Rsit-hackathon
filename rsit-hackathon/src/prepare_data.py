import os
import time
import earthaccess

DATASETS = {
    "ECO_L2T_LSTE": "002",
    "SPL4SMGP": "008"
}

def robust_login():
    print("--- Authenticating with NASA Earthdata (.netrc) ---")
    try:
        auth = earthaccess.login(strategy="netrc")
        if getattr(auth, "authenticated", False):
            print("Authentication successful using .netrc")
            return True
        print("Authentication failed. Please ensure a valid .netrc file is in your home directory.")
        return False
    except Exception as e:
        print(f"Auth error: {e}")
        return False

def search_and_download(short_name, version, bounding_box, time_range, max_files, download_dir):
    print(f"\n--- Processing: {short_name} v{version} ---")
    try:
        q = earthaccess.DataGranules().short_name(short_name).version(version)
        q = q.bounding_box(*bounding_box).temporal(*time_range)
        
        results = q.get() # Fetch all available granules
        if not results:
            print(f"NO_RESULTS:{short_name}")
            return []

        print(f"Found {len(results)} granules, will download a max of {max_files}.")
        results_to_download = results[:max_files]

        downloaded = []
        if results_to_download:
            for attempt in range(3):
                try:
                    downloaded = earthaccess.download(results_to_download, local_path=download_dir)
                    break
                except Exception as e:
                    wait = 2 ** (attempt + 1)
                    print(f"Download attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)

        downloaded_files = [f for f in downloaded if str(f).endswith((".h5", ".hdf5", ".tif", ".tiff"))]
        
        print(f"Downloaded: {len(downloaded_files)} files")
        print(f"Saved to: {download_dir}")
        for f in downloaded_files:
            print(f" - {os.path.basename(str(f))}")
        return downloaded_files
    except Exception as e:
        print(f"Unexpected error for {short_name}: {e}")
        return []

def main():
    bbox_str = os.environ.get("BBOX", "-77.6,38.85,-77.3,39.15")
    time_range_str = os.environ.get("TIME_RANGE", "2023-07-15,2023-07-15")
    max_files = int(os.environ.get("MAX_FILES", 2))
    download_dir = os.path.abspath(os.environ.get("DOWNLOAD_DIR", "./tmp_data"))

    bounding_box = tuple(map(float, bbox_str.split(',')))
    time_range = tuple(time_range_str.split(','))

    if not robust_login():
        print("Authentication failed. Exiting.")
        return

    os.makedirs(download_dir, exist_ok=True)
    print(f"Download directory ready: {download_dir}")

    total_files = 0
    for short_name, version in DATASETS.items():
        files = search_and_download(
            short_name=short_name,
            version=version,
            bounding_box=bounding_box,
            time_range=time_range,
            max_files=max_files,
            download_dir=download_dir
        )
        total_files += len(files)

    print(f"\n=== Summary ===")
    print(f"Total new files: {total_files}")
    if total_files < 1:
        print("No files downloaded. Consider adjusting parameters and rerun.")

if __name__ == "__main__":
    main()