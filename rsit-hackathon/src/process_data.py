import os
import h5py
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_geom
import numpy as np
import json
import glob
from datetime import datetime

def find_hdf5_variable(group, keywords, priority_keywords):
    """Recursively search for a dataset, prioritizing certain keywords."""
    candidates = {}
    for key in group:
        if isinstance(group[key], h5py.Dataset):
            if all(k in key.lower() for k in keywords):
                candidates[key] = group[key]
        elif isinstance(group[key], h5py.Group):
            found = find_hdf5_variable(group[key], keywords, priority_keywords)
            if found: return found

    if not candidates: return None

    for p_key in priority_keywords:
        for c_key in candidates:
            if p_key in c_key.lower():
                return candidates[c_key]
    
    return list(candidates.values())[0]

def get_smap_data(file_path):
    """Extracts and normalizes soil moisture data from a SMAP HDF5 file."""
    try:
        with h5py.File(file_path, 'r') as f:
            sm_surface_data = find_hdf5_variable(f, ['soil', 'moisture'], ['surface'])
            sm_root_data = find_hdf5_variable(f, ['soil', 'moisture'], ['root'])

            sm_surface_norm, sm_root_norm = None, None

            if sm_surface_data is not None:
                sm_surface = np.nanmean(sm_surface_data[:])
                sm_surface_norm = float(np.clip(sm_surface / 0.5, 0, 1))

            if sm_root_data is not None:
                sm_root = np.nanmean(sm_root_data[:])
                sm_root_norm = float(np.clip(sm_root / 0.5, 0, 1))

            return sm_surface_norm, sm_root_norm
    except Exception as e:
        print(f"Error processing SMAP file {os.path.basename(file_path)}: {e}")
        return None, None

def get_ecostress_data(lst_file_path, bbox):
    """Extracts, masks, and normalizes LST data from an ECOSTRESS GeoTIFF."""
    try:
        with rasterio.open(lst_file_path) as src:
            print(f"  - Raster CRS: {src.crs}")
            if not src.crs:
                raise ValueError("Source raster has no CRS specified.")

            # Define the geometry in WGS84
            geom = [{'type': 'Polygon', 'coordinates': [[(bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[2], bbox[3]), (bbox[0], bbox[3]), (bbox[0], bbox[1])]]}]
            
            # Transform the geometry to the raster's CRS
            print(f"  - Warping geometry from EPSG:4326 to {src.crs}...")
            warped_geom = [transform_geom('EPSG:4326', src.crs, g) for g in geom]
            print(f"  - Warped geometry: {warped_geom}")

            # Mask the raster with the warped geometry
            try:
                out_image, out_transform = mask(src, warped_geom, crop=True)
            except ValueError as e:
                print(f"  - ERROR during mask operation: {e}")
                # Re-raise or return to indicate failure
                raise e

            data = out_image[0].astype(np.float32)

            # --- QC Data Masking ---
            qc_file_path = lst_file_path.replace('_LST.tif', '_QC.tif')
            if os.path.exists(qc_file_path):
                with rasterio.open(qc_file_path) as qc_src:
                    qc_out_image, _ = mask(qc_src, warped_geom, crop=True)
                    qc_data = qc_out_image[0]
                    data[qc_data != 0] = np.nan

            # --- Data Conversion and Filtering ---
            data[data == src.nodata] = np.nan
            data = data * 0.02 - 273.15 # Apply scale and offset
            data[data < -50] = np.nan # Filter out unrealistic values

            if np.all(np.isnan(data)):
                print("  - Result: No valid data in AOI after masking.")
                return None, None

            avg_lst = np.nanmean(data)
            lst_norm = np.clip((avg_lst - 0) / 40, 0, 1)
            
            print(f"  - Result: Success! Avg LST: {avg_lst:.2f}°C")
            return float(avg_lst), float(lst_norm)

    except Exception as e:
        print(f"Error processing ECOSTRESS file {os.path.basename(lst_file_path)}: {e}")
        return None, None

