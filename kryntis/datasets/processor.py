"""
Dataset Processor — Cleans, filters, and packages code files into standardized JSONL files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Valid extensions mapping to language identifiers
EXT_LANG_MAP = {
    ".py": "python",
    ".java": "java",
    ".cs": "csharp",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c_header",
    ".hpp": "cpp_header",
    ".php": "php",
    ".rb": "ruby",
    ".pl": "perl",
    ".swift": "swift",
    ".kt": "kotlin",
    ".dart": "dart",
    ".r": "r",
    ".jl": "julia",
    ".scala": "scala",
    ".hs": "haskell",
    ".lua": "lua",
    ".f90": "fortran",
    ".f": "fortran",
    ".cbl": "cobol",
    ".cob": "cobol",
    ".erl": "erlang",
    ".ex": "elixir",
    ".exs": "elixir",
    ".clj": "clojure",
    ".fs": "fsharp",
    ".ml": "ocaml",
    ".zig": "zig",
    ".nim": "nim",
    ".v": "v",
    ".pas": "pascal",
    ".ada": "ada",
    ".adb": "ada",
    ".d": "d",
    ".groovy": "groovy",
    ".m": "matlab",
    ".sol": "solidity",
    ".vy": "vyper",
    ".sql": "sql",
    ".vhd": "vhdl",
    ".vhdl": "vhdl",
    ".wat": "webassembly",
    ".wasm": "webassembly",
    ".cls": "apex",
    ".trigger": "apex",
    ".abap": "abap",
    ".asm": "assembly",
    ".s": "assembly",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".sh": "bash",
    ".bash": "bash",
    ".bat": "cmd",
    ".cmd": "cmd",
    ".mobileconfig": "mdm",
    ".xml": "mdm",
}


class DatasetProcessor:
    """
    Processes raw text files, cloned GitHub repos, and downloaded JSONL files
    into clean, unified training JSONL format.
    """

    def __init__(self, raw_dir: str = "data/raw", processed_dir: str = "data/processed") -> None:
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def process_domain(self, domain: str) -> Path:
        """Process all raw files matching a specific domain into a dedicated JSONL corpus."""
        from kryntis.datasets.catalog import get_catalog_by_domain
        sources = get_catalog_by_domain(domain)
        target_ids = {ds.id for ds in sources}

        out_file = self.processed_dir / f"train_corpus_{domain}.jsonl"
        log.info("start_domain_dataset_processing", domain=domain, output=str(out_file))

        total_records = 0
        import gc

        with open(out_file, "w", encoding="utf-8") as out_f:
            for jsonl_file in self.raw_dir.glob("*.jsonl"):
                source_name = jsonl_file.stem
                if source_name not in target_ids:
                    continue
                log.info("processing_jsonl_file", path=jsonl_file.name, domain=domain)
                with open(jsonl_file, "r", encoding="utf-8", errors="ignore") as in_f:
                    for line in in_f:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            cleaned = self._clean_code(data.get("text", ""))
                            if cleaned:
                                record = {
                                    "domain": domain,
                                    "lang": data.get("languages", ["unknown"])[0],
                                    "text": cleaned,
                                }
                                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                                total_records += 1
                        except Exception:
                            continue
                gc.collect()

        log.info("domain_processing_completed", domain=domain, total_records=total_records, output=str(out_file))
        return out_file

    def process_all(self) -> Path:
        """Process all raw files across all domains into the unified training corpus."""
        out_file = self.processed_dir / "train_corpus.jsonl"
        log.info("start_dataset_processing", output=str(out_file))

        total_records = 0

        with open(out_file, "w", encoding="utf-8") as out_f:
            import gc
            # 1. Process HF jsonl files in raw_dir
            for jsonl_file in self.raw_dir.glob("*.jsonl"):
                log.info("processing_jsonl_file", path=jsonl_file.name)
                with open(jsonl_file, "r", encoding="utf-8", errors="ignore") as in_f:
                    for line in in_f:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            cleaned = self._clean_code(data.get("text", ""))
                            if cleaned:
                                record = {
                                    "lang": data.get("languages", ["unknown"])[0],
                                    "text": cleaned,
                                }
                                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                                total_records += 1
                        except Exception:
                            continue
                gc.collect()

            # 2. Process cloned GitHub code repositories
            github_dir = self.raw_dir / "github"
            if github_dir.exists():
                for ext, lang in EXT_LANG_MAP.items():
                    for code_file in github_dir.rglob(f"*{ext}"):
                        try:
                            content = code_file.read_text(encoding="utf-8", errors="ignore")
                            cleaned = self._clean_code(content)
                            if cleaned:
                                record = {"lang": lang, "text": cleaned}
                                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                                total_records += 1
                        except Exception:
                            continue
                    gc.collect()

        gc.collect()
        log.info("dataset_processing_completed", total_records=total_records, output=str(out_file))
        return out_file

    def _clean_code(self, code: str) -> str:
        """Strip invalid characters, excess blank lines, and empty files."""
        if not code or len(code.strip()) < 30:
            return ""
        
        # Remove trailing spaces from each line while keeping indentation
        lines = [line.rstrip() for line in code.splitlines()]
        
        # Max 3 consecutive empty lines
        result_lines = []
        empty_count = 0
        for line in lines:
            if not line:
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)

        cleaned = "\n".join(result_lines).strip()
        return cleaned if len(cleaned) >= 30 else ""
