BASE_MODEL_PATH="meta-llama/Llama-2-7b-hf"

# TRAIN_PATH="ebm_dataset/train.pkl"
TEST_PATH="ebm_comet_dataset/validation.pkl"



CUDA_VISIBLE_DEVICES=0 python3 inference_instruct.py \
    --dataset_name conll2003 \
    --test_path $TEST_PATH   \
    --model_type llama \
    --max_instances -1 \
    --prediction_path prediction_ebm_comet_AlpaCare_new.json\
    --model_name /notebooks/NER/instruct-ner/instruction_ner/models_AlpaCare_rev_ebm_comet/llama2-conll2003 \
    --batch_size 4
    # --org_model_name meta-llama/Llama-2-7b-hf
