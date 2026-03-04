# services/model_config.py
"""
Central configuration for LLM models, their hardware requirements, and estimated costs.
"""

MODEL_CONFIGS = {
    "llama3:8b": {
        "name": "Llama 3 (8B)",
        "params": "8B",
        "gpu_type": "NVIDIA GeForce RTX 4090",
        "gpu_count": 1,
        "storage_gb": 50,
        "estimated_cost_hr": 0.45,
        "description": "Fast and efficient for general tasks."
    },
    "llama3:70b": {
        "name": "Llama 3 (70B)",
        "params": "70B",
        "gpu_type": "NVIDIA RTX A6000",
        "gpu_count": 2,
        "storage_gb": 250,
        "estimated_cost_hr": 1.65,
        "description": "High intelligence for complex reasoning."
    },
    "Qwen/Qwen2.5-32B-Instruct-AWQ": {
        "name": "Qwen 2.5 (32B AWQ)",
        "params": "32B",
        "gpu_type": "NVIDIA RTX A6000",
        "gpu_count": 1,
        "storage_gb": 150,
        "estimated_cost_hr": 0.85,
        "description": "Excellent performance-to-cost ratio."
    },
    "mistralai/Mixtral-8x7B-Instruct-v0.1": {
        "name": "Mixtral 8x7B",
        "params": "8x7B",
        "gpu_type": "NVIDIA RTX A6000",
        "gpu_count": 2,
        "storage_gb": 250,
        "estimated_cost_hr": 1.65,
        "description": "Powerful mixture-of-experts model."
    },
    "deepseek-ai/deepseek-coder-33b-instruct": {
        "name": "DeepSeek Coder (33B)",
        "params": "33B",
        "gpu_type": "NVIDIA RTX A6000",
        "gpu_count": 1,
        "storage_gb": 150,
        "estimated_cost_hr": 0.85,
        "description": "Top-tier code generation and logic."
    }
}

def get_model_specs(model_id: str) -> dict:
    return MODEL_CONFIGS.get(model_id, MODEL_CONFIGS["llama3:8b"])
