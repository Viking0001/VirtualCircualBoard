import numpy as np
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from blueprint_utils import create_simple_blueprint, ComponentType


# Mapování mnemonik instrukcí na jejich POŘADÍ v commands.txt (1-based index)
INSTRUCTION_MAP = {
    "END":          0,
    "A=RAM":        1,
    "B=RAM":        2,
    "C=RAM":        3,
    "PTR=":         4,
    "GOTO1":        5,
    "GOTO1_IFA!=0": 6,
    "A=B+C":        7,
    "GOTO1_IFB!=0": 8,
    "B=A+C":        9,
    "GOTO1_IFC!=0": 10,    
    "C=A+B":        11,
    "GOTO1_IFA>=B": 12,
    "GOTO1_IFB<=A": 12,
    "A=C+B":        13,
    "GOTO1_IFA<=B": 14,
    "GOTO1_IFB>=A": 14,
    "B=C+A":        15,
    "GOTO1_IFB>=C": 16,
    "GOTO1_IFC<=B": 16,
    "C=B+A":        17,
    "GOTO1_IFB<=C": 18,
    "GOTO1_IFC>=B": 18,
    "RAM=A":        19,
    "GOTO1_IFC>=A": 20,
    "GOTO1_IFA<=C": 20,
    "RAM=B":        21,
    "GOTO1_IFC<=A": 22,
    "GOTO1_IFA>=C": 22,
    "RAM=C":        23,
    "A=":           24,
    "B=":           25,
    "C=":           26,
    "PTR=A":        27,
    "PTR=B":        28,
    "PTR=C":        29,
    "GOTO1_IFA==0": 30,
    "A=0":          31,
    "GOTO1_IFB==0": 32,
    "B=0":          33,
    "GOTO1_IFC==0": 34,
    "C=0":          35,
    "GOTO1_IFA<B":   36,
    "GOTO1_IFB>A":   36,
    "C=A-B":        37,
    "GOTO1_IFA>B":   38,
    "GOTO1_IFB<A":   38,
    "C=B-A":        39,
    "GOTO1_IFB<C":   40,
    "GOTO1_IFC>B":   40,
    "A=B-C":        41,
    "GOTO1_IFB>C":   42,
    "GOTO1_IFC<B":   42,
    "A=C-B":        43,
    "GOTO1_IFC<A":   44,
    "GOTO1_IFA>C":   44,
    "B=A-C":        45,
    "GOTO1_IFC>A":   46,
    "GOTO1_IFA<C":   46,
    "B=C-A":        47,
    "PTR=RAM":      48,
    "CALL1":         49,
    "RETURN":       50,
    "DRAW":         51,
    "DRAW_A":       52,
    "GOTO2_IFA==0":   53,
    "DRAW_B":       54,
    "GOTO2_IFB==0":   55,
    "DRAW_C":       56,
    "GOTO2_IFC==0":   57,
    "A=INPUT":      58,
    "GOTO2_IFA<B":   59,
    "GOTO2_IFB>A":   59,
    "B=INPUT":      60,
    "GOTO2_IFA>B":   61,
    "GOTO2_IFB<A":   61,
    "C=INPUT":      62,
    "GOTO2_IFB<C":   63,
    "GOTO2_IFC>B":   63,
    "X=":           64,
    "GOTO2_IFB>C":   65,
    "GOTO2_IFC<B":   65,
    "Y=":           66,
    "GOTO2_IFC<A":   67,
    "GOTO2_IFA>C":   67,
    "Y++":          68,
    "GOTO2_IFC>A":   69,
    "GOTO2_IFA<C":   69,    
    "X=A":          70,
    "X=B":          71,
    "X=C":          72,
    "X=RAM":        73,
    "Y=A":          74,
    "GOTO2_IFA!=0":  75,
    "Y=B":          76,
    "GOTO2_IFB!=0":  77,
    "Y=C":          78,
    "GOTO2_IFC!=0":  79,
    "Y=RAM":        80,
    "GOTO2_IFA>=B":   81,
    "GOTO2_IFB<=A":   81,
    "A=B":          82,
    "GOTO2_IFA<=B":   83,
    "GOTO2_IFB>=A":   83,
    "A=C":          84,
    "GOTO2_IFB>=C":   85,
    "GOTO2_IFC<=B":   85,
    "B=A":          86,
    "GOTO2_IFB<=C":   87,
    "GOTO2_IFC>=B":   87,
    "B=C":          88,
    "GOTO2_IFC>=A":   89,
    "GOTO2_IFA<=C":   89,
    "C=A":          90,
    "GOTO2_IFC<=A":   91,
    "GOTO2_IFA>=C":   91,
    "C=B":          92,
    "RAM=":         93,
    "GOTO2":        94,
    "RAM=INPUT":    95,
    "DRAW_INPUT":   96,
    "NOP":          97
}

INSTRUCTIONS_WITH_OPERAND = {    
    instr for instr in INSTRUCTION_MAP
    if instr.startswith("GOTO") or instr in {"CALL1", "PTR=", "A=", "B=", "C=", "RAM=", "DRAW", "X=", "Y="}
}

