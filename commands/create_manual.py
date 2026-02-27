import pathlib

# Get the path to commands.txt relative to this script
file_path = pathlib.Path(__file__).parent / "commands.txt"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            if '//' in line:
                # Get the part after the first '//' and strip whitespace
                comment = line.split('//', 1)[1].strip()
                
                if comment:
                    print(f"{format(line_number - 1, '08b')}  {comment}")
except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.")