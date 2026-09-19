"""
Dataset Downloader — Streams Hugging Face datasets and clones GitHub repos locally.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from kryntis.datasets.catalog import DATASET_CATALOG, DatasetSource, get_catalog_by_phase
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class DatasetDownloader:
    """
    Downloads coding datasets from Hugging Face (streaming mode to respect 8GB RAM)
    and clones GitHub sample repositories into local directories.
    """

    def __init__(self, raw_dir: str = "data/raw") -> None:
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.github_dir = self.raw_dir / "github"
        self.github_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir = self.raw_dir / "manifests"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def write_manifest(self, source: DatasetSource, output_paths: list[Path]) -> Path:
        """Write one provenance JSONL record for verified local dataset output.

        Raises:
            FileNotFoundError: If any claimed output artifact does not exist.
        """
        if missing := [path for path in output_paths if not path.exists()]:
            raise FileNotFoundError(f"Dataset outputs do not exist: {missing}")
        record = {
            "source_id": source.id, "name": source.name, "domain": source.domain,
            "source_type": source.source_type, "location": source.location,
            "languages": source.languages, "phase": source.phase, "license": source.license,
            "text_key": source.text_key, "generated_at": datetime.now(timezone.utc).isoformat(),
            "output_paths": [str(path) for path in output_paths],
        }
        manifest = self.manifest_dir / f"{source.id}.jsonl"
        manifest.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
        return manifest

    def download_domain(self, domain: str) -> None:
        from kryntis.datasets.catalog import get_catalog_by_domain
        sources = get_catalog_by_domain(domain)
        if not sources:
            log.warning("no_sources_found_for_domain", domain=domain)
            return

        log.info("start_domain_dataset_download", domain=domain, total_sources=len(sources))

        import gc
        for source in sources:
            if source.source_type == "synthetic":
                output = self._generate_synthetic(source)
            elif source.source_type == "huggingface":
                output = self._download_hf(source)
            elif source.source_type == "github":
                output = self._clone_github(source)
            else:
                output = None
            if output:
                self.write_manifest(source, [output])
            gc.collect()

        log.info("domain_dataset_download_completed", domain=domain)

    def _generate_synthetic(self, source: DatasetSource) -> Path | None:
        from kryntis.datasets.synthetic_generator import SyntheticDatasetGenerator
        gen = SyntheticDatasetGenerator(raw_dir=str(self.raw_dir))
        if source.id == "synthetic-english":
            gen.generate_english()
        elif source.id == "synthetic-regional":
            gen.generate_regional()
        elif source.id == "synthetic-emotion":
            gen.generate_emotion()
        elif source.id == "synthetic-sysadmin":
            gen.generate_sysadmin()
        elif source.id == "synthetic-extended-tech":
            gen.generate_extended_tech()
        elif source.id == "synthetic-security":
            gen.generate_security()
        elif source.id == "synthetic-crm":
            gen.generate_crm()
        else:
            gen.generate_all()
        output = self.raw_dir / f"{source.id}.jsonl"
        return output if output.exists() else None

    def download_all(self, phase: int = 1) -> None:
        sources = get_catalog_by_phase(phase)
        log.info("start_dataset_download", total_sources=len(sources), phase=phase)

        import gc
        for source in sources:
            if source.source_type == "synthetic":
                output = self._generate_synthetic(source)
            elif source.source_type == "huggingface":
                output = self._download_hf(source)
            elif source.source_type == "github":
                output = self._clone_github(source)
            else:
                output = None
            if output:
                self.write_manifest(source, [output])
            gc.collect()

        log.info("dataset_download_completed", phase=phase)

    def _download_hf(self, source: DatasetSource) -> Path | None:
        log.info("downloading_hf_dataset", id=source.id, location=source.location, config=source.config_name)
        try:
            from datasets import load_dataset
            kwargs = {"split": source.split, "streaming": source.stream}
            if source.config_name:
                kwargs["name"] = source.config_name

            ds = load_dataset(source.location, **kwargs)
            out_file = self.raw_dir / f"{source.id}.jsonl"

            import json
            count = 0
            max_samples = 50000

            with open(out_file, "w", encoding="utf-8") as f:
                for item in ds:
                    text_content = item.get(source.text_key, "")
                    if isinstance(text_content, list):
                        text_content = " ".join(str(x) for x in text_content)

                    if text_content and len(str(text_content).strip()) > 20:
                        entry = {
                            "source_id": source.id,
                            "languages": source.languages,
                            "text": str(text_content),
                        }
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        count += 1
                        if count >= max_samples:
                            break

            log.info("hf_dataset_saved", id=source.id, samples=count, path=str(out_file))
            return out_file if out_file.exists() else None
        except Exception as e:
            log.error("hf_download_failed", id=source.id, error=str(e))
            return None

    def _clone_github(self, source: DatasetSource) -> Path | None:
        log.info("cloning_github_repo", id=source.id, url=source.location)
        try:
            import git

            repo_name = source.id
            target_dir = self.github_dir / repo_name
            if target_dir.exists():
                log.info("github_repo_exists_pulling", target=str(target_dir))
                try:
                    repo = git.Repo(target_dir)
                    repo.remotes.origin.pull()
                except Exception as pull_err:
                    log.warning("github_pull_failed_keeping_existing", target=str(target_dir), error=str(pull_err))
            else:
                git.Repo.clone_from(source.location, target_dir)
                log.info("github_repo_cloned", target=str(target_dir))
            return target_dir if target_dir.exists() else None
        except Exception as e:
            log.error("github_clone_failed", id=source.id, error=str(e))
            return None
