#!/bin/bash
#SBATCH --time=1:00:00
#SBATCH -p bioe
#SBATCH --gpus=1
#SBATCH -c 8
#SBATCH --output=eval_af2.out
#SBATCH --job-name=eval_af2

python eval.py relaxdb --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/relaxdb
python eval.py relaxdb --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/relaxdb --rex_only
python eval.py relaxdb --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/relaxdb --missing_only

python eval.py cpmg --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/cpmg
python eval.py cpmg --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/cpmg --rex_only
python eval.py cpmg --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/cpmg --missing_only
python eval.py cpmg --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/cpmg --unsuppressed
python eval.py cpmg --method af2 --weights_dir /path/to/weights --save_dir /path/to/save/dir/cpmg --rex_only --unsuppressed

