"""Internal parser process. Applies memory limits before importing the PDF library."""

import ctypes
import json
import os
import sys

MEMORY_BYTES = 512 * 1024 * 1024


def memory_limit():
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
        return None
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [
            ("process_time", ctypes.c_longlong),
            ("job_time", ctypes.c_longlong),
            ("flags", wintypes.DWORD),
            ("min_working", ctypes.c_size_t),
            ("max_working", ctypes.c_size_t),
            ("process_count", wintypes.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority", wintypes.DWORD),
            ("scheduling", wintypes.DWORD),
        ]

    class Limits(ctypes.Structure):
        _fields_ = [
            ("basic", Basic),
            ("io", ctypes.c_ulonglong * 6),
            ("process_memory", ctypes.c_size_t),
            ("job_memory", ctypes.c_size_t),
            ("peak_process", ctypes.c_size_t),
            ("peak_job", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    job = kernel.CreateJobObjectW(None, None)
    limits = Limits()
    limits.basic.flags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    limits.process_memory = MEMORY_BYTES
    if not job or not kernel.SetInformationJobObject(
        job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
    ):
        raise OSError("Could not establish parser memory limit")
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise OSError("Could not attach parser memory limit")
    return job  # Hold the handle until this process exits.


def extract(path):
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    try:
        document = pymupdf.open(path)
    except Exception:
        return {"error": "corrupt_pdf", "message": "The PDF cannot be opened."}
    with document:
        if not document.is_pdf:
            return {"error": "unsupported_file", "message": "Only PDF documents are supported."}
        if document.needs_pass:
            return {"error": "encrypted_pdf", "message": "Upload an unencrypted PDF."}
        if not 1 <= len(document) <= 50:
            return {"error": "page_limit", "message": "PDF must contain 1 to 50 pages."}
        spans, warnings, characters = [], [], 0
        for index, page in enumerate(document):
            count = 0
            for block in page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)["blocks"]:
                for line in block.get("lines", []):
                    for item in line["spans"]:
                        text = item["text"].strip()
                        if not text:
                            continue
                        characters += len(text)
                        if characters > 1_000_000 or len(spans) >= 20000 or len(text) > 20000:
                            return {
                                "error": "text_limit",
                                "message": "Extracted text exceeds limits.",
                            }
                        spans.append(
                            {
                                "id": f"p{index + 1}-s{count}",
                                "page": index + 1,
                                "bbox": item["bbox"],
                                "text": text,
                            }
                        )
                        count += 1
            if count == 0:
                warnings.append(f"Page {index + 1}: no text; OCR is not supported.")
        if not spans:
            return {
                "error": "scanned_pdf",
                "message": "No text found. Scans require unsupported OCR.",
            }
        warnings.append(
            "Equations, tables, and reading order require review against the original PDF."
        )
        return {
            "pages": len(document),
            "spans": spans,
            "warnings": warnings,
            "parser_version": f"pymupdf-{pymupdf.VersionBind}/spans-v1",
        }


if __name__ == "__main__":
    try:
        job_handle = memory_limit()
    except OSError:
        result = {
            "error": "memory_limit_unavailable",
            "message": "Parser memory limits could not be applied.",
        }
    else:
        try:
            result = extract(sys.argv[1])
        except MemoryError:
            result = {"error": "parser_memory_limit", "message": "PDF exceeded parser memory."}
        except Exception:
            result = {"error": "parser_failure", "message": "PDF parsing failed."}
    sys.stdout.buffer.write(json.dumps(result, allow_nan=False).encode("utf-8"))
