#!/usr/bin/env bash
# Baixa os READMEs das aulas do grupo de MLOps para data/ (o "corpus" do RAG).
set -euo pipefail

REPO=https://github.com/CEIA-UFG-GROUPS/ceia-ufg-mlops.git
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT   # limpa a pasta temporaria ao sair, mesmo com erro

git clone --quiet --depth 1 "$REPO" "$TMP"
mkdir -p data

# Cada aula tem presentation/.../aulaNN/monitor/README.md -> data/aulaNN.md
find "$TMP/presentation" -path '*/monitor/README.md' | while read -r f; do
  aula=$(basename "$(dirname "$(dirname "$f")")")
  cp "$f" "data/$aula.md"
done

echo "Corpus pronto: $(ls data/*.md | wc -l) aulas em data/"
