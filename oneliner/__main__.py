import argparse

import oneliner
import oneliner.version
import oneliner.config

parser = argparse.ArgumentParser(
    description="Convert python scripts into oneliner expression."
)

parser.add_argument(
    "-C",
    action="append",
    type=str,
    help="Set configs of oneliner convertion"
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

# todo: remove in 1.3.0
parser.add_argument(
    "--unparser",
    type=str,
    default="ast.unparse",
    choices=["ast.unparse", "oneliner"],
)

args = parser.parse_args()

cfg = oneliner.config.Configs()

for input_config in args.C:
    assert isinstance(input_config, str)
    
    # todo: better error message
    config_name, config_value = input_config.split("=")

    setattr(cfg,config_name,config_value)

if args.unparser is not None:
    import warnings
    warnings.warn(
        f"'--unparser {args.unparser}' is deprecated,"
        f" use '-Cunparser={args.unparser}' instead",
        DeprecationWarning
    )
    cfg.unparser = args.unparser

with open(args.input_filename, "r", encoding="utf8") as infile:
    script = infile.read()

converted = oneliner.convert_code_string(script, configs=cfg)

if args.output is not None:
    with open(args.output, "w", encoding="utf8") as outfile:
        outfile.write(converted)
else:
    print(converted)
