#!/usr/bin/env python3
"""Generate the relative applicant-origin representation figure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_manifest(manifest_path: Path, scatter_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("module") != "src.analysis_08_origin_composition" or manifest.get("status") != "passed":
        raise ValueError(f"{manifest_path}: Section 8 analysis did not pass")
    relative = str(scatter_path.relative_to(ROOT))
    matches = [item for item in manifest.get("outputs", []) if item.get("path") == relative]
    if len(matches) != 1 or matches[0].get("sha256") != sha256(scatter_path):
        raise ValueError(f"{manifest_path}: share-scatter input hash mismatch")


def transformed_rows(rows: list[dict[str, str]]) -> list[dict[str, float | str]]:
    required = {"country", "au_decision_share", "nz_decision_share"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("invalid share-scatter contract")
    transformed: list[dict[str, float | str]] = []
    for row in rows:
        au_share = float(row["au_decision_share"])
        nz_share = float(row["nz_decision_share"])
        if au_share <= 0 or nz_share <= 0:
            raise ValueError(f"{row['country']}: relative-share figure requires positive matched shares")
        transformed.append(
            {
                "country": row["country"],
                "geometric_mean_share": math.sqrt(au_share * nz_share),
                "log2_share_ratio": math.log2(au_share / nz_share),
            }
        )
    return transformed


def select_labels(rows: list[dict[str, float | str]]) -> list[str]:
    major = sorted(
        rows,
        key=lambda row: (-float(row["geometric_mean_share"]), str(row["country"])),
    )[:3]
    substantial = [row for row in rows if float(row["geometric_mean_share"]) >= 0.001]
    if len(substantial) < 4:
        raise ValueError("insufficient substantial-share origins for deterministic labels")
    australian = sorted(
        substantial,
        key=lambda row: (-float(row["log2_share_ratio"]), str(row["country"])),
    )[:1]
    new_zealand = sorted(
        substantial,
        key=lambda row: (float(row["log2_share_ratio"]), str(row["country"])),
    )[:1]
    left_side = [row for row in rows if float(row["geometric_mean_share"]) < 0.0001]
    if len(left_side) < 2:
        raise ValueError("insufficient low-share origins for deterministic boundary labels")
    left_upper = max(
        left_side,
        key=lambda row: (float(row["log2_share_ratio"]), str(row["country"])),
    )
    left_lower = min(
        left_side,
        key=lambda row: (float(row["log2_share_ratio"]), str(row["country"])),
    )
    far_left = [row for row in rows if float(row["geometric_mean_share"]) < 0.00001]
    if not far_left:
        raise ValueError("insufficient far-left origins for lower-boundary label")
    far_left_lower = min(
        far_left,
        key=lambda row: (float(row["log2_share_ratio"]), str(row["country"])),
    )
    intermediate_left = [
        row
        for row in rows
        if 0.0001 <= float(row["geometric_mean_share"]) < 0.001
    ]
    if not intermediate_left:
        raise ValueError("insufficient intermediate low-share origins for boundary label")
    intermediate_upper = max(
        intermediate_left,
        key=lambda row: (float(row["log2_share_ratio"]), str(row["country"])),
    )
    leftmost = min(
        rows,
        key=lambda row: (float(row["geometric_mean_share"]), str(row["country"])),
    )
    most_negative = min(
        rows,
        key=lambda row: (float(row["log2_share_ratio"]), str(row["country"])),
    )
    return list(
        dict.fromkeys(
            str(row["country"])
            for row in (
                *major,
                *australian,
                *new_zealand,
                most_negative,
                left_upper,
                left_lower,
                far_left_lower,
                intermediate_upper,
                leftmost,
            )
        )
    )


def latex_escape(value: str) -> str:
    replacements = {"&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#"}
    return "".join(replacements.get(character, character) for character in value)


def generate(
    *,
    scatter_path: Path = ROOT / "data/results/composition/share_scatter_points.csv",
    manifest_path: Path = ROOT / "data/results/manifests/08_origin_composition.json",
    output_tex: Path = ROOT / "article/figures/origin_share_relative_representation.tex",
    output_pdf: Path = ROOT / "article/figures/origin_share_relative_representation.pdf",
    output_png: Path = ROOT / "article/figures/origin_share_relative_representation.png",
    compile_image: bool = True,
) -> dict[str, Path | list[str]]:
    verify_manifest(manifest_path, scatter_path)
    rows = transformed_rows(read_rows(scatter_path))
    labels = select_labels(rows)
    indexed = {str(row["country"]): row for row in rows}
    coordinates = " ".join(
        f"({float(row['geometric_mean_share']):.12g},{float(row['log2_share_ratio']):.12g})"
        for row in rows
    )
    placement = {
        "China": "south east",
        "India": "north east",
        "Nepal": "south west",
        "Bhutan": "south east",
        "Germany": "south west",
        "Tonga": "north west",
        "North Macedonia": "south east",
        "Kiribati": "north west",
        "Benin": "south east",
        "Uzbekistan": "south east",
        "Democratic People's Republic of Korea": "south west",
    }
    display_name = {
        "Democratic People's Republic of Korea": "DPR Korea",
    }
    nodes = []
    for country in labels:
        row = indexed[country]
        nodes.append(
            rf"\node[font=\scriptsize,anchor={placement.get(country, 'south west')},fill=white,fill opacity=0.82,text opacity=1,inner sep=1.2pt] at (axis cs:{float(row['geometric_mean_share']):.12g},{float(row['log2_share_ratio']):.12g}) {{{latex_escape(display_name.get(country, country))}}};"
        )
    source = rf"""% Generated by scripts/generate_relative_origin_share.py. Do not edit.
