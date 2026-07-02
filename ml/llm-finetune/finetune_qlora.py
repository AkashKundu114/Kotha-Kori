from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import torch, yaml, argparse

def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

def prepare_dataset(dataset_path: str):

    dataset = load_dataset("json", data_files=dataset_path, split="train")
    return dataset

def format_prompt(example: dict) -> dict:

    text = (
        "<|im_start|>system\n"
        "তুমি কোথা-খাতার AI সহায়ক। তুমি পশ্চিমবঙ্গের স্বনির্ভর গোষ্ঠীর মহিলাদের জন্য বাংলায় সাহায্য করো।<|im_end|>\n"
        "<|im_start|>user\n"
        f"{example['instruction']}\n\n"
        f"{example['input']}<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{example['output']}<|im_end|>"
    )
    return {"text": text}

def main(config_path: str):
    config = load_config(config_path)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    dataset = prepare_dataset(config["dataset_path"])
    dataset = dataset.map(format_prompt)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        args=TrainingArguments(
            output_dir="./output",
            num_train_epochs=3,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            save_steps=100,
            warmup_steps=50,
            lr_scheduler_type="cosine",
            report_to="tensorboard",
        ),
    )
    trainer.train()

    model.save_pretrained_gguf(
        "models/kotha-khata-qwen",
        tokenizer,
        quantization_method="q4_k_m"
    )
    print("✅ Model saved. Run: ollama create kotha-khata-qwen -f Modelfile")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/default.yaml")
    args = parser.parse_args()
    main(args.config)
