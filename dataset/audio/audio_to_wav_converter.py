import os
import subprocess
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

# 対象とする音声ファイルの拡張子
supported_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.alac', '.aiff', '.opus']

def convert_audio(file_path):
    try:
        base, ext = os.path.splitext(file_path)
        temp_output_file = base + "_temp.wav"
        final_output_file = base + ".wav"
        
        # ffmpegコマンドの最適化
        cmd = [
            "ffmpeg",
            "-y",                    # 上書き確認なし
            "-hide_banner",          # バナー非表示で出力を減らす
            "-loglevel", "error",    # エラーのみ出力
            "-i", file_path,         # 入力ファイル
            "-ar", "48000",          # サンプルレート指定
            "-threads", "52",
            temp_output_file         # 一時出力ファイル
        ]
        
        # 出力とエラーをキャプチャせずに高速化
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        
        # ファイル操作の一連の流れを試行
        os.remove(file_path)
        os.rename(temp_output_file, final_output_file)
        return f"成功: {file_path} -> {final_output_file}"
        
    except subprocess.CalledProcessError as e:
        return f"変換失敗: {file_path}"
    except Exception as e:
        return f"エラー: {file_path} - {str(e)}"

def process_batch(file_batch):
    results = []
    for file_path in file_batch:
        results.append(convert_audio(file_path))
    return results

def main():
    root_dir = r"F:\Data"
    files_to_convert = []

    # 変換対象ファイルのリストを一度に構築
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            _, ext = os.path.splitext(file)
            if ext.lower() in supported_extensions:
                files_to_convert.append(os.path.join(dirpath, file))
    
    total_files = len(files_to_convert)
    print(f"変換対象ファイル数: {total_files}")
    
    # CPUコア数に基づいてワーカー数を決定（少し余裕を持たせる）
    workers = 26
    
    # バッチサイズを調整（小さなファイルが多い場合に効果的）
    batch_size = 20
    batches = [files_to_convert[i:i+batch_size] for i in range(0, total_files, batch_size)]
    
    completed = 0
    
    # 並列処理で変換実行
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_batch, batch) for batch in batches]
        
        for future in as_completed(futures):
            results = future.result()
            completed += len(results)
            print(f"進捗: {completed}/{total_files} ({(completed/total_files*100):.1f}%)")

if __name__ == "__main__":
    main()