#!/usr/bin/env python3

import os
import subprocess
import glob
from security import safe_command

# 対象ディレクトリ
video_dir = "/home/user/ドキュメント/data"

# 閾値設定
threshold_fps = 30.0  # FPS閾値を30に変更
threshold_frames = 90  # フレーム数の閾値（例: 1000フレーム以下）
threshold_duration = 2.0  # 動画の長さの閾値（2秒以下）

# すべてのmp4ファイルを取得
video_files = glob.glob(os.path.join(video_dir, "*.mp4"))

# カウンタとリスト初期化
total_count = len(video_files)
to_delete_files = []

print(f"合計 {total_count} 個のmp4ファイルを処理します...")

# 最初に削除対象のファイルを特定
for video in video_files:
    try:
        # ffprobeでフレームレートを取得
        cmd_fps = [
            "ffprobe", "-v", "error", 
            "-select_streams", "v:0", 
            "-show_entries", "stream=r_frame_rate", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            video
        ]
        
        result = safe_command.run(subprocess.run, cmd_fps, capture_output=True, text=True)
        fps_str = result.stdout.strip()
        
        # 分数形式のフレームレートを計算（例：24000/1001）
        if '/' in fps_str:
            num, den = map(float, fps_str.split('/'))
            fps = num / den
        else:
            fps = float(fps_str)
        
        # 動画の長さ（秒）を取得
        cmd_duration = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video
        ]
        
        result = safe_command.run(subprocess.run, cmd_duration, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        # フレーム数を計算
        frame_count = int(duration * fps)
        
        # FPSが30以下、フレーム数が閾値以下、または動画の長さが2秒以下なら削除リストに追加
        if fps <= threshold_fps or frame_count <= threshold_frames or duration <= threshold_duration:
            to_delete_files.append((video, fps, frame_count, duration))
            print(f"削除候補: {os.path.basename(video)} (FPS: {fps:.2f}, フレーム数: {frame_count}, 長さ: {duration:.2f}秒)")
        else:
            print(f"保持: {os.path.basename(video)} (FPS: {fps:.2f}, フレーム数: {frame_count}, 長さ: {duration:.2f}秒)")
            
    except Exception as e:
        print(f"エラー ({os.path.basename(video)}): {str(e)}")

# 削除確認
if to_delete_files:
    print(f"\n{len(to_delete_files)} 個のファイルが削除対象です。")
    response = input("これらのファイルを削除しますか？ [y/n]: ").lower()
    
    if response == 'y':
        # 実際に削除を実行
        deleted_count = 0
        for video, fps, frame_count, duration in to_delete_files:
            try:
                os.remove(video)
                print(f"削除完了: {os.path.basename(video)} (FPS: {fps:.2f}, フレーム数: {frame_count}, 長さ: {duration:.2f}秒)")
                deleted_count += 1
            except Exception as e:
                print(f"削除エラー ({os.path.basename(video)}): {str(e)}")
                
        print(f"\n処理完了: {deleted_count}/{total_count} 個のファイルを削除しました")
    else:
        print("削除をキャンセルしました。")
else:
    print("\n削除対象のファイルはありませんでした。")
