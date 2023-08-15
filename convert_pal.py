from PIL import Image
import numpy as np
import os
import argparse
import csv

def read_palette(pcx_file):
    # Open the PCX image using PIL
    img = Image.open(pcx_file)
    # Get the palette
    palette = img.getpalette()[:768] # 256 colors * 3 (RGB)
    return [tuple(palette[i:i+3]) for i in range(0, len(palette), 3)]

def color_distance(c1, c2):
    # Compute the Euclidean distance between two RGB colors
    return np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2 + (c1[2] - c2[2])**2)

def closest_color(color, palette):
    # Initialize the minimum distance with a high value
    min_distance = float('inf')
    closest_col = None

    # Loop through each color in the palette
    for col in palette:
        distance = color_distance(color, col)
        if distance < min_distance:
            min_distance = distance
            closest_col = col

    return closest_col

def create_conversion_table(palette1, palette2):
    # Create a table matching each color in palette1 to the closest color in palette2
    return {color: closest_color(color, palette2) for color in palette1}

def create_index_mapping(palette1, palette2):
    index_mapping = {}
    color_differences = []
    
    for i, color1 in enumerate(palette1):
        closest_col = closest_color(color1, palette2)
        mapped_index = palette2.index(closest_col)
        index_mapping[i] = mapped_index
        difference = color_distance(color1, closest_col)
        color_differences.append((i, mapped_index, color1, closest_col, difference))
    
    return index_mapping, color_differences

def mip_to_bytes(mip_file_path):
    with open(mip_file_path,'rb') as f:
        return bytearray(f.read())

def read_header(byte_array):
    header = {
        'file_size': int.from_bytes(byte_array[0:4], 'little'),
        'main_image_width': int.from_bytes(byte_array[8:12], 'little'),
        'main_image_height': int.from_bytes(byte_array[12:16], 'little'),
        'number_of_images': int.from_bytes(byte_array[16:20], 'little'),
        'first_image_offset': int.from_bytes(byte_array[32:36], 'little') + 4
    }
    return header

def extract_image_offsets(header, byte_array):
    offsets = [header['first_image_offset']]
    for i in range(0, header['number_of_images'] - 1):
        offset = int.from_bytes(byte_array[44 + i * 12 : 48 + i * 12], 'little')
        offsets.append(offset)
    return offsets

def map_pixels(arr, first_image_offset, index_mapping):
    # Create a new byte array for the mapped pixels
    mapped_pixels = bytearray(arr[:first_image_offset]) # Copy the header

    # Extract the default color from byte 20
    default_color_index = arr[20]

    # Convert the default color using the index mapping
    mapped_default_color = index_mapping[default_color_index]

    # Replace the default color in the new byte array
    mapped_pixels[20] = mapped_default_color

    # Iterate through the original pixels and append the mapped index to the new byte array
    for pixel_index in arr[first_image_offset:]:
        mapped_index = index_mapping[pixel_index]
        mapped_pixels.append(mapped_index)
        
    return mapped_pixels


def bytes_to_image(mapped_pixels, palette, width, height, offset):
    # Extract the mapped pixels corresponding to the image data
    image_data = mapped_pixels[offset:]

    # Convert the image data into a 1D byte array
    image_bytes = bytearray(image_data)

    # Create a PIL Image object using the image bytes and the new palette
    img = Image.frombytes('P', (width, height), bytes(image_bytes))
    img.putpalette(palette)

    return img

def write_mip_file(file_path, mapped_pixels):
    with open(file_path, 'wb') as file:
        file.write(mapped_pixels)

def convert_all_mips(source_folder, destination_folder, index_mapping):
    # Check if the destination folder exists, and create it if not
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Iterate through all .mip files in the source folder
    for filename in os.listdir(source_folder):
        if filename.lower().endswith('.mip'):
            source_file_path = os.path.join(source_folder, filename)
            destination_file_path = os.path.join(destination_folder, filename)

            # Read the original .mip file
            arr = mip_to_bytes(source_file_path)
            header = read_header(arr)
            first_image_offset = header['first_image_offset']

            # Map the pixels using the index mapping
            mapped_pixels = map_pixels(arr, first_image_offset, index_mapping)

            # Write the new .mip file to the destination folder
            write_mip_file(destination_file_path, mapped_pixels)
            print(f"Converted {source_file_path} and saved to {destination_file_path}")

def read_pmp_file(file_path):
    with open(file_path, 'rb') as file:
        header = file.read(12)  # Read the 12-byte header
        image_data = bytearray(file.read())  # Read the image data
        
    return header, image_data

