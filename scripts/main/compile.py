import compile_assembly
import os
import re

class Command:
    saved_commands = None

    def __init__(self, text: str | None) -> None:
        self.text = text

    @staticmethod
    def create(text: str | None):
        if Command.saved_commands is not None:
            command = Command.saved_commands
            command.text = text
            Command.saved_commands = None
            return command

        return Command(text)
    
    @staticmethod
    def create_blind_command():
        command = Command(None)
        Command.saved_commands = command
        return command

    def __str__(self) -> str:
        return self.text

class Variable:
    def __init__(self, name: str | None, RAM_position: int, pointer_level: int = 0) -> None:
        self.pointer_level = pointer_level
        self.name = name
        self.RAM_position = RAM_position


        

class Control_flow:
    x_length = 255
    list_if_commands = [] 
    def __init__(self, commands: list[Command], command: Command | None = None) -> None:
        if command is None:
            self.command = Command.create(None)
            commands.append(self.command)
        else:
            self.command = command
        self.list_if_commands.append(self)
        self.first = True
        self.position = None
    
    def set(self, commands: list[Command], position: int | None, add : int = 0 ) -> None:
        if self.position is None:
            self.position = position
        if position is None:
            position = self.position
        
        position += add
        y = position // self.x_length
        x = position % self.x_length
        index = commands.index(self.command)
        if (y == (index // self.x_length)):
            self.command.text = str(x)
        else:
            if self.first:
                self.first = False
                command = commands[index-1]
                command = command.text.replace("1", "2")
                commands.insert(index-1,Command.create(str(y)))
                commands.insert(index-1,Command.create(command))
            self.command.text = str(x+2)
            
            index = self.list_if_commands.index(self) + 1
            while (index < len(self.list_if_commands)):
                self.list_if_commands[index].set(commands, None, 2)
                index += 1


class Ram:

    

    def __init__(self, start_free_position: int, letters: dict[str, str]) -> None:
        self.start_free_position: int = start_free_position
        self.variables: dict[str, Variable] = {}
        self.last_position: int = 0
        self.letters: dict[str, str] = letters

    def is_variable(self, name: str) -> bool:
        return name in self.variables

    def get_free_position(self) -> int:
        position = self.start_free_position
        self.start_free_position += 1
        return position
    
    def set_variable(self, name: str | None) -> Variable:
        self.variables[name] = Variable(name ,self.get_free_position())
        return self.variables[name]

    def get_variable(self, name: str) -> Variable:
        return self.variables[name]

    def seve_variables(self, commands: list[Command], registers ,target_variable: Variable, line: str, ):
        data, is_same_raw = self.parse_data(line)
        if (data is not None):
            self.set_RAM_position(commands, target_variable)
            if (is_same_raw):
                commands.append(Command.create(f"RAM={data}"))
            else:
                commands.append(Command.create(f"RAM="))
                commands.append(Command.create(data))
            registers.free_register_by_variable(target_variable)
        else:
            register = registers.get_data_to_register(commands, self.letters, line)
            self.set_RAM_position(commands, target_variable)
            commands.append(Command.create(f"RAM={register.name}"))
            registers.free_register_by_variable(target_variable)
            register.variable = target_variable
            register.last_used = 0

        
    def set_RAM_position(self, commands: list[Command] , variable: Variable | int) -> None:
        if isinstance(variable, Variable):
            position = variable.RAM_position
        else:
            position = variable

        if self.last_position == None or self.last_position != position:
            commands.append(Command.create("PTR="))
            commands.append(Command.create(str(position)))
            self.last_position = position

    def reset_last_position(self):
        self.last_position = None



    def parse_data(self,line):
        if (line.startswith("'") and line.endswith("'")):
            return self.letters[line[1:-1]], False
        elif line.isdigit():
            return line, False
        elif line == "input()":
            return "INPUT", True
        else:
            return None, False

class Register:
    def __init__(self, variable: Variable | None, name:str,RAM_position_verified : int ,last_used : int = 0):
        self.variable = variable
        self.name = name
        self.last_used = last_used
        self.RAM_registr_verieble = Variable(None,RAM_position_verified)
        self.number = None
    def Get_RAM_position(self):
        return self.RAM_registr_verieble

    def setNumber(self, number: int) -> None:
        self.number = number
    def getNumber(self) -> int:
        return self.number


class Function:
    def __init__(self, name: str, params: list[str], first_command: Command, ram: Ram) -> None:
        self.name = name
        self.ram = ram
        self.first_command = first_command

        self.params = []
        for param in params:
            self.params.append(self.ram.set_variable(param))

    def call(self, commands: list[Command], registers, params: list[str]) -> None:
        if (len(params) != len(self.params)):
            raise Exception("Function " + self.name + " called with wrong number of parameters")
        
        for i in range(len(params)):
            self.ram.seve_variables(commands, registers, self.params[i], params[i])

        
        commands.append(Command.create("CALL1"))
        c = Command.create(None)
        commands.append(c)
        control_flow = Control_flow(commands, c)
        control_flow.set(commands, commands.index(self.first_command))

        
        

class Registers:
    def __init__(self, ram: Ram):
        self.registers: list[Register] = []
        self.ram: Ram = ram
    
    def add_register(self, name):
        self.registers.append(Register(None, name, self.ram.get_free_position()))

    def last_used_register(self, without_register: list[Register] = None):
        if without_register is None:
            without_register = []

        last_register = None

        for r in self.registers:
            if r in without_register:
                continue

            if last_register is None or r.last_used > last_register.last_used:
                last_register = r

        if last_register is None:
            exit("Neni volny zadny registr")

        return last_register

    def set_variable_to_register(self, commands: list[Command], var: Variable, without_register: list[Register] = None):

        for r in self.registers:
            if r.variable == var and r not in without_register:
                r.last_used = 0
                return r

        free_register = self.get_empty_register(without_register)

        self.ram.set_RAM_position(commands, var)
        commands.append(Command.create(f"{free_register.name}=RAM"))

        free_register.variable = var
        free_register.last_used = 0
        free_register.setNumber(None)
        return free_register

    def input_register(self,commands: list[Command], without_register: list[Register] = None):
        free_register = self.get_empty_register(without_register)
        commands.append(Command.create(free_register.name + "=INPUT"))
        self.free_register(free_register)
        return free_register


    def get_register_with_number(self, number: int, without_register: list[Register] = None):
        if without_register is None:
            without_register = []
        for r in self.registers:
            if r not in without_register and r.getNumber() == number:
                return r
        return None

    def set_register(self,commands: list[Command], inte: str, without_register: list[Register] = None):
        if without_register is None:
            without_register = []
        free_register = self.get_register_with_number(inte, without_register)
        if free_register is not None:
            return free_register    
        
        free_register = self.get_empty_register(without_register)
        commands.append(Command.create(free_register.name + "="))
        commands.append(Command.create(inte))
        free_register.setNumber(inte)
        free_register.variable = None
        return free_register

    def get_empty_register(self, without_register: list[Register] = None) -> Register:
        if without_register is None:
            without_register = []
        for r in self.registers:
            if r not in without_register and r.variable == None:
                r.setNumber(None)
                return r
        r = self.last_used_register(without_register)
        r.setNumber(None)
        return r
    
    def free_register(self, register: Register) -> None:
        register.variable = None

    def free_register_by_variable(self, var: Variable):
        for r in self.registers:
            if r.variable == var:
                r.variable = None

    def free_all_registers(self):
        for r in self.registers:
            r.variable = None
            r.setNumber(None)
    
    def get_data_to_register(self,commands: list[Command], letters: dict[str, str],  line: str, without_register: list[Register] = None):
        if without_register is None:
            without_register = []
        register = None
        
        line = line.strip()
        
        if (self.ram.is_variable(line)):
            src_var = self.ram.get_variable(line)
            register = self.set_variable_to_register(commands, src_var, without_register)

        elif (line.startswith("&") and self.ram.is_variable(line[1:])):
            src_var = self.ram.get_variable(line[1:])
            register = self.set_register(commands, src_var.RAM_position, without_register)

        elif (line.startswith("'") and line.endswith("'")):
            register = self.set_register(commands, letters[line[1:-1]], without_register)
        
        elif (line.isdigit()):
            register = self.set_register(commands,line, without_register)

        elif (line == "input()"):
            register = self.input_register(commands, without_register)


        elif "+" in line or "-" in line:
            tokens = re.findall(r"'.*?'|\w+\(\)|\d+|\w+|[+-]", line)
            last_register = None

            # --- Spilling: Save ALL registers from 'without_register' to RAM ---
            saved_registers = []
            for r in without_register:
                target_ram = None
                if r.variable is not None:
                    target_ram = r.variable.RAM_position
                    self.ram.set_RAM_position(commands, target_ram)
                    commands.append(Command.create(f"RAM={r.name}"))
                else:
                    target_ram = r.Get_RAM_position()
                    self.ram.set_RAM_position(commands, target_ram)
                    commands.append(Command.create(f"RAM={r.name}"))
                
                saved_registers.append((r, r.variable, target_ram, r.number))
                self.free_register(r)

            last_register = self.get_data_to_register(commands, letters, tokens[0], [])

            for i, token in enumerate(tokens):
                if (token != "+" and token != "-"):
                    continue

                # We still need to protect the current math operands from each other
                right_register = self.get_data_to_register(commands, letters, tokens[i+1], [last_register])
                empty_register = self.get_empty_register([last_register, right_register])

                commands.append(Command.create(f"{empty_register.name}={last_register.name}{token}{right_register.name}"))
                empty_register.setNumber(None)
                last_register = empty_register

            # --- Spilling: Move result if it's in a register to be restored ---
            if any(r == last_register for r, var, ram, num in saved_registers):
                busy_restoring = [r for r, var, ram, num in saved_registers]
                new_reg = None
                for r in self.registers:
                    if r not in busy_restoring:
                        new_reg = r
                        break
                
                if new_reg:
                    commands.append(Command.create(f"{new_reg.name}={last_register.name}"))
                    last_register.setNumber(None)
                    last_register = new_reg

            # --- Spilling: Restore saved registers FROM RAM ---
            for r, var, ram, num in saved_registers:
                self.ram.set_RAM_position(commands, ram)
                commands.append(Command.create(f"{r.name}=RAM"))
                r.setNumber(num)
                r.variable = var
                r.last_used = 0

            register = last_register


        else:
            print("error 7632")
            exit(f"Chyba: Příkaz '{line}' není podporován. ")

        return register



class Processor:
    def __init__(self, letters: dict[str, str]):
        
        self.ram: Ram = Ram(4, letters)
        self.registers: Registers = Registers(self.ram)
        self.registers.add_register("A")
        self.registers.add_register("B")
        self.registers.add_register("C")

        self.functions: dict[str, Function] = {}
        self.letters: dict[str, str] = letters
        self.commands: list[Command] = []
        self.if_stack: list[Control_flow] = []
        self.while_stack: list[Command] = []

    def process_command(self, line: str):

        line = line.replace(" ", "")
        operators = ["==", "!=", ">=", "<=", ">", "<"]
        negated = {
            "==": "!=0",
            "!=": "==0",
            ">":  "<=",
            "<":  ">=",
            ">=": "<",
            "<=": ">"
        }

        line = line.strip()
        if not line:
            return

        if (line.startswith("if(") and line.endswith(")")):
            line = line[3:-1].strip()

            for op in operators:
                if op in line:
                    left, right = map(str.strip, line.split(op))
                    break
            else:
                raise ValueError("Neznámý operátor")

            left_register = self.registers.get_data_to_register(self.commands, self.letters, left)
            right_register = self.registers.get_data_to_register(self.commands, self.letters, right, [left_register])

            if op in ["==", "!="]:
                empty = self.registers.get_empty_register([left_register, right_register])
                self.commands.append(Command.create(f"{empty.name}={left_register.name}-{right_register.name}"))

                condition = negated[op]
                self.goto_if(f"{empty.name}{condition}")

            else:
                self.goto_if(f"{left_register.name}{negated[op]}{right_register.name}")

        elif (line == "else"):
            self.goto_else()

        elif (line == "endif"):
            self.goto_if_end()

        elif (line.startswith("while(") and line.endswith(")")):
            line = line[6:-1].strip()
            len_commands = len(self.commands)
            
            for op in operators:
                if op in line:
                    left, right = map(str.strip, line.split(op))
                    break
            else:
                raise ValueError("Neznámý operátor")

            self.registers.free_all_registers()
            self.ram.reset_last_position()

            left_register = self.registers.get_data_to_register(self.commands, self.letters, left)
            right_register = self.registers.get_data_to_register(self.commands, self.letters, right, [left_register])

            if op in ["==", "!="]:
                empty = self.registers.get_empty_register([left_register, right_register])
                self.commands.append(Command.create(f"{empty.name}={left_register.name}-{right_register.name}"))

                condition = negated[op]
                self.goto_while(f"{empty.name}{condition}", self.commands[len_commands])

            else:
                self.goto_while(f"{left_register.name}{negated[op]}{right_register.name}", self.commands[len_commands])


        elif (line == "endwhile"):
            self.goto_while_end()
            

        elif (line.startswith("def")):
            line = line[3:].strip()
            func_name = line.split("(")[0].strip()
            params_str = line[line.find("(") + 1 : line.rfind(")")]
            params = [p.strip() for p in params_str.split(",") if p.strip()]
            self.registers.free_all_registers()
            self.ram.reset_last_position()
            self.commands.append(Command.create("GOTO1"))
            self.commands.append(Command.create(None))
            self.if_stack.append(Control_flow(self.commands, self.commands[-1]))
            command =Command.create_blind_command()
            self.functions[func_name] = Function(func_name, params, command, self.ram)
            

            
            
        elif (line.startswith("enddef")):
            self.commands.append(Command.create("RETURN"))
            self.if_stack.pop().set(self.commands, len(self.commands))
            self.ram.reset_last_position()
            self.registers.free_all_registers()
                        

        elif line.startswith("var") or "=" in line:

            is_declaration = line.startswith("var")

            if is_declaration:
                line = line[3:].strip()


            name, value = map(str.strip, line.split("="))

            if is_declaration:
                target_variable = self.ram.set_variable(name)
            else:
                target_variable = self.ram.get_variable(name)

            # --- vyhodnocení hodnoty ---
            self.ram.seve_variables(self.commands, self.registers, target_variable, value)


        elif line.startswith("print(") and line.endswith(")"):
            line = line[6:-1].strip()

            data, is_same_raw = self.parse_data(line)
            if (data is not None):
                if (is_same_raw):
                    self.commands.append(Command.create(f"DRAW_{data}"))
                else:
                    self.commands.append(Command.create("DRAW"))
                    self.commands.append(Command.create(data))
            else:
                register = self.registers.get_data_to_register(self.commands, self.letters, line)
                self.commands.append(Command.create(f"DRAW_{register.name}"))
                self.registers.free_register(register)
                

        elif line.startswith("input()"):
            register = self.registers.input_register(self.commands)

        elif (func := self.get_function(line)):
            params_str = line[line.find("(") + 1 : line.rfind(")")]
            params = [p.strip() for p in params_str.split(",") if p.strip()]
            func.call(self.commands, self.registers, params)
            self.registers.free_all_registers()

        else:
            exit(f"Chyba: Příkaz '{line}' není podporován.")

        for r in self.registers.registers:
            r.last_used += 1
                
        
    def goto_if(self,subcondition: str):
        if (any(op in subcondition for op in {"==", "!=", "<", ">", "<=", ">="})): 
            self.commands.append(Command.create(f"GOTO1_IF{subcondition}"))
            self.if_stack.append(Control_flow(self.commands))
        else:
            exit(f"Chyba: Příkaz '{subcondition}' není podporován.")
    
    def goto_else(self):
        self.commands.append(Command.create("GOTO1"))
        command = Command.create(None)
        self.commands.append(command)
        self.goto_if_end()
        self.if_stack.append(Control_flow(self.commands, command))

    def goto_if_end(self):
        self.if_stack.pop().set(self.commands, len(self.commands))

    def goto_while(self,subcondition: str, first_command: Command):
        if (any(op in subcondition for op in {"==", "!=", "<", ">", "<=", ">="})): 
            self.commands.append(Command.create(f"GOTO1_IF{subcondition}"))
            self.while_stack.append(first_command)
            self.if_stack.append(Control_flow(self.commands))
        else:
            exit(f"Chyba: Příkaz '{subcondition}' není podporován.")

    def goto_while_end(self):
        while_start = self.while_stack.pop()
        self.commands.append(Command.create("GOTO1"))
        Control_flow(self.commands).set(self.commands, self.commands.index(while_start))
        self.goto_if_end()


    def get_function(self, line: str) -> Function | None:
        for func in self.functions:
            if line.startswith(func + "("):
                return self.functions[func]
        return None

    def parse_data(self,line):
        if (line.startswith("'") and line.endswith("'")):
            return self.letters[line[1:-1]], False
        elif line.isdigit():
            return line, False
        elif line == "input()":
            return "INPUT", True
        else:
            return None, False


if __name__ == "__main__":
    latters_path = "latters/latters.txt"
    my_code_path = "scripts/myCode.txt"


    letters = {}
    if os.path.exists(latters_path):
        with open(latters_path, "r") as f:
            for i, letter in enumerate(f.read().splitlines()):
                if letter == "\\\\":
                    continue
                letters[letter] = i
    else:
        print(f"Chyba: {latters_path} neexistuje.")
        exit(1)

    processor : Processor = Processor(letters)

    if os.path.exists(my_code_path):
        with open(my_code_path, "r") as f:
            for line in f:
                line = line.split("//")[0].strip()
                if not line:
                    continue
                processor.process_command(line)  
            processor.commands.append(Command("END"))
    else:
        print(f"Chyba: {my_code_path} neexistuje.")
        exit(1)
    
    if processor.commands:
        print("Generované assemblery:")
        print([value.text for value in processor.commands])
        compile_assembly.main([value.text for value in processor.commands])
    else:
        print("Žádné příkazy k sestavení.")
