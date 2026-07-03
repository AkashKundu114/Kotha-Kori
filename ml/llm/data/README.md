# LLM Fine-Tuning Dataset

Expected file: kotha_khata_sft_dataset.jsonl

Format:
{"instruction": "...", "input": "Bengali text here", "output": "Expected structured output"}

Build this dataset using:
  python scripts/generate_scheme_qa.py        # ~500 scheme Q&A pairs
  python scripts/generate_ner_data.py         # ~3,000 financial NER examples
  python scripts/generate_meeting_data.py     # ~500 meeting minute examples
  + real pilot data (collected from week 18 onwards)

Target: 5,000-10,000 examples minimum for meaningful fine-tuning.
