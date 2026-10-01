# Train a small PromQL question router

This workflow applies Week 5's synthetic-data, LoRA, merge, and baseline-comparison techniques to a narrow task: route a learning request into one of five intents. The routing model does not write tutorials, assign grades, or award badges. The larger optional tutor model remains responsible for grounded explanations.

**Status:** the data pipeline, configs, notebook, evaluator, and runtime hook are implemented. GPU training has not been run for this repository; there are no bundled weights or claimed accuracy gains.

## Dataset

`python training/prepare.py` creates 120 training examples and 30 validation examples from 50 authored seed questions. For each of the five labels, eight seed families go to training and two to validation; simple prompt variations are generated **after** the split. A seed and its variations cannot leak across splits. The generator records a split manifest and LLaMA Factory ShareGPT metadata.

Labels: `explain_concept`, `compare_sql`, `debug_query`, `practice_request`, `needs_clarification`. Outputs are JSON with `intent`, `tool: "none"`, and an empty `query`. Security-related questions are included, but routing classification is not the security boundary; tool and grading permissions are independently enforced in Python.

The dataset is intentionally small and templated. Validation examples are correlated within seed families. Do not describe validation accuracy as independent generalization, and do not tune repeatedly on the same validation set. Gather a separate human-authored test set before enabling the model for real learners.

## Reproducible GPU workflow

Open [train_router.ipynb](train_router.ipynb) in Colab and select a T4 GPU. Or use a separate Linux GPU environment with compatible CUDA/PyTorch and [LLaMA Factory](https://github.com/hiyouga/LLaMA-Factory).

```bash
pip install -e '.[training]'
pip install 'llamafactory>=0.9.3,<1'
python training/prepare.py
python training/evaluate.py --model Qwen/Qwen3-1.7B-Base --output training/data/baseline.json
llamafactory-cli train training/lora.yaml
llamafactory-cli export training/merge.yaml
python training/evaluate.py --model training/output/router-merged --output training/data/merged.json
```

The selected model is [Qwen3-1.7B-Base](https://huggingface.co/Qwen/Qwen3-1.7B-Base). Training uses rank-8 LoRA, alpha 16, all eligible linear layers, 512-token inputs, FP16, a per-device batch of one, accumulation of eight, and three epochs. A T4 does not support native BF16, so the config uses FP16. The `qwen3_nothink` template matches this short JSON classification task, following the official [LLaMA Factory SFT](https://llamafactory.readthedocs.io/en/latest/getting_started/sft.html) and [merge](https://llamafactory.readthedocs.io/en/latest/getting_started/merge_lora.html) examples.

For a QLoRA experiment, copy `lora.yaml` and add `quantization_bit: 4` and `quantization_method: bitsandbytes` in a compatible CUDA environment with bitsandbytes installed. Treat its measured behavior as a separate experiment; the default is ordinary LoRA. Check framework compatibility and GPU memory before launching a paid run.

The evaluator records actual accuracy, per-class precision/recall/F1, a confusion matrix, invalid JSON predictions, and mean generation latency. Compare base and merged results on identical validation rows. The notebook prints the measured accuracy delta without inventing an expected gain. Archive software versions, training logs, the split manifest, and configs with your own run.

## Serve an evaluated router

After reviewing the evaluation, start the [LLaMA Factory API](https://llamafactory.readthedocs.io/en/latest/getting_started/inference.html) on a trusted local host:

```bash
API_HOST=127.0.0.1 API_PORT=8000 llamafactory-cli api training/serve.yaml
```

In the academy `.env`:

```dotenv
ROUTER_BASE_URL=http://127.0.0.1:8000/v1
ROUTER_MODEL=training/output/router-merged
```

Use the model identifier advertised by the inference server if it differs. The runtime validates JSON against a Pydantic intent enum and forcibly clears tool/query fields from router output. If the endpoint is absent or fails validation, the deterministic baseline router is retained. Keep inference on loopback or an authenticated internal endpoint; do not publish an unauthenticated model server.
