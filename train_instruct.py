import argparse
import json
import os
import pickle as pkl

import numpy as np
import torch
import wandb
from peft import (LoraConfig, PeftConfig, PeftModel, get_peft_model,
                  prepare_model_for_kbit_training)
from train_utils import fix_model, fix_tokenizer, set_random_seed, SUPPORTED_DATASETS
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          DataCollatorForSeq2Seq,
                          DataCollatorForTokenClassification, EvalPrediction,
                          T5ForConditionalGeneration, Trainer, TrainerCallback,
                          TrainerControl, TrainerState, TrainingArguments)
from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR

from utils.instruct_dataset import InstructDataset, Instruction
# from metric import calculate_metrics, extract_classes

hf_auth = 'Your Huggingface Key'


# https://github.com/huggingface/peft/issues/96
class SavePeftModelCallback(TrainerCallback):
    def on_save(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        checkpoint_folder = os.path.join(
            args.output_dir, f"{PREFIX_CHECKPOINT_DIR}-{state.global_step}"
        )

        peft_model_path = os.path.join(checkpoint_folder, "adapter_model")
        kwargs["model"].save_pretrained(peft_model_path)
        return control


def train(
    train_instructions: list[Instruction],
    test_instructions: list[Instruction],
    model_type: str,
    dataset_name: str,
    output_dir: str,
    seed: int,
    config_file: str,
    push_to_hub: bool
):
    set_random_seed(seed)
    with open(config_file, "r") as r:
        config = json.load(r)

    lora_config = config.get("lora")
    model_name = config['model_name']
    
    tokenizer = AutoTokenizer.from_pretrained(model_name,use_auth_token=hf_auth)
    tokenizer = fix_tokenizer(tokenizer)

    
    
    only_target_loss = config.get("only_target_loss", True)
    max_source_tokens_count = config["max_source_tokens_count"]
    max_target_tokens_count = config["max_target_tokens_count"]
    
    train_dataset = InstructDataset(
        train_instructions,
        tokenizer,
        max_source_tokens_count=max_source_tokens_count,
        max_target_tokens_count=max_target_tokens_count,
        model_type=model_type,
        only_target_loss=only_target_loss
    )

    val_dataset = InstructDataset(
        test_instructions,
        tokenizer,
        max_source_tokens_count=max_source_tokens_count,
        max_target_tokens_count=max_target_tokens_count,
        model_type=model_type,
        only_target_loss=only_target_loss
    )

    model_classes = {
        'llama': {
            'data_collator': DataCollatorForTokenClassification,
            'model': AutoModelForCausalLM
        },
        't5': {
            'data_collator': DataCollatorForSeq2Seq,
            'model': T5ForConditionalGeneration
        }
    }
    
    data_collator = model_classes[model_type]['data_collator'](tokenizer, pad_to_multiple_of=8)

    load_in_8bit = bool(config.get("load_in_8bit", True))
    is_adapter = config['is_adapter']
    if load_in_8bit:
        if is_adapter:
            peft_config = PeftConfig.from_pretrained(model_name)
            model = model_classes[model_type]['model'].from_pretrained(
                peft_config.base_model_name_or_path,
                load_in_8bit=True,
                device_map='auto',
                use_flash_attention_2=True,
                use_auth_token=hf_auth
            )
            model = fix_model(model, tokenizer, use_resize=False)
            model = prepare_model_for_kbit_training(model)
            model = PeftModel.from_pretrained(model, model_name, is_trainable=True)
        else:
            model = model_classes[model_type]['model'].from_pretrained(
                model_name,
                load_in_8bit=True,
                device_map='auto',
                use_flash_attention_2=True,
                use_auth_token=hf_auth
            )
            model = fix_model(model, tokenizer, use_resize=False)
            model = prepare_model_for_kbit_training(model)
            peft_config = LoraConfig(**lora_config) 
            model = get_peft_model(model, peft_config)            
    else:
        model = AutoModelForCausalLM.from_pretrained(model_name,use_auth_token=hf_auth)
        model = fix_model(model, tokenizer, use_resize=False)
    
    # Default model generation params
    model.config.num_beams = 5
    max_tokens_count = max_target_tokens_count + max_source_tokens_count + 1
    model.config.max_length = max_tokens_count

    if torch.cuda.device_count() > 1:
        model.is_parallelizable = True
        model.model_parallel = True

    deepspeed_config = config.get("deepspeed")
    trainer_config = config["trainer"]
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        save_total_limit=1,
        load_best_model_at_end=True,
        report_to='wandb',
        ddp_find_unused_parameters=None,
        deepspeed=deepspeed_config,
        **trainer_config
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        callbacks=[SavePeftModelCallback],
        data_collator=data_collator,
    )
    
    with wandb.init(project="Instruction NER") as run:
        model.print_trainable_parameters()
        trainer.train()
        if 'llama2' in config_file:
            model_type = 'llama2'
        if push_to_hub:
            model.save_pretrained(f"models/{model_type}-{dataset_name}")
            print(model.generation_config)
            model.generation_config.to_json_file(f"models/{model_type}-{dataset_name}/generation_config.json")
            model.config.to_json_file(f"models/{model_type}-{dataset_name}/config.json")
            tokenizer.save_pretrained(f"models/{model_type}-{dataset_name}")
        
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name", default='rudrec', type=str, help='name of dataset')
    parser.add_argument("--train_path", default='ebm_dataset/train.pkl', type=str, help='train_dataset')
    parser.add_argument("--test_path", default='ebm_dataset/validation.pkl', type=str, help='test_dataset')

    parser.add_argument("--data_path", default='data/rudrec/rudrec_annotated.json', type=str, help='train file_path')
    parser.add_argument("--output_dir", default='models/', type=str, help='output_dir')
    parser.add_argument("--test_size", default=0.3, type=float, help='test_size')
    parser.add_argument("--random_seed", default=42, type=int, help='random_seed')
    parser.add_argument("--config_file", default='configs/llama_7b_lora.json', type=str, help='path to config file')
    parser.add_argument("--model_type", default='llama', type=str, help='model type')
    parser.add_argument("--max_instances", default=-1, type=int, help='max number of instructions')
    parser.add_argument("--push_to_hub", default=True, type=bool, help='push to hugginface hub')
    arguments = parser.parse_args()

    assert arguments.dataset_name in SUPPORTED_DATASETS, f'expected dataset name from {SUPPORTED_DATASETS}'

    if arguments.dataset_name == 'rudrec':
        from utils.rudrec.rudrec_reader import create_train_test_instruct_datasets
        train_dataset, test_dataset = create_train_test_instruct_datasets(
            data_path=arguments.data_path,
            max_instances=arguments.max_instances,
            test_size=arguments.test_size,
            random_seed=arguments.random_seed
        )       
    elif arguments.dataset_name =='nerel_bio':
        from utils.nerel_bio.nerel_reader import create_instruct_dataset
        train_path = os.path.join(arguments.data_path, 'train')
        test_path = os.path.join(arguments.data_path, 'test')
        train_dataset = create_instruct_dataset(train_path, max_instances=arguments.max_instances)
        test_dataset = create_instruct_dataset(test_path, max_instances=arguments.max_instances)
    else:
        from utils.conll2003.conll_reader import create_instruct_dataset
        train_dataset = pkl.load(open(arguments.train_path,"rb"))
        test_dataset = pkl.load(open(arguments.test_path,"rb"))


    train(
        train_instructions=train_dataset,
        test_instructions=test_dataset,
        model_type=arguments.model_type,
        dataset_name=arguments.dataset_name,
        output_dir=arguments.output_dir,
        seed=arguments.random_seed,
        config_file=arguments.config_file,
        push_to_hub=arguments.push_to_hub
    )
    