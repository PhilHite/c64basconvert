#!/usr/bin/env python3
"""
c64basconvert.py
Converts a plain text C64 BASIC .txt file to a properly structured
C64 BASIC binary with:
  - 2-byte load address header: $01 $08 (=$0801)
  - Per-line structure: [next-line ptr 2 bytes][line number 2 bytes][tokens][0x00]
  - Program end marker: $00 $00
  - ASCII to PETSCII conversion (lowercase -> uppercase)
  - Line endings handled correctly
  - Output filename is automatically converted to uppercase

Usage:
    c64basconvert INPUTFILE.txt OUTPUTFILE.PRG
"""

import sys
import os


# C64 BASIC V2 keyword token table
# Maps keyword strings to their token bytes (0x80+)
TOKENS = {
    "END":0x80,"FOR":0x81,"NEXT":0x82,"DATA":0x83,"INPUT#":0x84,
    "INPUT":0x85,"DIM":0x86,"READ":0x87,"LET":0x88,"GOTO":0x89,
    "RUN":0x8A,"IF":0x8B,"RESTORE":0x8C,"GOSUB":0x8D,"RETURN":0x8E,
    "REM":0x8F,"STOP":0x90,"ON":0x91,"WAIT":0x92,"LOAD":0x93,
    "SAVE":0x94,"VERIFY":0x95,"DEF":0x96,"POKE":0x97,"PRINT#":0x98,
    "PRINT":0x99,"CONT":0x9A,"LIST":0x9B,"CLR":0x9C,"CMD":0x9D,
    "SYS":0x9E,"OPEN":0x9F,"CLOSE":0xA0,"GET":0xA1,"NEW":0xA2,
    "TAB(":0xA3,"TO":0xA4,"FN":0xA5,"SPC(":0xA6,"THEN":0xA7,
    "NOT":0xA8,"STEP":0xA9,"+":0xAA,"-":0xAB,"*":0xAC,"/":0xAD,
    "^":0xAE,"AND":0xAF,"OR":0xB0,">":0xB1,"=":0xB2,"<":0xB3,
    "SGN":0xB4,"INT":0xB5,"ABS":0xB6,"USR":0xB7,"FRE":0xB8,
    "POS":0xB9,"SQR":0xBA,"RND":0xBB,"LOG":0xBC,"EXP":0xBD,
    "COS":0xBE,"SIN":0xBF,"TAN":0xC0,"ATN":0xC1,"PEEK":0xC2,
    "LEN":0xC3,"STR$":0xC4,"VAL":0xC5,"ASC":0xC6,"CHR$":0xC7,
    "LEFT$":0xC8,"RIGHT$":0xC9,"MID$":0xCA,"GO":0xCB,
}

# Sort by length descending so longer keywords match first (e.g. PRINT# before PRINT)
SORTED_TOKENS = sorted(TOKENS.keys(), key=lambda k: -len(k))


def ascii_to_petscii(ch):
    """Convert a single ASCII character to PETSCII."""
    o = ord(ch)
    if 0x61 <= o <= 0x7A:  # lowercase a-z -> uppercase
        return o - 0x20
    return o


def tokenise_line(text):
    """
    Tokenise a line of BASIC text into C64 BASIC bytes.
    Keywords outside of strings/REM are replaced with token bytes.
    """
    result = bytearray()
    i = 0
    in_string = False
    in_rem = False

    while i < len(text):
        ch = text[i]

        # Inside a string - pass through as PETSCII, no tokenising
        if in_string:
            if ch == '"':
                in_string = False
            result.append(ascii_to_petscii(ch))
            i += 1
            continue

        # Inside a REM - pass through rest of line as PETSCII
        if in_rem:
            result.append(ascii_to_petscii(ch))
            i += 1
            continue

        # Start of string
        if ch == '"':
            in_string = True
            result.append(ascii_to_petscii(ch))
            i += 1
            continue

        # Try to match a keyword (case-insensitive)
        matched = False
        upper_rest = text[i:].upper()
        for kw in SORTED_TOKENS:
            if upper_rest.startswith(kw):
                result.append(TOKENS[kw])
                i += len(kw)
                if kw == "REM":
                    in_rem = True
                matched = True
                break

        if not matched:
            result.append(ascii_to_petscii(ch))
            i += 1

    return bytes(result)


def convert(input_path, output_path):
    if not os.path.isfile(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    # Uppercase the output filename (keep directory intact)
    output_dir = os.path.dirname(output_path)
    output_filename = os.path.basename(output_path).upper()
    output_path = os.path.join(output_dir, output_filename) if output_dir else output_filename

    with open(input_path, "r", encoding="latin-1") as f:
        raw_content = f.read()

    if not raw_content.endswith("\n"):
        raw_content += "\n"

    raw_lines = raw_content.splitlines()

    # Load address
    load_addr = 0x0801
    current_addr = load_addr

    # First pass: build each line's binary content (without next-ptr, we fill later)
    line_binaries = []
    for raw in raw_lines:
        raw = raw.strip()
        if not raw:
            continue

        # Split line number from rest
        parts = raw.split(None, 1)
        if not parts:
            continue
        try:
            line_num = int(parts[0])
        except ValueError:
            print(f"Warning: skipping line with no line number: {raw}")
            continue

        body = parts[1] if len(parts) > 1 else ""
        tokens = tokenise_line(body)

        # Line structure: [next_ptr 2][line_num 2][tokens][0x00]
        # We don't know next_ptr yet, store placeholder
        line_bin = bytearray(4)  # placeholder for next_ptr + line_num
        line_bin[2] = line_num & 0xFF
        line_bin[3] = (line_num >> 8) & 0xFF
        line_bin += tokens
        line_bin += b'\x00'
        line_binaries.append(line_bin)

    # Second pass: fill in next-line pointers
    addr = current_addr
    for i, lb in enumerate(line_binaries):
        next_addr = addr + len(lb)
        if i < len(line_binaries) - 1:
            lb[0] = next_addr & 0xFF
            lb[1] = (next_addr >> 8) & 0xFF
        else:
            # Last line: next_ptr = addr + len + 2 (points past end marker)
            end_addr = next_addr + 2
            lb[0] = end_addr & 0xFF
            lb[1] = (end_addr >> 8) & 0xFF
        addr = next_addr

    # Assemble output
    output = bytearray()
    output += bytes([0x01, 0x08])  # Load address header $0801
    for lb in line_binaries:
        output += lb
    output += bytes([0x00, 0x00])  # End of program marker

    with open(output_path, "wb") as f:
        f.write(output)

    # Verify header
    with open(output_path, "rb") as f:
        check = f.read(2)

    if check == bytes([0x01, 0x08]):
        print(f"Converted {len(line_binaries)} line(s). Header $0801 verified.")
        print(f"Output written to: {output_path}")
    else:
        print(f"ERROR: Header not written correctly! Got: {check.hex()}")
        sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print("Usage: c64basconvert INPUTFILE.txt OUTPUTFILE.PRG")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
