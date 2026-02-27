import os

def create_manual(input_file):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    SPECIAL_NAMES = {
        "+": "Kp Add",
        "-": "Kp Subtract",
        "/": "Kp Divide",
        "=": "Equal",
        ".": "Period",
        ",": "Comma",
        "?": "Question Mark",
        "!": "Exclamation Mark"
    }

    manual_lines = []
    constants_lines = []
    with open(input_file, "r", encoding="utf-8") as f:
        lines = [line.rstrip('\n') for line in f]

    for i, line in enumerate(lines):
        binary_addr = format(i, "08b")
        
        const_name = None
        if line == "\\\\":
            char_desc = "(blank)"
        elif line == "\\\\n":
            char_desc = "(newline)"
            const_name = "Enter"
        elif line == "":
            char_desc = "(empty)"
        elif line == " ":
            char_desc = "(space)"
            const_name = "SPACE"
        else:
            char_desc = line
            if line in SPECIAL_NAMES:
                const_name = SPECIAL_NAMES[line]
            elif len(line) == 1:
                const_name = line.upper()
            
        manual_lines.append(f"{binary_addr} => {char_desc}")
        if const_name:
            constants_lines.append(f"{const_name} = {i}")

    print("\n".join(manual_lines) + "\n")
    print(f"Total entries: {len(manual_lines)}\n")
    
    if constants_lines:
        print("\n".join(constants_lines))

if __name__ == "__main__":
    # Cesty relativní k rootu projektu
    input_path = "latters/latters.txt"
    create_manual(input_path)
