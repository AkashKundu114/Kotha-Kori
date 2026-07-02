
from transformers import WhisperProcessor, WhisperForConditionalGeneration, Seq2SeqTrainer, Seq2SeqTrainingArguments
from datasets import load_dataset, Audio
from dataclasses import dataclass
import torch, evaluate

wer_metric = evaluate.load("wer")

def prepare_dataset(batch, processor):
    audio = batch["audio"]
    batch["input_features"] = processor.feature_extractor(
        audio["array"], sampling_rate=16000
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
    return batch

@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: any
    def __call__(self, features):
        import torch
        from transformers import BatchFeature
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        batch["labels"] = labels
        return batch

def main():
    MODEL = "openai/whisper-large-v3"
    processor = WhisperProcessor.from_pretrained(MODEL, language="Bengali", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(MODEL)

    model.generation_config.language = "Bengali"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None

    dataset = load_dataset("mozilla-foundation/common_voice_13_0", "bn", split="train+validation")
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    dataset = dataset.map(prepare_dataset, fn_kwargs={"processor": processor}, remove_columns=dataset.column_names)

    trainer = Seq2SeqTrainer(
        model=model,
        args=Seq2SeqTrainingArguments(
            output_dir="./models/bengali-large-v3",
            per_device_train_batch_size=8,
            gradient_accumulation_steps=2,
            learning_rate=1e-5,
            warmup_steps=200,
            num_train_epochs=5,
            gradient_checkpointing=True,
            fp16=True,
            predict_with_generate=True,
            generation_max_length=225,
            save_steps=200,
            logging_steps=25,
            report_to=["tensorboard"],
        ),
        train_dataset=dataset,
        data_collator=DataCollatorSpeechSeq2SeqWithPadding(processor=processor),
        compute_metrics=lambda pred: {
            "wer": wer_metric.compute(
                predictions=processor.tokenizer.batch_decode(pred.predictions, skip_special_tokens=True),
                references=processor.tokenizer.batch_decode(pred.label_ids, skip_special_tokens=True)
            )
        },
        tokenizer=processor.feature_extractor,
    )
    trainer.train()
    trainer.save_model("./models/bengali-large-v3")
    print("✅ Whisper fine-tuned model saved.")

if __name__ == "__main__":
    main()
