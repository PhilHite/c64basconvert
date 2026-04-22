# c64basconvert v1.02 (macOS)

A macOS command line tool that converts a plain text C64 BASIC `.txt` file into a properly structured C64 BASIC binary `.PRG` file, ready to load directly into a C64 emulator such as VICE or Virtual64. The output filename is automatically converted to uppercase.

## Requirements

Python 3 is required. It is pre-installed on macOS. To check, run:

```bash
python3 --version
```

## Installation

1. Download both `c64basconvert` and `c64basconvert.py`.
2. Open Terminal and run:

```bash
chmod +x c64basconvert
sudo cp c64basconvert /usr/local/bin/
sudo cp c64basconvert.py /usr/local/bin/
```

The tool is now available from anywhere on the command line.

## Usage

```bash
c64basconvert inputfile.txt outputfile.prg
```

Example:

```bash
c64basconvert program.txt program.prg
```

The output file will be saved as `PROGRAM.PRG` (uppercase). The tool will report how many lines were converted and confirm the `$0801` header was written successfully.

## Loading the converted file in your C64 emulator

Once converted, load the file into your emulator using:

```
LOAD "PROGRAM.PRG",8,1
```

Then run it with:

```
RUN
```

## How it works

The C64 stores BASIC programs in a specific binary format in memory starting at address `$0801`. A plain text `.txt` file needs to be converted into this format before the C64 can run it. The tool performs the following steps:

**1. Tokenisation**
BASIC keywords such as `PRINT`, `GOTO`, `GOSUB`, `POKE`, `IF`, `FOR`, `NEXT` etc. are replaced with their single-byte C64 token values (e.g. `PRINT` becomes `$99`). This is exactly how the C64 stores BASIC programs internally. Keywords inside strings or `REM` comments are left as-is.

**2. Line structure**
Each line is stored in the C64 format:
- 2 bytes — pointer to the next line (little-endian)
- 2 bytes — line number (little-endian)
- n bytes — tokenised line content
- 1 byte — `$00` null terminator

**3. Program end marker**
Two null bytes `$00 $00` are appended after the last line to mark the end of the program.

**4. Load address header**
A 2-byte little-endian load address of `$0801` (`$01 $08`) is prepended to the file, telling the C64 where in memory to load the program.

**5. Trailing newline**
If the source `.txt` file does not end with a newline character, one is automatically appended before conversion. This ensures the last line is always processed correctly regardless of how the file was saved.

**6. ASCII to PETSCII conversion**
Lowercase letters (`a`–`z`) are converted to their PETSCII uppercase equivalents. Characters inside strings are converted to PETSCII as-is.

**7. Output filename**
The output filename is automatically converted to uppercase (e.g. `program.prg` becomes `PROGRAM.PRG`).

## Writing your .txt file

- Every line must start with a line number, e.g. `10 PRINT "HELLO WORLD"`
- Use uppercase or lowercase — keywords are matched case-insensitively
- Lines are separated by standard Unix (`LF`) or Windows (`CRLF`) line endings
- Use standard ASCII characters — avoid special symbols not present in PETSCII
