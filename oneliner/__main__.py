import argparse

import oneliner
import oneliner.version

parser = argparse.ArgumentParser(
    description="Convert python scripts into oneliner expression."
)

parser.add_argument(
    "input_filename",
    type=str,
    help="The filename of the python script to be converted",
)

ver = oneliner.version.oneliner_version
dev = "-dev" if oneliner.version.dev else ""
parser.add_argument(
    "-v",
    "--version",
    action="version",
    version=f"Oneliner-Py-{ver[0]}.{ver[1]}.{ver[2]}{dev}",
)

parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="The output filename. If this argument is not specified, "
    "Oneliner-Py will print the result to the screen.",
)

parser.add_argument(
    "--unparser",
    type=str,
    default="ast.unparse",
    choices=["ast.unparse", "oneliner"],
)

args = parser.parse_args()

with open(args.input_filename, "r", encoding="utf8") as infile:
    script = infile.read()

if args.unparser == "ast.unparse":
    converted = oneliner.convert_code_string(script, use_new_unparser=False)
else:
    converted = oneliner.convert_code_string(script, use_new_unparser=True)

if args.output is not None:
    with open(args.output, "w", encoding="utf8") as outfile:
        outfile.write(converted)
else:
    print(converted)
