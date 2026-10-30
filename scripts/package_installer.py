"""Compile a per-user Windows installer from the verified portable release."""
from pathlib import Path
import argparse
import hashlib
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sop_capture.updates import stage_archive


def build_installer(archive: Path, compiler: Path, output: Path) -> tuple[Path, Path]:
    archive = Path(archive).resolve()
    match = re.fullmatch(r'SOPCaptureStudio-(\d+\.\d+\.\d+)-Windows-x64\.zip', archive.name)
    if not match:
        raise ValueError('Expected a versioned Windows x64 release ZIP.')
    version = match[1]
    checksum = archive.with_suffix('.zip.sha256').read_text(encoding='utf-8').strip()
    digest = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?' + re.escape(archive.name), checksum)
    if not digest:
        raise ValueError('Release checksum is invalid or names another package.')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    setup = output / f'SOPCaptureStudio-{version}-Windows-x64-Setup.exe'
    setup_checksum = setup.with_suffix('.exe.sha256')
    # Clear only these generated outputs: a failed compile must never look published.
    setup.unlink(missing_ok=True)
    setup_checksum.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='sop-installer-') as temporary:
        payload = stage_archive(archive, digest[1], Path(temporary) / 'staged', version)
        subprocess.run([str(Path(compiler).resolve()), '/Qp', f'/DAppVersion={version}',
                        f'/DPayloadDir={payload}', f'/DOutputDir={output}',
                        str(ROOT / 'packaging/windows/SOPCaptureStudio.iss')], check=True)
    if not setup.is_file():
        raise RuntimeError('Compiler did not produce the expected installer.')
    with setup.open('rb') as stream:
        result = hashlib.file_digest(stream, 'sha256').hexdigest()
    setup_checksum.write_text(result + '  ' + setup.name + '\n', encoding='utf-8')
    return setup, setup_checksum


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/releases')
    args = parser.parse_args()
    for path in build_installer(args.archive, args.compiler, args.output):
        print(path)
