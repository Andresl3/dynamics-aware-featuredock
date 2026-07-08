#!/bin/bash
#SBATCH --time=1:00:00
#SBATCH -p bioe
#SBATCH --gpus=1
#SBATCH -c 8
#SBATCH --output=naive.out
#SBATCH --job-name=naive

python naive_classifier.py relaxdb --save_dir /path/to/save/dir/relaxdb
python naive_classifier.py relaxdb --save_dir /path/to/save/dir/relaxdb --rex_only
python naive_classifier.py relaxdb --save_dir /path/to/save/dir/relaxdb --missing_only

python naive_classifier.py cpmg --save_dir /path/to/save/dir/cpmg
python naive_classifier.py cpmg --save_dir /path/to/save/dir/cpmg --rex_only
python naive_classifier.py cpmg --save_dir /path/to/save/dir/cpmg --missing_only
python naive_classifier.py cpmg --save_dir /path/to/save/dir/cpmg --unsuppressed
python naive_classifier.py cpmg --save_dir /path/to/save/dir/cpmg --rex_only --unsuppressed

