# CDK2 pose-RMSD head-to-head (worksheet's primary metric) for BOTH regimes:
#   Run 1 = from-scratch : baseline80      vs dyna1_81
#   Run 2 = warm-start   : baseline80_warm vs dyna1_81_warm
# Native ligands and voxel grids already exist from preprocessing:
#   voxels -> dyna_featuredock_out/voxels/{pid}.voxels.pkl
#   native -> dyna_featuredock_out/het/{pid}_ligand.sdf
# Paste directly on a compute node (all absolute paths). Needs rdkit + scipy in
# the env. Runs on CPU fine (posing is scipy); --use_gpu only speeds the model
# forward pass. nsamples=50 rigid-body restarts per structure.

# 0) activate env (adjust name if yours differs)
source activate dynafeat 2>/dev/null || conda activate dynafeat
cd /scratch/mani.na/dynamics-aware-featuredock/featuredock

# --- sanity: confirm the data dirs are populated for the 18 CDK2 pids ---
echo "voxels present:"; ls /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/voxels/ | grep -cE '\.voxels\.pkl$'
echo "native ligands present:"; ls /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/het/ | grep -cE '_ligand\.sdf$'

# ===== RUN 1: from-scratch (5-block) baseline vs +Dyna-1 =====
python -u /scratch/mani.na/dynamics-aware-featuredock/featuredock/src/models/evaluate_cdk2_rmsd.py --baseline-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/baseline80/baseline80_final_params.torch --baseline-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_80 --dyna1-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/dyna1_81/dyna1_81_final_params.torch --dyna1-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_81 --voxeldir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/voxels --ligdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/het --test-pids /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/test_pids.txt --outdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/cdk2_rmsd_scratch --nsamples 50 --seed 0 --use_gpu

# ===== RUN 2: warm-start (20-block) baseline vs +Dyna-1 =====
python -u /scratch/mani.na/dynamics-aware-featuredock/featuredock/src/models/evaluate_cdk2_rmsd.py --baseline-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/baseline80_warm/baseline80_warm_final_params.torch --baseline-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_80 --dyna1-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/dyna1_81_warm/dyna1_81_warm_final_params.torch --dyna1-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_81 --voxeldir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/voxels --ligdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/het --test-pids /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/test_pids.txt --outdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/cdk2_rmsd_warm --nsamples 50 --seed 0 --use_gpu

# 3) results
echo "=== from-scratch RMSD ==="; cat /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/cdk2_rmsd_scratch/cdk2_rmsd_summary.csv
echo "=== warm-start RMSD ===";  cat /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/cdk2_rmsd_warm/cdk2_rmsd_summary.csv