% The x-axis is the geometric mean of AU and NZ decision shares. The y-axis is
% log2(AU share / NZ share). Labels show the three largest average shares, the
% largest positive and negative ratios among origins with geometric-mean share
% at least 0.1%, the most negative ratio overall, and the upper and lower
% ratio boundaries among origins with geometric-mean share below 0.01%, the
% lower boundary below 0.001%, the upper boundary from 0.01% to 0.1%, and the
% origin with the smallest geometric-mean share.
\begin{{tikzpicture}}
\begin{{semilogxaxis}}[
  width=0.92\textwidth,height=7.4cm,xmin=0.000001,xmax=0.5,ymin=-8,ymax=5,
  xlabel={{Geometric mean decision share across destinations}},
  ylabel={{Relative representation, $\log_2(\mathrm{{AU\ share}}/\mathrm{{NZ\ share}})$}},
  grid=major,tick label style={{font=\small}},label style={{font=\small}},
]
\addplot[gray!70,dashed,thick,domain=0.000001:0.5,forget plot] {{0}};
\addplot[only marks,mark=*,mark size=1.5pt,blue!70!black,opacity=0.72] coordinates {{{coordinates}}};
\addplot[only marks,mark=*,mark size=2.2pt,red!75!black] coordinates {{{' '.join(f"({float(indexed[country]['geometric_mean_share']):.12g},{float(indexed[country]['log2_share_ratio']):.12g})" for country in labels)}}};
\node[font=\small,align=left,anchor=north west] at (rel axis cs:0.02,0.98) {{Relatively larger share\\in Australia}};
\node[font=\small,align=right,anchor=south east] at (rel axis cs:0.98,0.02) {{Relatively larger share\\in New Zealand}};
{chr(10).join(nodes)}
\end{{semilogxaxis}}
\end{{tikzpicture}}
"""
    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(source, encoding="utf-8")
    result: dict[str, Path | list[str]] = {"tex": output_tex, "labels": labels}
    if compile_image:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            wrapper = temporary_path / "figure.tex"
            wrapper.write_text(
                "\\documentclass[tikz,border=5pt]{standalone}\n"
                "\\usepackage[T1]{fontenc}\n"
                "\\usepackage{pgfplots}\n"
                "\\pgfplotsset{compat=1.18}\n"
                "\\begin{document}\n"
                f"\\input{{{output_tex.resolve().as_posix()}}}\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "figure.tex"],
                cwd=temporary_path,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            shutil.copy2(temporary_path / "figure.pdf", output_pdf)
            subprocess.run(
                ["pdftoppm", "-singlefile", "-png", "-r", "220", str(output_pdf), str(temporary_path / "figure")],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            shutil.copy2(temporary_path / "figure.png", output_png)
        result.update({"pdf": output_pdf, "png": output_png})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-compile", action="store_true", help="write only the PGFPlots source")
    args = parser.parse_args()
    outputs = generate(compile_image=not args.no_compile)
    print("Relative-origin-share figure written:")
    for key in ("tex", "pdf", "png"):
        if key in outputs:
            print(f"- {Path(outputs[key]).relative_to(ROOT)}")
    print(f"Labels: {', '.join(outputs['labels'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
