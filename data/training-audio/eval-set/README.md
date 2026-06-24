# STT Evaluation Set

This directory should contain 500 labeled Bengali audio samples for weekly STT evaluation.

Format (JSONL): eval_set.jsonl
{"audio_path": "sample_001.wav", "ground_truth": "আজ ৩০০ টাকা পাপড় বিক্রি করেছি", "dialect": "rarhi"}

Sources:
1. Record during pilot (with consent) — 200 samples per dialect
2. Mozilla Common Voice test split
3. Synthetic: TTS + noise augmentation
