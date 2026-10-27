"""Check real document generation inside a frozen application subprocess."""
from pathlib import Path
import multiprocessing as mp
import multiprocessing.spawn
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sop_capture.models import Project, Step
from sop_capture.templates import TemplateLibrary
from sop_capture.word_export import create_example, export_docx
from sop_capture.document_export import export_pdf


def main():
    executable = str(Path(sys.argv[1]).resolve())
    mp.set_executable(executable)
    mp.spawn.get_command_line = lambda **kw: [executable, "--multiprocessing-fork", *[f"{key}={value}" for key, value in kw.items()]]
    preparation = mp.spawn.get_preparation_data
    def frozen_preparation(name):
        data = preparation(name)
        # Keep the frozen child's own runtime-hook paths (including pywin32),
        # rather than replacing them with the source parent's paths.
        data.pop("sys_path", None)
        data.pop("init_main_from_name", None)
        data.pop("init_main_from_path", None)
        return data
    mp.spawn.get_preparation_data = frozen_preparation
    with tempfile.TemporaryDirectory(prefix="sop-frozen-template-") as temporary:
        root = Path(temporary)
        example = create_example(root / "source.docx")
        library = TemplateLibrary(root / "library")
        profile = library.save("Bundle check", {}, source_docx=example)
        project = Project(title="Frozen template export", steps=[Step(title="Check output", description="Synthetic package verification.")], template=library.snapshot(profile["id"], root / "project"))
        for target, extension in ((export_docx, ".docx"), (export_pdf, ".pdf")):
            output = root / ("result"+extension)
            process = mp.get_context("spawn").Process(target=target, args=(project, root / "project", output))
            process.start()
            process.join(60)
            if process.is_alive():
                process.terminate()
                process.join()
                raise RuntimeError("Frozen document generation timed out")
            if process.exitcode != 0 or not output.exists(): raise RuntimeError("Frozen document export failed: "+extension)
            print("Packaged template export:", extension, "passed", output.stat().st_size, "bytes", flush=True)


if __name__ == "__main__": main()
