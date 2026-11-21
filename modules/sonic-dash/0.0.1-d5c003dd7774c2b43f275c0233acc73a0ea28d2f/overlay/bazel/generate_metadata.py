"""Run the SAI metadata generators directly on their declared files."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def run_doxygen(doxygen, inputs, directory, environment):
    version = subprocess.check_output(
        [doxygen, "-v"], env=environment, text=True
    ).strip()
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Unrecognized Doxygen version: {version}")
    template_name = (
        "Doxyfile" if tuple(map(int, match.groups())) >= (1, 8, 16)
        else "Doxyfile.compat"
    )
    meta = inputs["."]
    headers = [
        str(path)
        for group in ("../inc/", "../experimental/", "../custom/")
        for name, path in sorted(inputs[group].items())
        if name.endswith(".h")
    ] + [
        str(meta[name])
        for name in (
            "saimetadatatypes.h",
            "saimetadatautils.h",
            "saimetadatalogger.h",
            "saiserialize.h",
        )
    ]
    template = meta[template_name].read_text()
    # Doxygen's explicit inputs hold both the original and generated
    # headers. Preserve its definition of all metadata-producing options.
    config = re.sub(r"^INPUT\s*\+?=.*$", "", template, flags=re.MULTILINE)
    config += '\nINPUT = ' + " ".join(json.dumps(header) for header in headers)
    config += "\nGENERATE_HTML = NO\n"
    configuration = directory / template_name
    configuration.write_text(config)
    result = subprocess.run(
        [doxygen, str(configuration)],
        cwd=directory,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode or "warning" in result.stdout.lower():
        raise RuntimeError(f"Doxygen failed or emitted a warning:\n{result.stdout}")


def main():
    parser = argparse.ArgumentParser()
    for name in ("manifest", "parser", "doxygen", "perl", "aspell"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--output", action="append", required=True, type=Path)
    args = parser.parse_args()

    inputs = {
        group: {name: Path(path).absolute() for name, path in files.items()}
        for group, files in json.loads(args.manifest.read_text()).items()
    }
    with tempfile.TemporaryDirectory(prefix="dash-sai-metadata-") as temporary:
        directory = Path(temporary).absolute()
        environment = {
            "HOME": str(directory),
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "",
            "SAI_ASPELL": str(args.aspell.absolute()),
            "TMPDIR": str(directory),
        }
        # The pinned SAI archive has no Git history. Its Make generators
        # produce empty headers for this checkout mode.
        for name in ("saiattrversion.h", "saimetadatasize.h"):
            path = directory / name
            path.touch()
            inputs["."][name] = path

        run_doxygen(args.doxygen.absolute(), inputs, directory, environment)
        manifest = directory / "inputs.json"
        manifest.write_text(json.dumps(inputs, default=os.fspath))
        environment["SAI_METADATA_INPUTS"] = str(manifest)
        parser_path = args.parser.absolute()
        subprocess.run(
            [args.perl.absolute(), "-I" + str(parser_path.parent), parser_path],
            cwd=directory,
            env=environment,
            check=True,
        )
        for output in args.output:
            output.write_bytes((directory / output.name).read_bytes())


if __name__ == "__main__":
    main()