def main():
    input_dir = os.path.abspath(os.environ.get("DOWNLOAD_DIR", "./tmp_data"))
    aoi_bbox_str = os.environ.get("BBOX", "-77.6,38.85,-77.3,39.15")
    output_file = os.path.abspath(os.environ.get("OUTPUT_FILE", "./docs/data/result.json"))
    aoi_name = os.environ.get("AOI_NAME", "ashburn")

    aoi_bbox = tuple(map(float, aoi_bbox_str.split(',')))

    print(f"Starting data processing from: {input_dir}")
    smap_files = sorted(glob.glob(os.path.join(input_dir, '*_SM_*.h5')))
    lst_files = sorted(glob.glob(os.path.join(input_dir, '*_LST.tif')))

    print(f"Found {len(smap_files)} SMAP files and {len(lst_files)} ECOSTRESS LST files.")

    results = []
    if not smap_files and not lst_files:
        print("No data files found to process.")
    else:
        sm_surface_norm, sm_root_norm, lst, lst_norm = None, None, None, None
        timestamp = "N/A"

        # Try to find a valid ECOSTRESS file first
        for eco_path in reversed(lst_files):
            print(f"Processing ECOSTRESS: {os.path.basename(eco_path)}")
            lst, lst_norm = get_ecostress_data(eco_path, aoi_bbox)
            if lst is not None:
                try:
                    fname = os.path.basename(eco_path)
                    dt_str = fname.split('_')[5]
                    timestamp = datetime.strptime(dt_str, '%Y%m%dT%H%M%S').isoformat() + "Z"
                    # Find a corresponding SMAP file by timestamp
                    for smap_path in reversed(smap_files):
                        smap_fname = os.path.basename(smap_path)
                        smap_dt_str = smap_fname.split('_')[4]
                        smap_timestamp = datetime.strptime(smap_dt_str, '%Y%m%dT%H%M%S')
                        eco_timestamp = datetime.strptime(dt_str, '%Y%m%dT%H%M%S')
                        if abs((eco_timestamp - smap_timestamp).total_seconds()) < 3 * 3600:
                            print(f"Found matching SMAP: {smap_fname}")
                            sm_surface_norm, sm_root_norm = get_smap_data(smap_path)
                            break
                    break  # Found a valid LST, so we stop
                except Exception as e:
                    print(f"Timestamp parsing or SMAP search error: {e}")
                    continue

        # If no valid LST was found, fall back to SMAP or START_DATE for timestamp
        if timestamp == "N/A":
            if smap_files:
                smap_path = smap_files[-1]
                try:
                    fname = os.path.basename(smap_path)
                    dt_str = fname.split('_')[4]
                    timestamp = datetime.strptime(dt_str, '%Y%m%dT%H%M%S').isoformat() + "Z"
                    print(f"Processing SMAP for timestamp: {fname}")
                    sm_surface_norm, sm_root_norm = get_smap_data(smap_path)
                except Exception as e: 
                    print(f"SMAP processing error: {e}")
            else:
                timestamp = datetime.strptime(os.environ.get("START_DATE"), '%Y-%m-%d').isoformat() + "Z"

        # --- RSI Calculation ---
        if lst is None:
            print("Warning: LST data not found. Assuming neutral temperature of 25°C for RSI calculation.")
            lst = 25.0
            lst_norm = np.clip((lst - 0) / 40, 0, 1)

        t_norm = lst_norm
        m_norm = sm_surface_norm if sm_surface_norm is not None else 0.5
        m_deficit = 1 - m_norm
        rsi = (0.6 * t_norm) + (0.4 * m_deficit)

        record = {
            "timestamp": timestamp,
            "aoi": {"name": aoi_name, "bbox": list(aoi_bbox)},
            "lst_c": round(lst, 2) if lst is not None else None,
            "sm_surface": sm_surface_norm,
            "sm_root": sm_root_norm,
            "t_norm": float(t_norm) if t_norm is not None else None,
            "m_norm": float(m_norm) if m_norm is not None else None,
            "rsi": round(rsi, 4)
        }
        results.append(record)
        print(f"Calculated record: {record}")

    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Successfully wrote results to {output_file}")
    except Exception as e:
        print(f"Error writing to JSON file: {e}")

if __name__ == "__main__":
    main()
