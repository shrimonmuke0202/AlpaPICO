TEST_PATH="dataset/validation.pkl"

CUDA_VISIBLE_DEVICES=0 python3 inference_instruct.py \
    --dataset_name conll2003 \
    --test_path $TEST_PATH   \
    --model_type llama \
    --max_instances -1 \
    --prediction_path prediction_ebm_comet_AlpaCare_new.json\
    --model_name path of trained model \
    --batch_size 4
