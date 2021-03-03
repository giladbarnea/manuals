#!/usr/bin/env python3.8
from typing import Optional, List

import re
import semver
import sys
from pathlib import Path
import subprocess
import shlex

DRY_RUN_RE = re.compile('^[-]+dry[-_]?run$')


def confirm(prompt='continue?') -> bool:
    answer = input(f'{prompt} y/n/q\t').lower()
    if answer == 'q':
        import sys
        sys.exit()
    return answer == 'y' or answer == 'yes'


_print = lambda *args, **kwargs: print('\n', *args, **kwargs, end='\n\n')


def is_dry_run():
    # -n, [-]+dry[-_]?run
    for arg in sys.argv[1:]:
        if arg == '-n' or DRY_RUN_RE.fullmatch(arg):
            sys.argv.remove(arg)
            return True
    return False


def main():
    if subprocess.check_output(shlex.split("git status -s")):
        _print('some uncommitted changes:')
        subprocess.run(shlex.split('git status'))
        if not confirm('publish?'):
            sys.exit()
    with open('./setup.py') as f:
        data = f.read()
    VERSION_RE = re.compile(r"\s*version='(?P<ver>\d+(?:\.\d+)+)',")
    version = VERSION_RE.search(data).groupdict()['ver']
    parsed = semver.VersionInfo.parse(version)
    bumped = parsed.bump_patch()
    if bumped.patch == 10:
        bumped = parsed.bump_minor()
    if confirm(f'current version is {version}, bump to {bumped}?'):
        bump_version(data, version, bumped)
    
    if Path('./dist').is_dir() or Path('./build').is_dir():
        cmd = 'rm -rf dist build'
        if confirm(f"run '{cmd}'?"):
            if run(shlex.split(cmd)) is None:
                sys.exit(1)
    else:
        _print("dist and/or build dirs don't exist")
    if not Path('./env').is_dir():
        _print('./env is not a directory')
        sys.exit(1)
    if not any(pkg.startswith('twine') for pkg in run(shlex.split('pip freeze'))):
        _print('twine is not installed')
        sys.exit(1)
    
    if confirm(f"run './env/bin/python setup.py sdist bdist_wheel'?"):
        if run(shlex.split('./env/bin/python setup.py sdist bdist_wheel')) is None:
            sys.exit(1)
    if confirm(f"run './env/bin/python -m twine upload dist/*'?"):
        import os # asks for password
        os.system('./env/bin/python -m twine upload dist/*')
        
    


def run(cmd) -> Optional[List[str]]:
    if dry_run:
        _print('dry_run, not actually running anything')
        return
    try:
        comp_proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        _print(f'FAILED cmd: {cmd}', repr(e))
        return None
    else:
        if comp_proc.returncode != 0:
            _print(f"'{cmd}' exited with return code: {comp_proc.returncode}. stderr: {repr(comp_proc.stderr)}")
        else:
            _print(f"success running '{cmd}'")
        try:
            return comp_proc.stdout.decode().splitlines()
        except AttributeError as e:
            return []


def bump_version(data, version, bumped):
    replaced = data.replace(version, str(bumped), 1)
    before, after = map(str.strip, set(data.splitlines()).symmetric_difference(set(replaced.splitlines())))
    if dry_run:
        _print('dry run: would have made the following changes to setup.py;', 'before:', before, 'after:', after, sep='\n')
        return
    with open('./setup.py', 'w') as f:
        f.write(replaced)
    _print(f'replaced "{before}" with "{after}" successfully')


if __name__ == '__main__':
    dry_run = is_dry_run()
    main()
