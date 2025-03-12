import os
import subprocess
import pathlib
from tqdm import tqdm

def convert_to_mp4(source_path):
    """ファイルをMP4形式に変換する"""
    output_path = source_path.with_suffix('.mp4')
    
    # 既にMP4ファイルが存在する場合は別名を付ける
    if output_path.exists():
        base = output_path.stem
        counter = 1
        while output_path.exists():
            output_path = output_path.with_name(f"{base}_{counter}.mp4")
            counter += 1
    
    try:
        # FFmpegを使用して変換
        subprocess.run([
            'ffmpeg', 
            '-i', str(source_path),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-y',
            str(output_path)
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"変換成功: {source_path} → {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"変換エラー ({source_path}): {e}")
        return False

def main():
    # 対象ディレクトリ
    target_dir = pathlib.Path('/home/user/ドキュメント/data')
    
    # MP4以外の変換対象となる拡張子
    video_extensions = ['.gif', '.webm', '.avi', '.mov', '.mkv', '.flv']
    
    # ディレクトリ内のファイルを検索
    files_to_convert = []
    for file_path in target_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            files_to_convert.append(file_path)
    
    if not files_to_convert:
        print("変換が必要なファイルが見つかりませんでした。")
        return
    
    print(f"{len(files_to_convert)}個のファイルを変換します...")
    
    # 進捗バーを表示しながら変換
    success_count = 0
    for file_path in tqdm(files_to_convert):
        if convert_to_mp4(file_path):
            success_count += 1
    
    print(f"変換完了: {success_count}/{len(files_to_convert)}ファイルを変換しました。")
    
    # 変換後、元ファイルを削除するかの確認
    if success_count > 0:
        answer = input("変換元のファイルを削除しますか？ (y/n): ")
        if answer.lower() == 'y':
            for file_path in files_to_convert:
                if file_path.with_suffix('.mp4').exists() or any(file_path.with_name(f"{file_path.stem}_{i}.mp4").exists() for i in range(1, 10)):
                    os.remove(file_path)
                    print(f"削除: {file_path}")

if __name__ == "__main__":
    # FFmpegが利用可能か確認
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("FFmpegがインストールされていません。次のコマンドでインストールしてください:")
        print("sudo apt install ffmpeg")
        exit(1)
    
    main()