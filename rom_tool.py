import sys
import os
import re
import subprocess

# 1. Binary to Header
def binary_to_header(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        return

    # Generate variable name from filename
    var_name = os.path.splitext(os.path.basename(input_path))[0]
    var_name = re.sub(r'[^a-zA-Z0-9]', '_', var_name)

    with open(input_path, 'rb') as f_in, open(output_path, 'w') as f_out:
        data = f_in.read()
        
        # Trim/Scrub trailing 0xFF padding
        data = data.rstrip(b'\xff')

        f_out.write(f"#ifndef {var_name}_H\n")
        f_out.write(f"#define {var_name}_H\n\n")
        f_out.write(f"const unsigned long long {var_name}_size = {len(data)};\n")
        f_out.write(f"const unsigned char {var_name}_data[] = {{\n")

        # Write hex data
        for i, byte in enumerate(data):
            f_out.write(f"0x{byte:02X},")
            if (i + 1) % 16 == 0:
                f_out.write("\n")
            else:
                f_out.write(" ")
        
        f_out.write("\n};\n\n#endif\n")
    
    print(f"Successfully converted {input_path} to {output_path}")

# 2. Header Minifier
def minify_header(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        return

    with open(input_path, 'r') as f_in, open(output_path, 'w') as f_out:
        content = f_in.read()
        
        out = []
        in_array = False
        
        # State machine to strip whitespace only inside the array {}
        for char in content:
            if char == '{':
                in_array = True
                out.append(char)
                continue
            if char == '}':
                in_array = False
                out.append(char)
                continue
                
            if in_array:
                # Inside array: strip spaces/newlines, keep content
                if not char.isspace():
                    out.append(char)
            else:
                # Outside array: keep original formatting
                out.append(char)
                
        f_out.write("".join(out))
    
    print(f"Successfully minified {input_path} to {output_path}")

# 3. Header to Binary Recompiler
def header_to_binary(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found.")
        return

    print("Parsing header... (this may take a few seconds)")

    # Read the text file
    with open(input_path, 'r') as f_in:
        content = f_in.read()

    # Find all occurrences of 0xXX
    # regex finds '0x' followed by exactly 2 hex digits
    matches = re.finditer(r'0x([0-9A-Fa-f]{2})', content)
    
    with open(output_path, 'wb') as f_out:
        # Buffer writes to avoid excessive IO
        chunk = bytearray()
        for m in matches:
            chunk.append(int(m.group(1), 16))
            
            # Write every 1MB to keep memory usage low
            if len(chunk) > 1024 * 1024:
                f_out.write(chunk)
                chunk = bytearray()
        
        # Process remaining bytes
        if chunk:
            # Trim/Scrub trailing 0xFF padding from the reconstructed data
            # We need to act on the file or the buffer. 
            # Since we wrote in chunks, we might need to trim the file itself or last chunk.
            # For simplicity in this logic, we write the last chunk then truncate file.
            pass # see below
            
    # Post-processing scrub on the output file
    with open(output_path, 'rb+') as f:
        d = f.read()
        trimmed = d.rstrip(b'\xff')
        if len(trimmed) < len(d):
            f.seek(0)
            f.write(trimmed)
            f.truncate()
            
    print(f"Successfully recompiled {input_path} to {output_path}")

# 4. LZ4 Comparison
def lz4_compare(original, new):
    print("\n--- LZ4 Compression Comparison ---")
    try:
        # Compress both files to temp locations to check size
        subprocess.run(f"lz4 -f -q \"{original}\" \"{original}\".lz4", shell=True, check=True)
        subprocess.run(f"lz4 -f -q \"{new}\" \"{new}\".lz4", shell=True, check=True)
        
        s1 = os.path.getsize(f"{original}.lz4")
        s2 = os.path.getsize(f"{new}.lz4")
        
        print(f"Original LZ4 Size: {s1} bytes")
        print(f"Ending   LZ4 Size: {s2} bytes")
        print(f"Difference:        {s2 - s1} bytes")
        
        # Cleanup
        os.remove(f"{original}.lz4")
        os.remove(f"{new}.lz4")
    except Exception as e:
        print(f"LZ4 check failed (is lz4 installed?): {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("GameBoy ROM Tool (Python Version)")
        print("Usage:")
        print("  Convert:   python3 rom_tool.py -c <input.gb> <output.h>")
        print("  Minify:    python3 rom_tool.py -m <input.h>  <output.h>")
        print("  Recompile: python3 rom_tool.py -r <input.h>  <output.gb>")
        sys.exit(1)

    mode = sys.argv[1]
    inp = sys.argv[2]
    out = sys.argv[3]

    if mode == "-c":
        binary_to_header(inp, out)
    elif mode == "-m":
        minify_header(inp, out)
    elif mode == "-r":
        header_to_binary(inp, out)
    elif mode == "-a":
        binary_to_header(inp, out + ".h")
        minify_header(out + ".h", out + ".min.h")
        header_to_binary(out + ".min.h", out)
        lz4_compare(inp, out)
    else:
        print(f"Unknown mode: {mode}")
