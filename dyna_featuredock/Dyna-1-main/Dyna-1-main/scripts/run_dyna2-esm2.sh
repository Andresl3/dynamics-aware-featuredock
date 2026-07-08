#!/bin/bash
#SBATCH --time=1:00:00
#SBATCH -p bioe
#SBATCH --gpus=1
#SBATCH -c 8
#SBATCH --output=dyna1-esm2.out
#SBATCH --job-name=dyna1-esm2

# Input is a sequence
python dyna1-esm2.py \
	--name flavodoxin_seq \
	--sequence MAEIGIFVGTMYGNSLLVAEEAEAILTAQGHKATVFEDPELSDWLPYQDKYVLVVTSTTGQGDLPDSIVPLFQGIKDSLGFQPNLRYGVIALGDSSYVNFCNGGKQFDALLQEQSAQRVGEMLLIDASENPEPETESNPWVEQWGTLLS \
	--save_dir /Dyna-1/output