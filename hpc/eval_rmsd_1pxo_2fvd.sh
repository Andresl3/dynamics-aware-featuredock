# CDK2 pose-RMSD for 1pxo + 2fvd, FeatureDock-paper settings:
#   --nsamples 500   (paper: "500 random rotations" per conformer)
#   --topk 4         (paper: "RMSD converged after picking 4 top-scored poses")
#   --prob-cutoff 0.5 (paper objective-function cutoff)
# RMSD formula is exactly the repo's (dbscan_cluster.py L48). Paper's CDK2
# result to beat: mean 2.4 A, median 2.1 A.
# Runs BOTH regimes (from-scratch + warm). 500 restarts x 2 pids x 4 model-evals
# is CPU-bound -> set --nthreads to your allocated core count.

source activate dynafeat 2>/dev/null || conda activate dynafeat
cd /scratch/mani.na/dynamics-aware-featuredock/featuredock

# a 2-line pid list for just these two structures
printf '1pxo\n2fvd\n' > /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pids_1pxo_2fvd.txt

# ===== from-scratch (5-block) =====
python -u /scratch/mani.na/dynamics-aware-featuredock/featuredock/src/models/evaluate_cdk2_rmsd.py --baseline-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/baseline80/baseline80_final_params.torch --baseline-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_80 --dyna1-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/dyna1_81/dyna1_81_final_params.torch --dyna1-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_81 --voxeldir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/voxels --ligdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/het --test-pids /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pids_1pxo_2fvd.txt --outdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/rmsd_1pxo_2fvd_scratch --nsamples 500 --topk 4 --prob-cutoff 0.5 --seed 0 --nthreads 8 --use_gpu

# ===== warm-start (20-block) =====
python -u /scratch/mani.na/dynamics-aware-featuredock/featuredock/src/models/evaluate_cdk2_rmsd.py --baseline-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/baseline80_warm/baseline80_warm_final_params.torch --baseline-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_80 --dyna1-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/dyna1_81_warm/dyna1_81_warm_final_params.torch --dyna1-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_81 --voxeldir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/voxels --ligdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/het --test-pids /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pids_1pxo_2fvd.txt --outdir /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/rmsd_1pxo_2fvd_warm --nsamples 500 --topk 4 --prob-cutoff 0.5 --seed 0 --nthreads 8 --use_gpu

echo "=== from-scratch (1pxo,2fvd) ==="; cat /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/rmsd_1pxo_2fvd_scratch/cdk2_rmsd_per_structure.csv
echo "=== warm-start (1pxo,2fvd) ===";  cat /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/rmsd_1pxo_2fvd_warm/cdk2_rmsd_per_structure.csv