def convert_pmp_colors(input_file, index_mapping, output_file):
    header, image_data = read_pmp_file(input_file)


    # Iterate through the 4-byte sequences and update the color using the index mapping
    for i in range(0, len(image_data) - 1, 4):
        original_color_index = image_data[i + 3]
        mapped_color_index = index_mapping.get(original_color_index, original_color_index)
        image_data[i + 3] = mapped_color_index

    # Write the modified data to the output file
    with open(output_file, 'wb') as file:
        file.write(header)
        file.write(image_data)

    print(f"Converted PMP file written to {output_file}")

def convert_all_pmps_in_folder(input_folder, output_folder, index_mapping):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Iterate through all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.pmp'):
            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, filename)
            convert_pmp_colors(input_file, index_mapping, output_file)
            print(f"Converted {input_file} to {output_file}")

def convert_3do_file(input_file, output_file, index_mapping):
    flavor_names = {
        b'\x00\x00\x00\x00': ('VERTEX', 'F00'),
        b'\x01\x00\x00\x80': ('POLY', 'F01'),
        b'\x02\x00\x00\x80': ('POLY [T]', 'F02'),
        b'\x03\x00\x00\x80': ('PMP', 'F03'),
        b'\x04\x00\x00\x80': ('MATERIAL MIP', 'F04'),
        b'\x05\x00\x00\x80': ('FACE', 'F05'),
        b'\x06\x00\x00\x80': ('FACE2', 'F06'),
        b'\x07\x00\x00\x80': ('BSPF', 'F07'),
        b'\x08\x00\x00\x80': ('BSPA', 'F08'),
        b'\x09\x00\x00\x80': ('BSP2', 'F09'),
        b'\x0a\x00\x00\x80': ('BSPN', 'F10'),
        b'\x0b\x00\x00\x80': ('LIST', 'F11'),
        b'\x0c\x00\x00\x80': ('DYNO', 'F12'),
        b'\x0d\x00\x00\x80': ('RES', 'F13'),
        b'\x0e\x00\x00\x80': ('REDEF', 'F14'),
        b'\x0f\x00\x00\x80': ('DYNAMIC', 'F15'),
        b'\x10\x00\x00\x80': ('SUPEROBJ', 'F16'),
        b'\x11\x00\x00\x80': ('DATA2', 'F17'),
        b'\x12\x00\x00\x80': ('PMP2', 'F18')
    }


    with open(input_file, 'rb') as file:
        byte_array = file.read()  # Read the 12-byte header

        body_size = int.from_bytes(byte_array[0:4], 'little')
        root_offset = int.from_bytes(byte_array[4:8], 'little')
        num_mip_files = int.from_bytes(byte_array[8:12], 'little')
        num_pmp_files = int.from_bytes(byte_array[12:16], 'little')
        num_3do_files = int.from_bytes(byte_array[16:20], 'little')
        total_num_files = num_mip_files + num_pmp_files + num_3do_files
        body_offset = 20 + total_num_files * 8

        header = byte_array[0:body_offset]
        body = byte_array[body_offset:]

        # Initialize looping through flavors
        flavor_pointers = []
        root = [root_offset]
        polys_list = []

        while True:
            # If root offset has not been checked, check it. This should
            # run only during the first loop.
            if root:
                cur_pos = root.pop()

            # Go through everything in flavors if list is not empty
            elif flavor_pointers:
                cur_pos = flavor_pointers.pop()

            # If all the lists are empty (i.e. we've checked all referenced flavors in file), then exit the loop
            else:
                break

            flavor = body[cur_pos:cur_pos + 4]
            flavor_type = flavor_names[flavor][0]
            cur_pos += 4

            # Flavor 1
            if flavor_type == 'POLY':
                color = int.from_bytes(body[cur_pos: cur_pos + 4], 'little')
                polys_list.append((cur_pos, color))

            # Flavor 2
            elif flavor_type == 'POLY [T]':
                color = int.from_bytes(body[cur_pos + 4: cur_pos + 8], 'little')
                if color > 255: print (color)
                polys_list.append((cur_pos + 4, color))

            # Flavor 4
            elif flavor_type == 'MATERIAL MIP':
                color = int.from_bytes(body[cur_pos + 4: cur_pos + 8], 'little')
                mat_pointer = int.from_bytes(body[cur_pos + 8: cur_pos + 12], 'little')
                polys_list.append((cur_pos + 4, color))
                flavor_pointers.append(mat_pointer)

            # Flavor 5
            elif flavor_type == 'FACE':
                pointer1 = int.from_bytes(body[cur_pos + 20: cur_pos + 24], 'little')
                flavor_pointers.append(pointer1)

            # Flavor 6                                       
            elif flavor_type == 'FACE2':
                pointer1 = int.from_bytes(body[cur_pos + 20: cur_pos + 24], 'little')
                pointer2 = int.from_bytes(body[cur_pos + 24: cur_pos + 28], 'little')
                flavor_pointers.extend((pointer1, pointer2))

            # Flavor 7
            elif flavor_type == 'BSPF':
                pointer1 = int.from_bytes(body[cur_pos + 20: cur_pos + 24], 'little')
                pointer2 = int.from_bytes(body[cur_pos + 24: cur_pos + 28], 'little')
                pointer3 = int.from_bytes(body[cur_pos + 28: cur_pos + 32], 'little')
                flavor_pointers.extend((pointer1, pointer2, pointer3))

            # Flavor 8
            if flavor_type == 'BSPA':
                pointer1 = int.from_bytes(body[cur_pos + 20: cur_pos + 24], 'little')
                pointer2 = int.from_bytes(body[cur_pos + 24: cur_pos + 28], 'little')
                pointer3 = int.from_bytes(body[cur_pos + 28: cur_pos + 32], 'little')
                flavor_pointers.extend((pointer1, pointer2, pointer3))

            # Flavor 9
            elif flavor_type == 'BSP2':
                pointer1 = int.from_bytes(body[cur_pos + 20: cur_pos + 24], 'little')
                pointer2 = int.from_bytes(body[cur_pos + 24: cur_pos + 28], 'little')
                pointer3 = int.from_bytes(body[cur_pos + 28: cur_pos + 32], 'little')
                flavor_pointers.extend((pointer1, pointer2, pointer3))

            # Flavor 10
            elif flavor_type == 'BSPN':
                pointer1 = int.from_bytes(body[cur_pos + 20: cur_pos + 24], 'little')
                pointer2 = int.from_bytes(body[cur_pos + 24: cur_pos + 28], 'little')
                flavor_pointers.extend((pointer1, pointer2))

            # Flavor 11
            elif flavor_type == 'LIST':
                num_list_obj = int.from_bytes(body[cur_pos: cur_pos + 4], 'little')
                cur_pos += 4
                for i in range(0,num_list_obj):
                    list_pointer = int.from_bytes(body[cur_pos + i * 4: cur_pos + 4 + i * 4], 'little')
                    flavor_pointers.append(list_pointer)

        # go through polys list and update colors
        new_body = bytearray(body)

        for pointer, original_color_index in polys_list:
            new_body[pointer] = index_mapping[original_color_index]

        # Combine the header and updated body
        updated_byte_array = header + new_body

        # Write to a new file
        with open(output_file, 'wb') as new_file:
            new_file.write(updated_byte_array)

        print(f"Updated 3DO file written to {output_file}")

