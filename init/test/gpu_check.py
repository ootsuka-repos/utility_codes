import torch
# GPUが利用可能か確認
gpu_available = torch.cuda.is_available()
print(f"GPU Available: {gpu_available}")

# GPUの数を取得
num_gpus = torch.cuda.device_count()
print(f"Number of GPUs: {num_gpus}")

# 各GPUの名前を取得
for i in range(num_gpus):
    print(f"GPU {i}: {torch.cuda.get_device_name(i)}")

# 現在のデフォルトGPUを取得
print(f"Current Device: {torch.cuda.current_device()}")

from huggingface_hub import hf_hub_download

model_name = "Lightricks/LTX-Video"
model_path = hf_hub_download(model_name, filename="License.txt")  # 例: config.json のパスを取得
print("Model path:", model_path)
