#!/bin/bash
#SBATCH --time=1:00:00
#SBATCH -p bioe
#SBATCH --gpus=1
#SBATCH -c 8
#SBATCH --output=dyna1-esm3.out
#SBATCH --job-name=dyna1-esm3

# Input only the sequence
python dyna1.py \
	--name flavodoxin_seq \
	--sequence MAEIGIFVGTMYGNSLLVAEEAEAILTAQGHKATVFEDPELSDWLPYQDKYVLVVTSTTGQGDLPDSIVPLFQGIKDSLGFQPNLRYGVIALGDSSYVNFCNGGKQFDALLQEQSAQRVGEMLLIDASENPEPETESNPWVEQWGTLLS \
	--save_dir /Dyna-1/output

# Input only the pdb structure
python dyna1.py \
	--name flavodoxin_struct \
	--structure /Dyna-1/input/flavodoxin.pdb \
	--save_dir /Dyna-1/output

# Input uses the sequence on the pdb and the pdb structure
python dyna1.py \
	--name flavodoxin_pdb \
	--structure /Dyna-1/input/flavodoxin.pdb \
	--use_pdb_seq \
	--save_dir /Dyna-1/output

# Input uses the sequence on the pdb and the pdb structure
# Output the probabilities to the structure
python dyna1.py \
	--name flavodoxin_seqstruct \
	--structure /Dyna-1/input/flavodoxin.pdb \
	--use_pdb_seq \
	--write_pred_to_struct \
	--save_dir /Dyna-1/output

# Input uses a custom sequence and pdb structure
python dyna1.py \
	--name flavodoxin \
	--sequence MAEIGIFVGTMYGNSLLVAEEAEAILTAQGHKATVFEDPELSDWLPYQDKYVLVVTSTTGQGDLPDSIVPLFQGIKDSLGFQPNLRYGVIALGDSSYVNFCNGGKQFDALLQEQSAQRVGEMLLIDASENPEPETESNPWVEQWGTLLS \
	--structure /Dyna-1/input/flavodoxin.pdb \
	--save_dir /Dyna-1/output
