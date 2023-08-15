# Palette Conversion Utility: `convert_pal.py`

This utility allows users to convert image files (MIP, PMP, 3DO) based on provided color palettes. The color palettes are extracted from PCX files (i.e. SUNNY.PCX).

## Features

1. **Extract Palettes from PCX Files**: Quickly read and extract color palettes from PCX format images.
2. **Compute Color Distances**: Utilizes the Euclidean distance formula to measure the difference between two RGB colors.
3. **Find Closest Colors**: Given a specific color and a palette, the utility identifies the closest matching color within the palette.
4. **Generate Conversion Tables**: For two given palettes, the utility can create a mapping from each color in the first palette to its closest counterpart in the second.
5. **Palette Index Mapping**: For efficient conversion, an index mapping between the source and destination palettes is used.
6. **Support for Multiple Formats**: The utility can process and convert MIP, PMP, and 3DO file formats.
7. **Logging Capabilities**: Optionally, users can save a detailed log of the color mappings in a CSV format.

## Usage

To use this utility, you'll need to run it from the command-line with the appropriate arguments:
```bash
python convert_pal.py SOURCE_FOLDER DESTINATION_FOLDER ORIGINAL_PALETTE NEW_PALETTE [--log LOG_FILENAME]
```
Where:

- `SOURCE_FOLDER`: Path to the source folder containing the files to be converted.
- `DESTINATION_FOLDER`: Path to the destination folder where the converted files will be saved.
- `ORIGINAL_PALETTE`: Path to the PCX file of the original palette.
- `NEW_PALETTE`: Path to the PCX file of the new palette.
- `--log LOG_FILENAME`: (Optional) If provided, a CSV log of the color mappings will be saved with the given filename.

## Dependencies

- Pillow (Python Imaging Library)
- NumPy

Make sure to install the required dependencies before running the utility.
