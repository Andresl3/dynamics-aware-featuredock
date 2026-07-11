# CDK2 occupancy head-to-head for the WARM-START models.
# Paste these lines directly into a terminal on a compute node (all absolute paths).

# 1) activate the environment (adjust the name if yours differs)
source activate dynafeat 2>/dev/null || conda activate dynafeat

# 2) run the evaluation (baseline_warm vs dyna1_81_warm on the 18 CDK2 structures)
cd /scratch/mani.na/dynamics-aware-featuredock/featuredock

python -u /scratch/mani.na/dynamics-aware-featuredock/featuredock/src/models/evaluate_cdk2.py \
    --baseline-ckpt /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/baseline80_warm/baseline80_warm_final_params.torch \
    --baseline-data /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_80 \
    --dyna1-ckpt    /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/dyna1_81_warm/dyna1_81_warm_final_params.torch \
    --dyna1-data    /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/pvar_81 \
    --test-pids     /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/test_pids.txt \
    --outdir        /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/cdk2_eval_warm \
    --use_gpu

# 3) look at the outputs
ls -la /scratch/mani.na/dynamics-aware-featuredock/dyna_featuredock_out/results/cdk2_eval_warm/
