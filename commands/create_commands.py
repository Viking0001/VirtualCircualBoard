import numpy as np
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from blueprint_utils import ComponentType, create_simple_blueprint, read_blueprint_info

def parse_commands(filename):
    """
    Načte commands.txt a vrátí 2D pole bitů (integery).
    Odstraní mezery a vše za // (včetně).
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Soubor {filename} nebyl nalezen.")
        
    commands = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            # Odstranění komentářů
            clean_line = line.split('//')[0]
            # Odstranění mezer a tabulátorů
            bits_str = clean_line.replace(' ', '').replace('\t', '').strip()
            
            if not bits_str:
                continue
                
            # Převod '1'/'0' na inty
            row = [int(bit) for bit in bits_str]
            commands.append(row)
            
    return commands

def generate_commands_blueprint(commands_list):
    """
    Vytvoří VCB blueprint z 2D pole příkazů s mezerami.
    1 = BUFFER, 0 = NONE
    Mezery: 1 kostička horizontálně, 3 kostičky vertikálně.
    """
    if not commands_list:
        raise ValueError("Seznam příkazů je prázdný.")
        
    num_commands = len(commands_list)
    num_bits = len(commands_list[0])
    
    # Výpočet rozměrů s mezerami
    # Každých 10 bitů je 1 mezera (grid_unit)
    grid_units = num_bits + (num_bits // 10) + 1
    final_width = grid_units * 2 + 2
    # Výška: 4 řádky na příkaz
    final_height = 4 * num_commands + 1
    
    # Inicializace pole s ComponentType.NONE
    components = np.full((final_height, final_width), ComponentType.NONE, dtype=object)
    
    y_offset = 1
    for y, row in enumerate(commands_list):
        if len(row) != num_bits:
            raise ValueError(f"Řádek {y+1} má nekonzistentní délku.")
            
        for x, val in enumerate(row):
            # Posun každých 10 bitů o jeden grid_unit (3 pixely)
            grid_x = x + (x // 10)
            base_x = grid_x * 2
            
            components[y * 4 + y_offset - 1, base_x] = ComponentType.CROSS
            if val == 1:
                components[y * 4 + y_offset - 1, base_x + 1] = ComponentType.READ
                components[y * 4 + y_offset, base_x] = ComponentType.WRITE
            else:
                components[y * 4 + y_offset - 1, base_x + 1] = ComponentType.TC_YELLOW_C  
                components[y * 4 + y_offset, base_x] = ComponentType.TC_VIOLET         
            
            # Row y+1 & y+2: VIOLET under the center column
            components[y * 4 + y_offset + 1, base_x] = ComponentType.TC_VIOLET
            components[y * 4 + y_offset + 2, base_x] = ComponentType.TC_VIOLET
            
            if val == 1:
                components[y * 4 + y_offset, base_x + 1] = ComponentType.BUFFER
            else:
                components[y * 4 + y_offset, base_x + 1] = ComponentType.NONE
                
        # Separators logic
        # Mezery jsou na pozicích grid_x: 10, 21, 32... tj. (11*k - 1)
        for x_idx in range(1, (num_bits // 10)):
            sep_grid_x = x_idx * 11 - 1
            sep_x = sep_grid_x * 2
            
            # Check boundaries
            if sep_x >= final_width:
                continue

            # Use columns around the gap
            boxs = ComponentType.TC_ORANGE if x_idx == (num_bits // 10) -1 else ComponentType.TC_RED
            
            components[y * 4 + y_offset - 1, sep_x] = ComponentType.CROSS
            components[y * 4 + y_offset - 1, sep_x + 1] = ComponentType.TC_YELLOW_C
            components[y * 4 + y_offset, sep_x] = boxs
            components[y * 4 + y_offset + 1, sep_x] = boxs
            components[y * 4 + y_offset + 2, sep_x] = boxs

                
    return create_simple_blueprint(
        components, 
        name="Commands Blueprint with Spacing", 
        description=f"Generated from commands.txt (Spacing: 1H, 3V)"
    )

if __name__ == "__main__":
    commands_file = "commands/commands.txt"
    try:
        commands = parse_commands(commands_file)
        blueprint_str = generate_commands_blueprint(commands)
        
        print("\nVygenerovaný blueprint (VCB+):")
        print(blueprint_str)
        
        print("\nStatistiky:")
        info = read_blueprint_info(blueprint_str)
        print(f"Rozměry: {info['width']}x{info['height']}")
        print(f"Počet příkazů: {len(commands)}")
        
    except Exception as e:
        print(f"Chyba: {e}")