def bits_to_components(rows_list, hspace=3, vspace=2):
    """
    Převede seznam 8-bitových binárních řetězců na 2D pole komponent.
    Každý bit je 1x1 blok.
    1 = LATCH_ON, 0 = LATCH_OFF
    Mezery: hspace (3), vspace (3).
    """
    if not rows_list:
        return np.array([])

    num_rows = len(rows_list)
    bit_width = 8

    # Šířka: 8 bitů * 1 + (7 mezer * hspace)
    final_width = bit_width * 1 + (bit_width - 1) * hspace
    # Výška: num_rows * 1 (blok) + (num_rows - 1) * vspace
    final_height = num_rows * 1 + (num_rows - 1) * vspace
    
    components = np.full((final_height, final_width), ComponentType.NONE, dtype=object)
    
    for r_idx, bits in enumerate(rows_list):
        y_base = r_idx * (1 + vspace)
        
        for b_idx, bit in enumerate(bits):
            x_base = b_idx * (1 + hspace)
            
            block_type = ComponentType.WRITE if bit == '1' else ComponentType.TC_YELLOW_C
            
            if y_base < final_height and x_base < final_width:
                components[y_base, x_base] = block_type
                        
    return components

def assemble_tokens(tokens):
    """
    Sestaví seznam tokenů na binární řádky ROM.
    """
    # --- Pass 1: Mapování pořadí instrukce na adresu v ROM ---
    # instruction_address[1] = adresa první instrukce atd.
    instruction_addresses = {}
    current_rom_addr = 0
    instr_index = 1
    
    j = 0
    while j < len(tokens):
        token = str(tokens[j]).upper()
        if token in INSTRUCTION_MAP:
            instruction_addresses[instr_index] = current_rom_addr
            instr_index += 1
            current_rom_addr += 1 # Opcode řádek
            
            if token in INSTRUCTIONS_WITH_OPERAND:
                current_rom_addr += 1 # Operand řádek
                j += 2 # Přeskočíme instrukci i její operand token
            else:
                j += 1
        else:
            j += 1

    # --- Pass 2: Skutečná sestavení ---
    binary_rows = []
    i = 0
    while i < len(tokens):
        token = str(tokens[i]).upper()
        
        if token in INSTRUCTION_MAP:
            instr = token
            opcode = INSTRUCTION_MAP[instr]
            print(f"{i}: {instr} ({opcode})", end="")
            i += 1
            
            # 8-bit opcode řádek
            binary_rows.append(format(opcode & 0xFF, "08b"))
            
            # Pokud instrukce vyžaduje operand
            if instr in INSTRUCTIONS_WITH_OPERAND:
                operand = 0
                if i < len(tokens):
                    try:
                        val_str = str(tokens[i])
                        if val_str.lstrip('-').isdigit():
                            val = int(val_str)
                            i += 1
                            
                            # Vždy použijeme doslovnou hodnotu (literal) bez přepočtu adres
                            operand = val
                        else:
                            print(f"Warning: Instrukce {instr} vyžaduje operand, ale nalezeno '{val_str}'. Používám 0.")
                    except ValueError:
                        print(f"Warning: Neplatný operand pro {instr}. Používám 0.")
                
                print(f" + operand={operand}")
                binary_rows.append(format(operand & 0xFF, "08b"))
            else:
                print()
        else:
            i += 1
            
    return binary_rows

def assemble_file(input_filename):
    if not os.path.exists(input_filename):
        print(f"Error: {input_filename} nebyl nalezen.")
        return []

    tokens = []
    with open(input_filename, "r", encoding="utf-8") as f:
        for line in f:
            # Odstraníme komentář a nahradíme středníky mezerou
            clean_line = line.split("//")[0].replace(";", " ")
            tokens.extend(clean_line.split())

    return assemble_tokens(tokens)

def main(argv):
    # Pokud je argv seznam tokenů (od compile.py), zpracujeme je přímo
    if isinstance(argv, list) and len(argv) > 0 and (isinstance(argv[0], int) or (isinstance(argv[0], str) and not argv[0].endswith(".py"))):
        bin_rows = assemble_tokens(argv)
    # Jinak předpokládáme argumenty příkazové řádky (argv[1] je jméno souboru)
    elif len(argv) > 1:
        input_file = argv[1]
        bin_rows = assemble_file(input_file)
    else:
        print("Please provide an input file.")
        return
        
    try:
        if bin_rows:
            components = bits_to_components(bin_rows)
            
            if components.size > 0:
                blueprint = create_simple_blueprint(
                    components,
                    name="Variable Row ROM",
                    description=f"8-bit rows, operands on separate lines",
                    tags="rom,assembler,8bit"
                )
                
                print("\nVygenerovaný blueprint (VCB+):")
                print(blueprint)
                print(f"\nPočet vygenerovaných 8-bit řádků: {len(bin_rows)}")
                print(f"Rozměry: {components.shape[1]}x{components.shape[0]}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Běhová chyba: {e}")

if __name__ == "__main__":
    main(sys.argv)
