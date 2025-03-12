import os
import glob

def rename_audio_files(directory):
    # 一般的な音声ファイルの拡張子
    audio_extensions = ['.mp4', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma']
    
    # 音声ファイルを収集
    audio_files = []
    for ext in audio_extensions:
        pattern = os.path.join(directory, f'*{ext}')
        audio_files.extend(glob.glob(pattern))
    
    # ファイルをソート
    audio_files.sort()
    
    if not audio_files:
        print("音声ファイルが見つかりませんでした")
        return
    
    # 一時的なリネーム（競合を避けるため）
    for i, file_path in enumerate(audio_files):
        dir_name = os.path.dirname(file_path)
        ext = os.path.splitext(file_path)[1]
        temp_path = os.path.join(dir_name, f"temp_{i}{ext}")
        os.rename(file_path, temp_path)
    
    # 最終的なリネーム
    temp_files = glob.glob(os.path.join(directory, "temp_*"))
    temp_files.sort()
    
    for i, temp_path in enumerate(temp_files, 1):
        dir_name = os.path.dirname(temp_path)
        ext = os.path.splitext(temp_path)[1]
        new_path = os.path.join(dir_name, f"{i}{ext}")
        os.rename(temp_path, new_path)
        print(f"リネーム完了: {new_path}")
    
    print(f"合計 {len(audio_files)} 個のファイルをリネームしました")

# 実行
if __name__ == "__main__":
    directory = '/home/user/ドキュメント/data'
    rename_audio_files(directory)