import os
import sys
import compile as compiler_mod
import test_assembly as simulator_mod

def load_letters(letters_path):
    letters = {}
    if os.path.exists(letters_path):
        with open(letters_path, "r") as f:
            for i, letter in enumerate(f.read().splitlines()):
                if letter == "\\\\":
                    continue
                letters[letter] = i
        return letters
    else:
        raise ValueError(f"Chyba: {letters_path} neexistuje.")

def compile_file(file_path, letters):
    processor = compiler_mod.Processor(letters, 8)
    with open(file_path, "r") as f:
        for line in f:
            line = line.split("//")[0].strip()
            if not line:
                continue
            processor.process_command(line)
        processor.commands.append(compiler_mod.Command("END"))
        if (len(processor.if_stack) > 0):
            raise ValueError(f"Chyba v {file_path}: Není uzavřený if.")
        if (len(processor.while_stack) > 0):
            raise ValueError(f"Chyba v {file_path}: Není uzavřený while.")
    return [cmd.text for cmd in processor.commands]

def run_simulator(tokens, letters):
    sim = simulator_mod.Simulator(tokens, letters)
    # Run until it hits END or errors
    # Note: We need a non-interactive way to run it.
    # Looking at Simulator.run(), it expects user input.
    # I'll manually step through it.
    max_steps = 10000
    steps = 0
    while sim.running and steps < max_steps:
        sim.step()
        steps += 1
    
    if steps >= max_steps:
        raise Exception("Simulation exceeded maximum steps (possible infinite loop).")
    
    return sim.outputs

def run_tests():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "../.."))
    letters_path = os.path.join(project_root, "letters/letters.txt")
    tests_dir = os.path.join(project_root, "scripts/tests")
    
    try:
        letters = load_letters(letters_path)
    except Exception as e:
        print(f"Error loading letters: {e}")
        return

    if not os.path.exists(tests_dir):
        print(f"Tests directory not found: {tests_dir}")
        return

    test_files = [f for f in os.listdir(tests_dir) if f.endswith(".txt")]
    passed_all = True
    any_tests = False

    for test_file in sorted(test_files):
        expected_file = test_file.replace(".txt", ".expected")
        expected_path = os.path.join(tests_dir, expected_file)
        
        if not os.path.exists(expected_path):
            continue

        any_tests = True
        test_path = os.path.join(tests_dir, test_file)
        print(f"Running test: {test_file}...", end=" ", flush=True)

        try:
            tokens = compile_file(test_path, letters)
            actual_outputs = run_simulator(tokens, letters)
            
            with open(expected_path, "r") as f:
                expected_outputs = [int(line.strip()) for line in f if line.strip()]
            
            if actual_outputs == expected_outputs:
                print("\033[92mPASSED\033[0m")
            else:
                print("\033[91mFAILED\033[0m")
                passed_all = False
                print("Differences:")
                print(f"  Expected: {expected_outputs}")
                print(f"  Actual:   {actual_outputs}")
        except Exception as e:
            print(f"\033[91mERROR\033[0m: {e}")
            passed_all = False

    if not any_tests:
        print("No tests found in scripts/tests/ (files with .txt and .expected extension).")
    elif passed_all:
        print("\n\033[92mVšechny testy prošly!\033[0m")
    else:
        print("\n\033[91mNěkteré testy selhaly.\033[0m")

if __name__ == "__main__":
    run_tests()
