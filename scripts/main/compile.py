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
        if Command.saved_commands is not None:
            return Command.saved_commands
        command = Command(None)
        Command.saved_commands = command
        return command

    def __str__(self) -> str:
        return self.text

class Variable:
    level = 0
    def __init__(self, name: str | None, RAM_position: int, is_array: bool = False) -> None:
        self.name = name
        self.RAM_position = RAM_position
        self.level = Variable.level
        self.is_array = is_array


class Control_flow:
    x_length = 256
    list_if_commands = [] 

    def name(self, commands: list[Command]) -> str:
        index = commands.index(self.start_command)
        return commands[index-1].text



    def __init__(self, commands: list[Command], command: Command | None = None) -> None:
        if command is None:
            self.start_command = Command.create(None)
            commands.append(self.start_command)
        else:
            self.start_command = command
        self.list_if_commands.append(self)
        self.first = True
        self.end_command = None
    
    def set(self, commands: list[Command], position: Command | None) -> None:
        if self.end_command is None:
            self.end_command = position

        index_end = commands.index(self.end_command) if self.end_command in commands else len(commands)
        index_start = commands.index(self.start_command) if self.start_command in commands else len(commands)

        y = index_end // self.x_length
        x = index_end % self.x_length
        if (y != (index_start // self.x_length)):
            if self.first:
                self.first = False
                old_command = commands[index_start-1]
                new_text = old_command.text.replace("1", "2")
                commands.insert(index_start-1,Command(str(y)))
                commands.insert(index_start-1,Command(new_text))
                for command in self.list_if_commands:
                    if(command.end_command in commands and commands.index(command.end_command) == index_start+1):
                        print(command.end_command.text)
                        command.end_command = commands[index_start-1]
                    command.set(commands, None)
                return

        self.start_command.text = str(x)


class Ram:
    def __init__(self, start_free_position: int, letters: dict[str, str], param_stack_max_size: int = 16) -> None:
        # RAM layout:
        # 0..3: registry (existing)
        # 4: Stack Pointer (SP)
        # 5..5+max_size-1: Parameter Stack
        # 5+max_size..: free memory for variables
        self.sp_address: int = start_free_position  # = 4
        self.param_stack_base: int = start_free_position + 1  # = 5
        self.param_stack_max_size: int = param_stack_max_size
        self.start_free_position: int = self.param_stack_base + param_stack_max_size
        self.level_start_positions: list[int] = []
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

    #NEBEZPECNY PROTOZE PRI VYTVARENI NEMUSI BYT ZASEBOU
    def set_array(self, length: int, name: str,registers, commands: list[Command], data: list[str] = []) -> Variable:
        var = self.set_variable(name)
        var.is_array = True
        self.seve_variables(commands, registers, self.variables[name], data[0])
        for i in range(1,length):
            free_position = self.get_free_position()
            item, is_same_raw = self.parse_data(data[i])
            self.set_RAM_position(commands, free_position)
            if (item is not None):
                if (is_same_raw):
                    commands.append(Command.create(f"RAM={item}"))
                else:
                    commands.append(Command.create("RAM="))
                    commands.append(Command.create(item))
            else:
                register = registers.get_data_to_register(commands, self.letters, data[i])
                self.set_RAM_position(commands, free_position)
                commands.append(Command.create(f"RAM={register.name}"))
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

    def remove_verieble_under_level(self, level: int):
        self.variables = {
            name: variable
            for name, variable in self.variables.items()
            if variable.level <= level
        }
    
        
    def set_RAM_position(self, commands: list[Command] , variable: Variable | int, level: int = 0) -> None:
        if isinstance(variable, Variable):
            position = variable.RAM_position
        else:
            position = variable

        if self.last_position == None or self.last_position != position:
            commands.append(Command.create("PTR="))
            commands.append(Command.create(str(position)))
            self.last_position = position

        for _ in range(level):
            commands.append(Command.create("PTR=RAM"))

        if (level > 0):    
            self.reset_last_position()


    def reset_last_position(self):
        self.last_position = None

    def emit_push_param(self, commands: list, registers, value_str: str) -> None:
        """Push a parameter value onto the param stack.
        Generates: read SP, write value at stack[SP], increment SP, write SP back."""
        # Load the value into a register first
        register = registers.get_data_to_register(commands, self.letters, value_str)

        # Read SP into another register
        sp_reg = registers.get_empty_register([register])
        self.set_RAM_position(commands, self.sp_address)
        commands.append(Command.create(f"{sp_reg.name}=RAM"))

        # Write value to stack[SP]
        commands.append(Command.create(f"PTR={sp_reg.name}"))
        self.reset_last_position()
        commands.append(Command.create(f"RAM={register.name}"))
        registers.free_register(register)

        # Increment SP
        one_reg = registers.get_empty_register([sp_reg])
        commands.append(Command.create(f"{one_reg.name}="))
        commands.append(Command.create("1"))
        result_reg = registers.get_empty_register([sp_reg, one_reg])
        commands.append(Command.create(f"{result_reg.name}={sp_reg.name}+{one_reg.name}"))
        registers.free_register(sp_reg)
        registers.free_register(one_reg)

        # Write SP back
        self.set_RAM_position(commands, self.sp_address)
        commands.append(Command.create(f"RAM={result_reg.name}"))
        registers.free_register(result_reg)

    def emit_pop_param(self, commands: list, registers, target_variable) -> None:
        """Pop a parameter from the param stack into a target variable.
        Generates: decrement SP, read value from stack[SP], store into variable."""
        # Read SP
        sp_reg = registers.get_empty_register()
        self.set_RAM_position(commands, self.sp_address)
        commands.append(Command.create(f"{sp_reg.name}=RAM"))

        # Decrement SP
        one_reg = registers.get_empty_register([sp_reg])
        commands.append(Command.create(f"{one_reg.name}="))
        commands.append(Command.create("1"))
        result_reg = registers.get_empty_register([sp_reg, one_reg])
        commands.append(Command.create(f"{result_reg.name}={sp_reg.name}-{one_reg.name}"))
        registers.free_register(sp_reg)
        registers.free_register(one_reg)

        # Write decremented SP back
        self.set_RAM_position(commands, self.sp_address)
        commands.append(Command.create(f"RAM={result_reg.name}"))

        # Read value from stack[SP]
        commands.append(Command.create(f"PTR={result_reg.name}"))
        self.reset_last_position()
        val_reg = registers.get_empty_register([result_reg])
        commands.append(Command.create(f"{val_reg.name}=RAM"))
        registers.free_register(result_reg)

        # Store into target variable
        self.set_RAM_position(commands, target_variable)
        commands.append(Command.create(f"RAM={val_reg.name}"))
        registers.free_register(val_reg)

    def emit_init_sp(self, commands: list) -> None:
        """Initialize stack pointer to param_stack_base at program start."""
        commands.append(Command.create("PTR="))
        commands.append(Command.create(str(self.sp_address)))
        commands.append(Command.create("RAM="))
        commands.append(Command.create(str(self.param_stack_base)))
        self.last_position = self.sp_address

    def inc_level(self):
        self.level_start_positions.append(self.start_free_position)
        Variable.level += 1

    def dec_level(self, revert_position: bool = True):
        Variable.level -= 1
        self.remove_verieble_under_level(Variable.level)
        if self.level_start_positions:
            old_pos = self.level_start_positions.pop()
            if revert_position:
                self.start_free_position = old_pos



    def parse_data(self,line):
        if (line.startswith("'") and line.endswith("'")):
            return self.letters[line[1:-1]], False
        elif line.isdigit():
            return line, False
        elif line == "input()":
            return "INPUT", True
        elif line.startswith("&") and self.is_variable(line[1:]):
            return self.get_variable(line[1:]).RAM_position, False
        else:
            return None, False

class Register:
    def __init__(self, variable: Variable | None, name:str ,last_used : int = 0):
        self.variable = variable
        self.name = name
        self.last_used = last_used
        self.number = None
        self.save_data = None
        self.RAM_static_position = None

    def setNumber(self, number: int) -> None:
        self.number = number
    def getNumber(self) -> int:
        return self.number

    def save_registr(self, commands: list[Command], ram: Ram):
        target_ram = None
        if (self.RAM_static_position is not None):
            target_ram = self.RAM_static_position
        elif self.variable is not None:
            target_ram = self.variable.RAM_position
        else:
            target_ram = Variable(None,ram.get_free_position())
            self.RAM_static_position = target_ram
        
        self.save_data = {"position": target_ram, "variable": self.variable, "number": self.number}

        ram.set_RAM_position(commands, target_ram)
        commands.append(Command.create(f"RAM={self.name}"))

    def load_registr(self, commands, ram):
        ram.set_RAM_position(commands, self.save_data["position"])
        self.number = self.save_data["number"]
        self.variable = self.save_data["variable"]
        self.save_data = None
        commands.append(Command.create(f"{self.name}=RAM"))


class Function:
    def __init__(self, name: str, param_names: list[str], first_command: Command, ram: Ram) -> None:
        self.name = name
        self.ram = ram
        self.first_command = first_command
        self.param_names = param_names  # just names, no RAM allocation

    def emit_pop_params(self, commands: list[Command], registers) -> None:
        """Generate code at function entry to pop params from stack into local variables.
        Params are popped in reverse order (last pushed = first popped)."""
        for param_name in reversed(self.param_names):
            var = self.ram.set_variable(param_name)
            self.ram.emit_pop_param(commands, registers, var)


    def call(self, commands: list[Command], registers, params: list[str]) -> None:
        if (len(params) != len(self.param_names)):
            raise Exception("Function " + self.name + " called with wrong number of parameters")
        
        # Push all params onto the stack (left to right)
        for param_value in params:
            self.ram.emit_push_param(commands, registers, param_value)

        commands.append(Command.create("CALL1"))
        c = Command.create(None)
        commands.append(c)
        control_flow = Control_flow(commands, c)
        control_flow.set(commands, self.first_command)

class ExpressionParser:
    def __init__(self, registers_obj, commands, letters):
        self.registers_obj = registers_obj
        self.commands = commands
        self.letters = letters
        self.tokens = []
        self.pos = 0

    def tokenize(self, line):
        self.tokens = re.findall(r"\(|\)|\[|\]|\+|\-|\*|&|[a-zA-Z_]\w*|'[^\']'|\d+", line)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected=None):
        token = self.peek()
        if expected and token != expected:
            raise Exception(f"Expected {expected}, got {token}")
        self.pos += 1
        return token

    def parse_expression(self, without_register):
        return self.parse_math(without_register)

    def parse_math(self, without_register):
        reg = self.parse_term(without_register)
        while self.peek() in ('+', '-'):
            op = self.consume()
            right_reg = self.parse_term(without_register + [reg])
            empty_reg = self.registers_obj.get_empty_register(without_register + [reg, right_reg])
            self.commands.append(Command.create(f"{empty_reg.name}={reg.name}{op}{right_reg.name}"))
            self.registers_obj.free_register(reg)
            self.registers_obj.free_register(right_reg)
            reg = empty_reg
        return reg

    def parse_term(self, without_register):
        reg = self.parse_factor(without_register)
        while self.peek() == '[':
            self.consume('[')
            index_reg = self.parse_expression(without_register + [reg])
            self.consume(']')

            if (len(without_register) > 0):
                self.registers_obj.save_registers(self.commands,without_register)
            
            addr_reg = self.registers_obj.get_empty_register([reg, index_reg])
            self.commands.append(Command.create(f"{addr_reg.name}={reg.name}+{index_reg.name}"))
            self.commands.append(Command.create(f"PTR={addr_reg.name}"))
            self.registers_obj.ram.reset_last_position()
            
            self.registers_obj.free_register(reg)
            self.registers_obj.free_register(index_reg)
            self.registers_obj.free_register(addr_reg)
            reg = self.registers_obj.load_in_to_register_from_ram(self.commands)

            if (len(without_register) > 0):
                reg = self.registers_obj.load_registers(self.commands,without_register,reg)

        return reg

    def parse_factor(self, without_register):
        token = self.consume()
        if token == '*':
            # Lookahead: is the next token a simple variable?
            next_token = self.peek()
            if next_token and self.registers_obj.ram.is_variable(next_token):
                var = self.registers_obj.ram.get_variable(next_token)
                if not var.is_array:
                    self.consume() # consume the variable token
                    self.registers_obj.ram.set_RAM_position(self.commands, var)
                    self.commands.append(Command.create("PTR=RAM"))
                    self.registers_obj.ram.reset_last_position()
                    return self.registers_obj.load_in_to_register_from_ram(self.commands, without_register)

            addr_reg = self.parse_factor(without_register)
            self.commands.append(Command.create(f"PTR={addr_reg.name}"))
            self.registers_obj.ram.reset_last_position()
            self.registers_obj.free_register(addr_reg)
            return self.registers_obj.load_in_to_register_from_ram(self.commands, without_register)
        elif token == '&':
            name = self.consume()
            var = self.registers_obj.ram.get_variable(name)
            return self.registers_obj.set_register(self.commands, str(var.RAM_position), without_register)
        elif token == '(':
            reg = self.parse_expression(without_register)
            self.consume(')')
            return reg
        elif token.startswith("'"):
            val = self.letters.get(token[1:-1], 0)
            return self.registers_obj.set_register(self.commands, str(val), without_register)
        elif token.isdigit():
            return self.registers_obj.set_register(self.commands, token, without_register)
        elif self.registers_obj.ram.is_variable(token):
            var = self.registers_obj.ram.get_variable(token)
            if var.is_array:
                return self.registers_obj.set_register(self.commands, str(var.RAM_position), without_register)
            else:
                return self.registers_obj.set_variable_to_register(self.commands, var, without_register)
        else:
            raise Exception(f"Unexpected token in factor: {token}")

class Registers:
    def __init__(self, ram: Ram):
        self.registers: list[Register] = []
        self.ram: Ram = ram
    
    def add_register(self, name):
        self.registers.append(Register(None, name))

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
            raise ValueError("Neni volny zadny registr")

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
        free_register.number = None
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
        self.free_register(free_register)
        free_register.setNumber(inte)
        return free_register

    def load_in_to_register_from_ram(self,commands: list[Command], without_register: list[Register] = None):
        free_register = self.get_empty_register(without_register)
        commands.append(Command.create(free_register.name + "=RAM"))
        free_register.number = None
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
        self.free_register(r)
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


    def get_level_and_variable(self, line: str) -> tuple[int, Variable]:
        level = 0
        while line.startswith("*"):
            level += 1
            line = line[1:]
        return level, self.ram.get_variable(line)

    def save_registers(self, commands: list[Command], registers: list[Register]):
        for r in registers:
            r.save_registr(commands, self.ram)
            self.free_register(r)

    def load_registers(self, commands: list[Command], registers: list[Register], without_register: Register) -> Register:
        if any(r == without_register for r in registers):
            busy_restoring = [r for r in registers]
            new_reg = None
            for r in self.registers:
                if r not in busy_restoring:
                    new_reg = r
                    self.free_register(new_reg)
                    break
            
            if new_reg:
                    commands.append(Command.create(f"{new_reg.name}={without_register.name}"))
                    without_register.setNumber(None)
                    without_register = new_reg

        
        for r in registers:
            r.load_registr(commands, self.ram)

        return without_register
        
    
    def get_data_to_register(self,commands: list[Command], letters: dict[str, str],  line: str, without_register: list[Register] = None):
        parser = ExpressionParser(self, commands, letters)
        parser.tokenize(line)
        return parser.parse_expression(without_register or [])


        
        return register



class Processor:
    def __init__(self, letters: dict[str, str], param_stack_max_size: int = 16):
        
        self.ram: Ram = Ram(4, letters, param_stack_max_size)
        self.registers: Registers = Registers(self.ram)
        self.registers.add_register("A")
        self.registers.add_register("B")
        self.registers.add_register("C")

        self.functions: dict[str, Function] = {}
        self.letters: dict[str, str] = letters
        self.commands: list[Command] = []
        self.if_stack: list[Control_flow] = []
        self.while_stack: list[Command] = []

        # Initialize SP at program start
        self.ram.emit_init_sp(self.commands)

    def process_command(self, line: str):

        line = self.remove_spaces_outside_quotes(line)
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

        if (line.startswith("pass")):
            if "*" in line:
                times = int(line.split("*")[1])
                for _ in range(times):
                    self.commands.append(Command.create("NOP"))
            else:
                self.commands.append(Command.create("NOP"))


        elif (line.startswith("if(") and line.endswith(")")):
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

            self.ram.inc_level()

        elif (line == "else"):
            self.goto_else()

        elif (line == "endif"):
            self.goto_if_end()
            self.registers.free_all_registers()
            self.ram.reset_last_position()
            self.ram.dec_level()

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

            self.ram.inc_level()

        elif (line == "endwhile"):
            self.goto_while_end()
            self.registers.free_all_registers()
            self.ram.reset_last_position()
            self.ram.dec_level()
            

        elif (line.startswith("def")):
            self.ram.inc_level()
            line = line[3:].strip()
            func_name = line.split("(")[0].strip()
            params_str = line[line.find("(") + 1 : line.rfind(")")]
            params = [p.strip() for p in params_str.split(",") if p.strip()]
            self.registers.free_all_registers()
            self.ram.reset_last_position()
            self.commands.append(Command.create("GOTO1"))
            self.commands.append(Command.create(None))
            self.if_stack.append(Control_flow(self.commands, self.commands[-1]))
            command = Command.create_blind_command()
            func = Function(func_name, params, command, self.ram)
            self.functions[func_name] = func
            # Emit pop code at function entry to read params from stack into local vars
            func.emit_pop_params(self.commands, self.registers)
            self.registers.free_all_registers()
            self.ram.reset_last_position()
            

            
            
        elif (line == "enddef"):
            self.commands.append(Command.create("RETURN"))
            self.if_stack.pop().set(self.commands, Command.create_blind_command())
            self.registers.free_all_registers()
            self.ram.reset_last_position()
            self.ram.dec_level(revert_position=False)
                        

        elif line.startswith("var") or "=" in line:

            is_declaration = line.startswith("var")

            if is_declaration:
                line = line[3:].strip()
            

            name_value = [part.strip() for part in line.split("=")]
            target_name = name_value[0]

            if is_declaration:
                if target_name.endswith("]") and (len(name_value) > 1):
                    data_string = name_value[1]
                    if ((data_string.startswith("{") and data_string.endswith("}")) or (data_string.startswith("[") and data_string.endswith("]"))):
                        data = data_string[1:-1].split(",")
                        bracket_pos = target_name.find("[")
                        name = target_name[:bracket_pos]
                        target_variable = self.ram.set_array(len(data), name, self.registers, self.commands, data)
                        return

                if target_name.endswith("]"):
                    bracket_pos = target_name.find("[")
                    size = int(target_name[bracket_pos + 1 : -1])
                    name = target_name[:bracket_pos]
                    data = []
                    if (len(name_value) > 1):
                        data_string = name_value[1]
                        if ((data_string.startswith("{") and data_string.endswith("}")) or (data_string.startswith("[") and data_string.endswith("]"))):
                            data = data_string[1:-1].split(",")
                        
                    target_variable = self.ram.set_array(size, name, self.registers, self.commands, data)
                    return                    
                else:
                    target_variable = self.ram.set_variable(target_name)


            if (len(name_value) == 1):
                return

            value = name_value[1]

            if (target_name.startswith("console")):
                target = target_name[8:]
                data, is_same_row = self.ram.parse_data(value)
                if data is not None:
                    if is_same_row:
                        self.commands.append(Command.create(f"{target}={data}"))
                    else:
                        self.commands.append(Command.create(f"{target}="))
                        self.commands.append(Command.create(data))
                else:
                    if (self.ram.is_variable(value)):
                        self.ram.set_RAM_position(self.commands, self.ram.get_variable(value))
                        self.commands.append(Command.create(f"{target}=RAM"))
                    elif value.startswith("*") and self.ram.is_variable(value[1:]) and not "+" in value and not "-" in value:
                        var = self.ram.get_variable(value[1:])
                        self.ram.set_RAM_position(self.commands, var)
                        self.commands.append(Command.create("PTR=RAM"))
                        self.ram.reset_last_position()
                        self.commands.append(Command.create(f"{target}=RAM"))
                    elif "[" in value and value.endswith("]") and not "(" in value and not "*" in value:
                        bracket_pos = value.rfind("[")
                        array_name = value[:bracket_pos]
                        index_str = value[bracket_pos+1:-1]
                        if self.ram.is_variable(array_name):
                            array_var = self.ram.get_variable(array_name)
                            if index_str.isdigit():
                                self.ram.set_RAM_position(self.commands, array_var.RAM_position + int(index_str))
                                self.commands.append(Command.create(f"{target}=RAM"))
                            else:
                                idx_reg = self.registers.get_data_to_register(self.commands, self.letters, index_str)
                                base_reg = self.registers.set_register(self.commands, str(array_var.RAM_position), [idx_reg])
                                addr_reg = self.registers.get_empty_register([idx_reg, base_reg])
                                self.commands.append(Command.create(f"{addr_reg.name}={base_reg.name}+{idx_reg.name}"))
                                self.commands.append(Command.create(f"PTR={addr_reg.name}"))
                                self.ram.reset_last_position()
                                self.registers.free_register(idx_reg)
                                self.registers.free_register(base_reg)
                                self.registers.free_register(addr_reg)
                                self.commands.append(Command.create(f"{target}=RAM"))
                        else:
                            register = self.registers.get_data_to_register(self.commands, self.letters, value)
                            self.commands.append(Command.create(f"{target}={register.name}"))
                    else:
                        register = self.registers.get_data_to_register(self.commands, self.letters, value)
                        self.commands.append(Command.create(f"{target}={register.name}"))
                
                return
               

            if target_name.startswith("*"):
                level, ptr_var = self.registers.get_level_and_variable(target_name)
                data, is_same_row = self.ram.parse_data(value)
                if data is not None:
                    self.ram.set_RAM_position(self.commands, ptr_var.RAM_position, level)
                    if is_same_row:
                        self.commands.append(Command.create(f"RAM={data}"))
                    else:
                        self.commands.append(Command.create("RAM="))
                        self.commands.append(Command.create(data))
                else:
                    register = self.registers.get_data_to_register(self.commands, self.letters, value)
                    self.ram.set_RAM_position(self.commands, ptr_var.RAM_position, level)
                    self.commands.append(Command.create(f"RAM={register.name}"))
                return
            
            if target_name.endswith("]"):
                bracket_pos = target_name.find("[")
                index_str = target_name[bracket_pos + 1 : -1]
                array_name = target_name[:bracket_pos]
                variable = self.ram.get_variable(array_name)
                
                if index_str.isdigit():
                    # Statický index: pole[2] = value
                    index = int(index_str)
                    position = variable.RAM_position + index
                    register = self.registers.get_data_to_register(self.commands, self.letters, value)
                    self.ram.set_RAM_position(self.commands, position)
                    self.commands.append(Command.create(f"RAM={register.name}"))
                else:
                    idx_reg = self.registers.get_data_to_register(self.commands, self.letters, index_str)
                    addr_reg = self.registers.get_empty_register([idx_reg])
                    empty_reg = self.registers.get_empty_register([addr_reg, idx_reg])
                    self.commands.append(Command.create(f"{addr_reg.name}="))
                    self.commands.append(Command.create(str(variable.RAM_position)))
                    self.commands.append(Command.create(f"{empty_reg.name}={addr_reg.name}+{idx_reg.name}"))
                    val_reg = self.registers.get_data_to_register(self.commands, self.letters, value, [empty_reg])
                    self.commands.append(Command.create(f"PTR={empty_reg.name}"))
                    self.ram.reset_last_position()
                    self.commands.append(Command.create(f"RAM={val_reg.name}"))
                    
                return
            else:
                target_variable = self.ram.get_variable(target_name)

            

            if (value.startswith("&") and self.ram.is_variable(value[1:])):
                self.ram.set_RAM_position(self.commands, target_variable)
                src_var = self.ram.get_variable(value[1:])
                self.commands.append(Command.create("RAM="))
                self.commands.append(Command.create(str(src_var.RAM_position)))
                
            else:
                self.ram.seve_variables(self.commands, self.registers, target_variable, value)


        elif line.startswith("print(") and line.endswith(")"):
            line = line[6:-1].strip()

            data, is_same_raw = self.ram.parse_data(line)
            if (data is not None):
                if (is_same_raw):
                    self.commands.append(Command.create(f"DRAW_{data}"))
                else:
                    self.commands.append(Command.create("DRAW"))
                    self.commands.append(Command.create(data))
            else:
                if (self.ram.is_variable(line)):
                    self.ram.set_RAM_position(self.commands, self.ram.get_variable(line))
                    self.commands.append(Command.create("DRAW_RAM"))
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
            raise ValueError(f"Chyba: Příkaz '{line}' není podporován.")

        for r in self.registers.registers:
            r.last_used += 1
                
        
    def goto_if(self,subcondition: str):
        if (any(op in subcondition for op in {"==", "!=", "<", ">", "<=", ">="})): 
            self.commands.append(Command.create(f"GOTO1_IF{subcondition}"))
            self.if_stack.append(Control_flow(self.commands))
        else:
            raise ValueError(f"Chyba: Příkaz '{subcondition}' není podporován.")
    
    def goto_else(self):
        self.commands.append(Command.create("GOTO1"))
        command = Command.create(None)
        self.commands.append(command)
        self.goto_if_end()
        self.if_stack.append(Control_flow(self.commands, command))

    def goto_if_end(self):
        self.if_stack.pop().set(self.commands, Command.create_blind_command())

    def goto_while(self,subcondition: str, first_command: Command):
        if (any(op in subcondition for op in {"==", "!=", "<", ">", "<=", ">="})): 
            self.commands.append(Command.create(f"GOTO1_IF{subcondition}"))
            self.while_stack.append(first_command)
            self.if_stack.append(Control_flow(self.commands))
        else:
            raise ValueError(f"Chyba: Příkaz '{subcondition}' není podporován.")

    def goto_while_end(self):
        while_start = self.while_stack.pop()
        self.commands.append(Command.create("GOTO1"))
        Control_flow(self.commands).set(self.commands, while_start)
        self.goto_if_end()


    def get_function(self, line: str) -> Function | None:
        for func in self.functions:
            if line.startswith(func + "("):
                return self.functions[func]
        return None


    def remove_spaces_outside_quotes(self, text: str) -> str:
        result = []
        in_single = False
        in_double = False

        for char in text:
            if char == "'" and not in_double:
                in_single = not in_single
                result.append(char)
            elif char == '"' and not in_single:
                in_double = not in_double
                result.append(char)
            elif char == " " and not in_single and not in_double:
                continue  # přeskočíme mezeru mimo uvozovky
            else:
                result.append(char)

        return "".join(result)


if __name__ == "__main__":
    letters_path = "letters/letters.txt"
    my_code_path = "scripts/myCode.txt"


    letters = {}
    if os.path.exists(letters_path):
        with open(letters_path, "r") as f:
            for i, letter in enumerate(f.read().splitlines()):
                if letter == "\\\\":
                    continue
                letters[letter] = i
    else:
        raise ValueError(f"Chyba: {letters_path} neexistuje.")

    processor : Processor = Processor(letters, 8)

    if os.path.exists(my_code_path):
        with open(my_code_path, "r") as f:
            for line in f:
                line = line.split("//")[0].strip()
                if not line:
                    continue
                processor.process_command(line)  
            processor.commands.append(Command("END"))
            if (len(processor.if_stack) > 0):
                raise ValueError("Chyba: Není uzavřený if.")
            if (len(processor.while_stack) > 0):
                raise ValueError("Chyba: Není uzavřený while.")
    else:
        raise ValueError(f"Chyba: {my_code_path} neexistuje.")
    
    if processor.commands:
        print("Generované assemblery:")
        compile_assembly.main([value.text for value in processor.commands])
    else:
        print("Žádné příkazy k sestavení.")