def convert_all_3dos_in_folder(input_folder, output_folder, index_mapping):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Iterate through all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.3do'):
            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, filename)

            convert_3do_file(input_file, output_file, index_mapping)
            print(f"Converted {input_file} to {output_file}")      

def log_color_mappings_to_csv(color_differences, filename):
    # Open the file in write mode
    with open(filename, 'w', newline='') as csvfile:
        # Create a CSV writer
        csvwriter = csv.writer(csvfile)
        
        # Write the header
        csvwriter.writerow(["Original Index", "Mapped Index", "Original Color (RGB)", 
                            "Mapped Color (RGB)", "Color Difference"])
        
        # Write the data
        for original_index, mapped_index, original_color, mapped_color, difference in color_differences:
            csvwriter.writerow([original_index, mapped_index, original_color, mapped_color, difference])

def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Convert MIP/PMP/3DO files using given palettes.")
    
    # Add arguments
    parser.add_argument("source_folder", help="Path to the source folder containing the files to be converted.")
    parser.add_argument("destination_folder", help="Path to the destination folder where converted files will be saved.")
    parser.add_argument("original_palette", help="Path to the PCX file of the original palette.")
    parser.add_argument("new_palette", help="Path to the PCX file of the new palette.")
    parser.add_argument("--log", help="Filename to save the color mappings log as a CSV. (Optional)", default=None)

    
    # Parse the arguments
    args = parser.parse_args()
    
    # Read palettes
    palette1 = read_palette(args.original_palette)
    palette2 = read_palette(args.new_palette)
    
    # Create index mapping
    index_mapping, color_differences = create_index_mapping(palette1, palette2)
    
    # Convert files
    convert_all_mips(args.source_folder, args.destination_folder, index_mapping)
    convert_all_pmps_in_folder(args.source_folder, args.destination_folder, index_mapping)
    convert_all_3dos_in_folder(args.source_folder, args.destination_folder, index_mapping)
    
    # Print mapping information
    if args.log:
        log_color_mappings_to_csv(color_differences, args.log)

if __name__ == "__main__":
    main()
