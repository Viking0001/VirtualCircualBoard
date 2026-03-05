import sys
import os
import re
import termios
import tty
import copy

class Screen:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 41
        self.height = 32
        self.buffer = [[" " for _ in range(self.width)] for _ in range(self.height)]
    
    def draw(self, char):
        self.buffer[self.y][self.x] = char
        self.x += 1
        if self.x >= self.width:
            self.x = 0
            self.y += 1
        if self.y >= self.height:
            self.y = 0
    

def get_key():
    if not sys.stdin.isatty():
        # Fallback for non-interactive environments
        line = sys.stdin.readline()
        if not line: return 'q'
        return line[0]

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            # Read potential escape sequence for arrow keys
            seq = sys.stdin.read(2)
            ch += seq
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

class Simulator:
    def __init__(self, tokens, letters=None):
        self.tokens = tokens
        self.ram = {}
        self.registers = {"A": 0, "B": 0, "C": 0, "PTR": 0}
        self.pc = 0
        self.program = tokens
        self.outputs = []
        self.running = True
        self.last_action = "Initialized"
        self.history = []
        self.return_stack = []
        self.pending_y = 0  # Y offset set by GOTO2/CALL2 for 2D addressing
        self.screen = Screen()
        self.letters = letters or {}
        self.reverse_letters = {v: k for k, v in self.letters.items()}

    def get_char(self, val):
        if val in self.reverse_letters:
            return self.reverse_letters[val]
        return chr(val) if 32 <= val <= 126 else str(val)

    def get_value(self, ptr):
        return self.ram.get(ptr, 0)

    def set_value(self, ptr, val):
        self.ram[ptr] = val & 0xFF

    def save_state(self):
        state = {
            "ram": copy.deepcopy(self.ram),
            "registers": copy.deepcopy(self.registers),
            "pc": self.pc,
            "outputs": copy.deepcopy(self.outputs),
            "last_action": self.last_action,
            "return_stack": copy.deepcopy(self.return_stack),
            "pending_y": self.pending_y,
            "screen": copy.deepcopy(self.screen)
        }
        self.history.append(state)

    def undo(self):
        if not self.history:
            self.last_action = "Cannot undo (start of program)"
            return
        
        state = self.history.pop()
        self.ram = state["ram"]
        self.registers = state["registers"]
        self.pc = state["pc"]
        self.outputs = state["outputs"]
        self.return_stack = state["return_stack"]
        self.pending_y = state["pending_y"]
        self.screen = state["screen"]
        self.last_action = f"Undid: {state['last_action']}"
        self.running = True

    def draw_ui(self):
        os.system('clear')
        term_size = os.get_terminal_size()
        term_width = term_size.columns
        
        # Header: Current Command
        next_instr = ""
        if self.pc < len(self.program):
            next_instr = str(self.program[self.pc])
            # Check if next has operand
            if next_instr in ["PTR=", "A=", "B=", "C=", "RAM=", "GOTO1", "CALL1", "DRAW", "X=", "Y="] or next_instr.startswith("GOTO1_IF"):
                if self.pc + 1 < len(self.program):
                    next_instr += " " + str(self.program[self.pc+1])
        
        print("=" * term_width)
        print(f" NEXT COMMAND: {next_instr:30} | PC: {self.pc:3} | Status: {self.last_action}")
        print("=" * term_width)

        # Registers (Sidebar)
        reg_lines = [
            f" [ REGISTERS ] ",
            f" A:   {self.registers['A']:3} (0x{self.registers['A']:02X})",
            f" B:   {self.registers['B']:3} (0x{self.registers['B']:02X})",
            f" C:   {self.registers['C']:3} (0x{self.registers['C']:02X})",
            f" PTR: {self.registers['PTR']:3} (0x{self.registers['PTR']:02X})",
            "",
            " [ OUTPUTS ] "
        ]
        reg_lines.extend([f" > {out}" for out in self.outputs[-10:]]) # last 10 outputs

        # ROM View (Left)
        # We show a range around current PC, but group operands
        rom_lines = []
        rom_header = " [ ROM VIEW ] "
        rom_lines.append(rom_header)
        
        # Build list of displayable lines (index, text, is_pc)
        display_data = []
        i = 0
        while i < len(self.program):
            token = str(self.program[i])
            display_text = token
            original_idx = i
            is_pc = (i == self.pc)
            
            # Check if this instruction has an operand
            if token in ["PTR=", "A=", "B=", "C=", "RAM=", "GOTO1", "DRAW", "X=", "Y="] or token.startswith("GOTO1_IF"):
                if i + 1 < len(self.program):
                    display_text += " " + str(self.program[i+1])
                    if not is_pc and (i + 1 == self.pc):
                        is_pc = True
                    i += 1
            elif token in ["GOTO2", "CALL2"] or token.startswith("GOTO2_IF"):
                if i + 2 < len(self.program):
                    display_text += f" {self.program[i+1]} {self.program[i+2]}"
                    if not is_pc and (i in [self.pc-1, self.pc-2]): # PC inside multi-byte
                        is_pc = True
                    i += 2
            
            display_data.append((original_idx, display_text, is_pc))
            i += 1

        pc_display_idx = 0
        for idx, (orig_i, text, is_pc) in enumerate(display_data):
            if is_pc:
                pc_display_idx = idx
                break
        
        start_display = max(0, pc_display_idx - 8)
        end_display = min(len(display_data), start_display + 17)
        
        GREEN = "\033[42m\033[30m"
        RESET = "\033[0m"

        for idx in range(start_display, end_display):
            orig_i, text, is_pc = display_data[idx]
            line_content = f" {orig_i:3}: {text:15}"
            if is_pc:
                rom_lines.append(f"{GREEN}{line_content}{RESET}")
            else:
                rom_lines.append(line_content)

        # RAM View (Center)
        # We show a range around current PTR
        ram_start = max(0, self.registers['PTR'] - 8)
        ram_end = ram_start + 16
        
        ram_lines = [f" [ RAM VIEW ] "]
        for addr in range(ram_start, ram_end + 1):
            val = self.get_value(addr)
            line_content = f" {addr:4}: {val:3} (0x{val:02X}) "
            if addr == self.registers['PTR']:
                ram_lines.append(f"{GREEN}{line_content}{RESET}")
            else:
                ram_lines.append(line_content)

        # Combine lines
        # Determine how many lines to show. 
        # ROM has ~17, RAM has 17, Screen has 34.
        # We'll put registers and outputs next to Roman/RAM, and Screen on the right.

        output_lines = []
        screen_lines = [f" [ SCREEN ] "]
        screen_lines.append(" " + "".join([str(i % 10) for i in range(self.screen.width)]))
        for row_idx, row in enumerate(self.screen.buffer):
            screen_lines.append(f"{row_idx%10}" + "".join(row))

        max_lines = max(len(reg_lines), len(ram_lines), len(rom_lines), len(screen_lines))
        for i in range(max_lines):
            rom_part = rom_lines[i] if i < len(rom_lines) else ""
            ram_part = ram_lines[i] if i < len(ram_lines) else ""
            reg_part = reg_lines[i] if i < len(reg_lines) else ""
            scr_part = screen_lines[i] if i < len(screen_lines) else ""
            
            # Adjust padding for ANSI codes (which have 0 visible width)
            rom_pad = 25 if "\033" not in rom_part else 25 + len(GREEN) + len(RESET)
            ram_pad = 28 if "\033" not in ram_part else 28 + len(GREEN) + len(RESET)
            reg_pad = 30
            
            print(f"{rom_part:<{rom_pad}} | {ram_part:<{ram_pad}} | {reg_part:<{reg_pad}} | {scr_part}")

        print("=" * term_width)

    def step(self):
        if self.pc >= len(self.program):
            self.running = False
            return

        self.save_state()

        token = str(self.program[self.pc]).upper()
        opcode_idx = self.pc
        self.pc += 1
        
        desc = token

        if token == "END":
            self.running = False
        elif token == "A=RAM":
            self.registers["A"] = self.get_value(self.registers["PTR"])
        elif token == "B=RAM":
            self.registers["B"] = self.get_value(self.registers["PTR"])
        elif token == "C=RAM":
            self.registers["C"] = self.get_value(self.registers["PTR"])
        elif token == "PTR=":
            operand = int(self.program[self.pc])
            self.pc += 1
            self.registers["PTR"] = operand
            desc += f" {operand}"
        elif token == "PTR=RAM":
            self.registers["PTR"] = self.get_value(self.registers["PTR"])
        elif token == "PTR=A":
            self.registers["PTR"] = self.registers["A"]
        elif token == "PTR=B":
            self.registers["PTR"] = self.registers["B"]
        elif token == "PTR=C":
            self.registers["PTR"] = self.registers["C"]
        
        elif token == "RAM=A":
            self.set_value(self.registers["PTR"], self.registers["A"])
        elif token == "RAM=B":
            self.set_value(self.registers["PTR"], self.registers["B"])
        elif token == "RAM=C":
            self.set_value(self.registers["PTR"], self.registers["C"])
        elif token == "RAM=":
            operand = int(self.program[self.pc])
            self.pc += 1
            self.set_value(self.registers["PTR"], operand)
            desc += f" {operand}"
        
        elif token == "A=":
            operand = int(self.program[self.pc])
            self.pc += 1
            self.registers["A"] = operand & 0xFF
            desc += f" {operand}"
        elif token == "B=":
            operand = int(self.program[self.pc])
            self.pc += 1
            self.registers["B"] = operand & 0xFF
            desc += f" {operand}"
        elif token == "C=":
            operand = int(self.program[self.pc])
            self.pc += 1
            self.registers["C"] = operand & 0xFF
            desc += f" {operand}"
            
        elif token == "A=B+C": self.registers["A"] = (self.registers["B"] + self.registers["C"]) & 0xFF
        elif token == "B=A+C": self.registers["B"] = (self.registers["A"] + self.registers["C"]) & 0xFF
        elif token == "C=A+B": self.registers["C"] = (self.registers["A"] + self.registers["B"]) & 0xFF
        elif token == "A=C+B": self.registers["A"] = (self.registers["C"] + self.registers["B"]) & 0xFF
        elif token == "B=C+A": self.registers["B"] = (self.registers["C"] + self.registers["A"]) & 0xFF
        elif token == "C=B+A": self.registers["C"] = (self.registers["B"] + self.registers["A"]) & 0xFF
        
        elif token == "A=B-C": self.registers["A"] = (self.registers["B"] - self.registers["C"]) & 0xFF
        elif token == "B=A-C": self.registers["B"] = (self.registers["A"] - self.registers["C"]) & 0xFF
        elif token == "C=A-B": self.registers["C"] = (self.registers["A"] - self.registers["B"]) & 0xFF
        elif token == "A=C-B": self.registers["A"] = (self.registers["C"] - self.registers["B"]) & 0xFF
        elif token == "B=C-A": self.registers["B"] = (self.registers["C"] - self.registers["A"]) & 0xFF
        elif token == "C=B-A": self.registers["C"] = (self.registers["B"] - self.registers["A"]) & 0xFF

        elif token == "A=B": self.registers["A"] = self.registers["B"]
        elif token == "A=C": self.registers["A"] = self.registers["C"]
        elif token == "B=A": self.registers["B"] = self.registers["A"]
        elif token == "B=C": self.registers["B"] = self.registers["C"]
        elif token == "C=A": self.registers["C"] = self.registers["A"]
        elif token == "C=B": self.registers["C"] = self.registers["B"]

        elif token == "GOTO1":
            try:
                operand = int(self.program[self.pc])
                self.pc = self.pending_y * 255 + operand
                desc += f" {operand} (Y={self.pending_y})"
                self.pending_y = 0
            except (TypeError, ValueError):
                self.running = False
                self.last_action = f"Error: GOTO1 has invalid operand at {self.pc}"
        elif token == "GOTO2":
            try:
                y = int(self.program[self.pc])
                self.pc += 1
                self.pending_y = y
                desc += f" Y={y}"
            except (TypeError, ValueError):
                self.running = False
                self.last_action = f"Error: GOTO2 has invalid operand at {self.pc}"
        elif token.startswith("GOTO1_IF"):
            cond = token[len("GOTO1_IF"):]
            try:
                operand = int(self.program[self.pc])
                self.pc += 1
                desc += f" {operand}"
                if self.check_condition(cond):
                    self.pc = self.pending_y * 255 + operand
                self.pending_y = 0
            except (TypeError, ValueError):
                self.running = False
                self.last_action = f"Error: {token} has invalid operand at {self.pc-1}"
        elif token.startswith("GOTO2_IF"):
            cond = token[len("GOTO2_IF"):]
            try:
                y = int(self.program[self.pc])
                self.pc += 1
                self.pending_y = y
                desc += f" Y={y}"
                # Condition is checked by the following GOTO1_IF
            except (TypeError, ValueError):
                self.running = False
                self.last_action = f"Error: {token} has invalid operand at {self.pc}"
        
        elif token == "X=":
            operand = int(self.program[self.pc])
            self.pc += 1
            self.screen.x = operand % self.screen.width
            desc += f" {operand}"
        elif token == "Y=":
            operand = int(self.program[self.pc])
            self.pc += 1
            self.screen.y = operand % self.screen.height
            desc += f" {operand}"
        elif token == "X=A": self.screen.x = self.registers["A"] % self.screen.width
        elif token == "X=B": self.screen.x = self.registers["B"] % self.screen.width
        elif token == "X=C": self.screen.x = self.registers["C"] % self.screen.width
        elif token == "X=RAM": self.screen.x = self.get_value(self.registers["PTR"]) % self.screen.width
        elif token == "Y=A": self.screen.y = self.registers["A"] % self.screen.height
        elif token == "Y=B": self.screen.y = self.registers["B"] % self.screen.height
        elif token == "Y=C": self.screen.y = self.registers["C"] % self.screen.height
        elif token == "Y=RAM": self.screen.y = self.get_value(self.registers["PTR"]) % self.screen.height

        elif token == "DRAW":
            operand = int(self.program[self.pc])
            self.pc += 1
            char = self.get_char(operand)
            self.screen.draw(char)
            self.outputs.append(operand)
            desc += f" {operand}"
        elif token == "DRAW_A": 
            char = self.get_char(self.registers["A"])
            self.screen.draw(char)
            self.outputs.append(operand)
        elif token == "DRAW_B":
            char = self.get_char(self.registers["B"])
            self.screen.draw(char)
            self.outputs.append(operand)
        elif token == "DRAW_C":
            char = self.get_char(self.registers["C"])
            self.screen.draw(char)
            self.outputs.append(operand)
        elif token == "DRAW_RAM":
            val = self.get_value(self.registers["PTR"])
            char = self.get_char(val)
            self.screen.draw(char)
            self.outputs.append(val)

        elif token == "CALL1":
            try:
                operand = int(self.program[self.pc])
                self.pc += 1
                self.return_stack.append(self.pc)
                self.pc = self.pending_y * 255 + operand
                desc += f" {operand} (Y={self.pending_y})"
                self.pending_y = 0
            except (TypeError, ValueError):
                self.running = False
                self.last_action = f"Error: CALL1 has invalid operand at {self.pc}"
        elif token == "CALL2":
            try:
                y = int(self.program[self.pc])
                self.pc += 1
                self.pending_y = y
                desc += f" Y={y}"
            except (TypeError, ValueError):
                self.running = False
                self.last_action = f"Error: CALL2 has invalid operand at {self.pc}"
        elif token == "RETURN":
            if self.return_stack:
                self.pc = self.return_stack.pop()
            else:
                self.running = False
                self.last_action = "RETURN with empty stack!"

        elif token == "A=INPUT":
            val = input(" INPUT for A: ")
            self.registers["A"] = int(val) & 0xFF
        elif token == "B=INPUT":
            val = input(" INPUT for B: ")
            self.registers["B"] = int(val) & 0xFF
        elif token == "C=INPUT":
            val = input(" INPUT for C: ")
            self.registers["C"] = int(val) & 0xFF

        elif token == "NOP":
            pass
        else:
            self.running = False
            self.last_action = f"Unknown instruction: {token}"

        self.last_action = f"Ran {desc}"

    def check_condition(self, cond):
        match = re.match(r"([ABC])(!=|==|>=|<=|>|<)([ABC]|\d+)", cond)
        if match:
            lhs_reg, op, rhs = match.groups()
            lhs_val = self.registers[lhs_reg]
            rhs_val = self.registers[rhs] if rhs in self.registers else int(rhs)
            
            if op == "==": return (lhs_val == rhs_val)
            elif op == "!=": return (lhs_val != rhs_val)
            elif op == ">=": return (lhs_val >= rhs_val)
            elif op == "<=": return (lhs_val <= rhs_val)
            elif op == ">": return (lhs_val > rhs_val)
            elif op == "<": return (lhs_val < rhs_val)
        elif cond == "": # unconditional
            return True
        return False

    def run(self):
        mode = 'step'
        while self.running:
            self.draw_ui()
            if mode == 'step':
                print("[Arrows/Enter] Step fwd/back, [c] Continue, [q] Quit: ", end="", flush=True)
                key = get_key()
                if key == 'q': break
                elif key == 'c': mode = 'continue'
                elif key in ['\x1b[A', '\x1b[D']: # Up or Left
                    self.undo()
                    continue
                elif key in ['\r', '\n', '\x1b[B', '\x1b[C']: # Enter, Down or Right
                    pass
                else: continue
            
            self.step()
        
        self.draw_ui()
        print("\n--- Simulation Ended ---")

if __name__ == "__main__":
    import os
    import sys
    
    script_dir = os.path.dirname(__file__)
    main_dir = os.path.join(script_dir, 'main')
    sys.path.append(main_dir)
    import compile as compiler_mod

    # Resolve absolute paths for resource files
    letters_path = os.path.abspath(os.path.join(script_dir, "../../letters/letters.txt"))
    my_code_path = os.path.abspath(os.path.join(script_dir, "../myCode.txt"))
    # Verify existence (fallback not needed, raise if missing)
    if not os.path.exists(letters_path):
        raise FileNotFoundError(f"Letters file not found at {letters_path}")
    if not os.path.exists(my_code_path):
        raise FileNotFoundError(f"myCode file not found at {my_code_path}")

    letters = {}
    with open(letters_path, "r") as f:
        for i, letter in enumerate(f.read().splitlines()):
            if letter == "\\\\": continue
            letters[letter] = i

    processor = compiler_mod.Processor(letters)
    with open(my_code_path, "r") as f:
        for line in f:
            line = line.split("//")[0].strip()
            if not line: continue
            processor.process_command(line)
        processor.commands.append(compiler_mod.Command("END"))

    tokens = [v.text for v in processor.commands]
    sim = Simulator(tokens, letters)
    sim.run()
