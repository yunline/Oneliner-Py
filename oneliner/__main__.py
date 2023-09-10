import argparse

import oneliner

parser = argparse.ArgumentParser(
    description="Convert python scripts into oneliner expression."
)

parser.add_argument(
    "input_filename",
    type=str,
    help="The filename of the python script to be converted",
)

parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="The output filename. If this argument is not specified, "
    "Oneliner-Py will print the result to the screen.",
)

args = parser.parse_args()

with open(args.input_filename, "r", encoding="utf8") as infile:
    script = infile.read()

converted = oneliner.convert_code_string(script)

if args.output is not None:
    with open(args.output, "w", encoding="utf8") as outfile:
        outfile.write(converted)
else:
    print(converted)
