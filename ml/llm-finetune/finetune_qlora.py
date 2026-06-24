"""
QLoRA fine-tuning of Qwen2.5-7B-Instruct for Kotha-Khata.

What we're fine-tuning FOR:
  1. Bengali financial entity extraction (ledger)
  2. West Bengal government scheme eligibility Q&A
  3. Bengali meeting minutes parsing
  4. Instruction-following in dialectal Bengali
  5. Strict "refuse to hallucinate" behaviour on scheme data

Hardware needed: 1x RTX 3090 (24GB) or 1x A10G (24GB)
Training time: ~4–6 hours for 10,000 examples
Cost on RunPod: ~$2–3 (one-time)

Usage:
  python finetune_qlora.py --config config/default.yaml
"""

from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
import torch, yaml, argparse

def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

def prepare_dataset(dataset_path: str):
    """
    Expected dataset format (JSONL):
    {
      "instruction": "নিচের বাংলা বাক্য থেকে আর্থিক তথ্য বের করো।",
      "input": "আজ আমি ১৫ প্যাকেট পাপড় ৩০০ টাকায় বিক্রি করেছি।",
      "output": "{\"transactions\": [{\"type\": \"INCOME\", \"amount_inr\": 300, ...}]}"
    }
    """
    dataset = load_dataset("json", data_files=dataset_path, split="train")
    return dataset

def format_prompt(example: dict) -> dict:
    """Qwen2.5 chat template format."""
    text = f"""<|im_start|>system
তুমি কোথা-খাতার AI সহায়ক। তুমি পশ্চিমবঙ্গের স্বনির্ভর গোষ্ঠীর মহিলাদের জন্য বাংলায় সাহায্য করো।<|im_end|>
<|im_start|>user
{example['instruction']}

{example['input']}<|im_end|>
<|im_start|>assistant
{example['output']}<|im_end|>"""
    return {"text": text}

def main(config_path: str):
    config = load_config(config_path)

    # ── Load base model with Unsloth (4x faster fine-tuning) ────────
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
        max_seq_length=2048,
        dtype=None,  # Auto-detect
        load_in_4bit=True,  # QLoRA: 4-bit quantization
    )

    # ── Apply LoRA adapters ─────────────────────────────────────────
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,                       # LoRA rank
        target_modules=[            # Attention + FFN layers
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # ── Prepare dataset ─────────────────────────────────────────────
    dataset = prepare_dataset(config["dataset_path"])
    dataset = dataset.map(format_prompt)

    # ── Training ─────────────────────────────────────────────────────
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

    # ── Save + convert to GGUF for Ollama ────────────────────────────
    model.save_pretrained_gguf(
        "models/kotha-khata-qwen",
        tokenizer,
        quantization_method="q4_k_m"  # Best quality/size balance
    )
    print("✅ Model saved. Run: ollama create kotha-khata-qwen -f Modelfile")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/default.yaml")
    args = parser.parse_args()
    main(args.config)
