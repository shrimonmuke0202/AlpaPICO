BASE_MODEL_PATH="xz97/AlpaCare-llama1-7b"

TRAIN_PATH="dataset/train.pkl"
TEST_PATH="dataset/validation.pkl"



CUDA_VISIBLE_DEVICES=0 python3 train_instruct.py \
    --dataset_name conll2003 \
    --train_path $TRAIN_PATH \
    --test_path $TEST_PATH   \
    --output_dir models/Llama-2-model_demo \
    --test_size 0.3 \
    --random_seed 42 \
    --config_file configs/llama2_7b_lora.json \
    --model_type llama \
    --max_instances 1000 \
