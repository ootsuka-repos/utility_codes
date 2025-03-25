import os
import shutil
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import random
import re
import time
import subprocess
from typing import Dict, Any, Optional

# last_flame_save.pyから関数をインポート
from last_flame_save import save_last_frame
from security import safe_command

# 定数と設定
CONFIG = {
    "server_address": "127.0.0.1:8188",
    "comfyui_output_path": "/home/user/デスクトップ/ComfyUI/output",
    "prompt_file_path": "/home/user/デスクトップ/image_and_video/workflow/wan_14b_i2v.json",
    "image_extensions": ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
    "default_steps": 15,
    "default_length": 24,
    "default_fps": 8,
    "max_seed": 1_000_000,
    "output_video_dir": "/home/user/デスクトップ/image_and_video/outputs/video",
    "input_mp4": "/home/user/デスクトップ/image_and_video/input.mp4"  # 入力MP4ファイルのパス
}

# テーマ設定
THEMES = {
    "フェラチオ": {
        "text": "A woman is lying on her stomach between the legs of the viewer and performing oral sex on a man. Her head moves up and down as she sucks the penis.",
        "lora_file": "wan_pov_blowjob.safetensors",
        "input_dir": "/home/user/デスクトップ/image_and_video/outputs/image/フェラチオ"
    },
    "セックス": {
        "text": "A man and woman having vaginal intercourse in missionary position with the woman's legs spread.",
        "lora_file": "wan_sex_missionary.safetensors",
        "input_dir": "/home/user/デスクトップ/image_and_video/outputs/image/セックス"
    },
    "パイズリ": {
        "text": "A woman is using her breasts to pleasure a man's penis, moving them up and down.",
        "lora_file": "wan_paizuri.safetensors",
        "input_dir": "/home/user/デスクトップ/image_and_video/outputs/image/パイズリ"
    }
}


class ComfyUIClient:
    """ComfyUI APIと通信するクライアントクラス"""
    
    def __init__(self, server_address: str):
        """クライアントの初期化"""
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.ws = websocket.WebSocket()
        self.connect()
        
    def connect(self) -> None:
        """WebSocketに接続"""
        try:
            self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        except Exception as e:
            print(f"WebSocket接続エラー: {e}")
            raise
            
    def queue_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """プロンプトをキューに追加"""
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        
        try:
            req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
            return json.loads(urllib.request.urlopen(req).read())
        except Exception as e:
            print(f"プロンプト送信エラー: {e}")
            raise
            
    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """指定IDの履歴を取得"""
        try:
            with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
                return json.loads(response.read())
        except Exception as e:
            print(f"履歴取得エラー: {e}")
            raise
            
    def get_images(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """プロンプトを実行して結果を取得"""
        try:
            prompt_id = self.queue_prompt(prompt)['prompt_id']
            
            # 処理完了を待機
            while True:
                out = self.ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break  # 実行完了
                time.sleep(0.1)
                
            return self.get_history(prompt_id)[prompt_id]
        except Exception as e:
            print(f"動画生成エラー: {e}")
            raise


class ImageProcessor:
    """動画処理とプロンプト生成を担当するクラス"""
    
    def __init__(self, config: Dict[str, Any], themes: Dict[str, Dict[str, str]]):
        self.config = config
        self.themes = themes
        
    def select_random_image(self, theme: str) -> Optional[str]:
        """テーマに基づいて入力動画をランダムに選択"""
        if theme not in self.themes:
            print(f"未定義のテーマです: {theme}")
            return None
            
        input_dir = self.themes[theme]["input_dir"]
        
        try:
            # 動画ファイルのリストを取得
            image_files = [
                f for f in os.listdir(input_dir)
                if os.path.isfile(os.path.join(input_dir, f)) and 
                any(f.lower().endswith(ext) for ext in self.config["image_extensions"])
            ]
            
            if not image_files:
                print(f"入力ディレクトリに動画がありません: {input_dir}")
                return None
                
            # ランダムに選択
            random_image = random.choice(image_files)
            return os.path.join(input_dir, random_image)
        except Exception as e:
            print(f"動画選択エラー: {e}")
            return None
            
    def prepare_prompt(self, image_path: str, theme: str) -> Dict[str, Any]:
        """ComfyUI用のプロンプトを準備"""
        # プロンプトテンプレートの読み込み
        try:
            with open(self.config["prompt_file_path"], 'r') as file:
                prompt_text = file.read()
            prompt = json.loads(prompt_text)
        except Exception as e:
            print(f"プロンプトファイル読み込みエラー: {e}")
            raise
            
        # テーマの設定を取得
        theme_settings = self.themes.get(theme, self.themes["フェラチオ"])  # デフォルト値
        theme_text = theme_settings["text"]
        lora_file = theme_settings["lora_file"]
        
        # 入力動画の名前から追加テキストを抽出
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        cleaned_name = re.sub(r'absurdres_seed_\d+', '', base_name)
        cleaned_name = cleaned_name.strip()
        full_text = f"{theme_text} {cleaned_name}"
        
        # プロンプトを更新
        prompt["3"]["inputs"]["seed"] = random.randint(1, self.config["max_seed"])
        prompt["3"]["inputs"]["steps"] = self.config["default_steps"]
        prompt["6"]["inputs"]["text"] = full_text
        prompt["28"]["inputs"]["fps"] = self.config["default_fps"]
        prompt["50"]["inputs"]["length"] = self.config["default_length"]
        prompt["52"]["inputs"]["image"] = image_path
        prompt["52"]["inputs"]["lora_name"] = lora_file
        
        return prompt
        
    def save_output_image(self, history: Dict[str, Any]) -> Optional[str]:
        """生成された動画を保存"""
        try:
            filename = history['outputs']['28']['images'][0]['filename']
            source_path = os.path.join(self.config["comfyui_output_path"], filename)
            
            # 出力ディレクトリの確認・作成
            output_dir = self.config.get("output_video_dir", os.getcwd())
            os.makedirs(output_dir, exist_ok=True)
            
            destination_path = os.path.join(output_dir, filename)
            
            shutil.copy(source_path, destination_path)
            print(f"動画を保存しました: {destination_path}")
            
            # webpをmp4に変換
            if destination_path.lower().endswith('.webp'):
                mp4_path = self.convert_webp_to_mp4(destination_path)
                return mp4_path
            return destination_path
        except Exception as e:
            print(f"動画保存エラー: {e}")
            return None
            
    def convert_webp_to_mp4(self, webp_path: str) -> Optional[str]:
        """WebP形式の動画をMP4形式に変換"""
        try:
            # 必要なライブラリをインポート
            try:
                import imageio
                import numpy as np
            except ImportError:
                print("imageioライブラリがインストールされていません。")
                print("インストールするには: pip install imageio numpy")
                return None
                
            # 出力ファイルのパスを作成
            mp4_path = os.path.splitext(webp_path)[0] + '.mp4'
            temp_dir = os.path.join(os.path.dirname(webp_path), "temp_frames")
            
            # 一時ディレクトリを作成
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # WebPを読み込んでフレームを抽出
                print("WebPファイルからフレームを抽出しています...")
                reader = imageio.get_reader(webp_path)
                
                # フレームをPNG画像として保存
                frame_paths = []
                for i, frame in enumerate(reader):
                    frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    imageio.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                
                if not frame_paths:
                    raise Exception("フレームを抽出できませんでした")
                    
                print(f"{len(frame_paths)}フレーム抽出しました")
                
                # FFmpegを使ってPNGからMP4を生成
                frames_cmd = [
                    'ffmpeg',
                    '-framerate', str(int(self.config["default_fps"])),  # intをstrに変換
                    '-pattern_type', 'glob',
                    '-i', f'{temp_dir}/frame_*.png',
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    '-y',
                    mp4_path
                ]
                frames_result = safe_command.run(subprocess.run, frames_cmd, capture_output=True, text=True)
                
                if frames_result.returncode != 0:
                    print(f"MP4生成エラー: {frames_result.stderr}")
                    raise Exception("MP4生成に失敗しました")
                
                print(f"MP4に変換しました: {mp4_path}")
                return mp4_path
                
            finally:
                # 一時ディレクトリを削除（成功・失敗に関わらず）
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            print(f"MP4変換エラー: {e}")
            return None

    def concatenate_videos(self, original_mp4: str, generated_mp4: str) -> Optional[str]:
        """元の動画と生成された動画を連結する"""
        try:
            # 出力ファイル名を設定
            base_name = os.path.splitext(os.path.basename(original_mp4))[0]
            output_dir = self.config["output_video_dir"]
            output_path = os.path.join(output_dir, f"{base_name}_extended.mp4")
            
            # 一時ファイルリストを作成
            temp_list_path = os.path.join(output_dir, "temp_file_list.txt")
            with open(temp_list_path, "w") as f:
                f.write(f"file '{os.path.abspath(original_mp4)}'\n")
                f.write(f"file '{os.path.abspath(generated_mp4)}'\n")
            
            # FFmpegを使って動画を連結
            concat_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', temp_list_path,
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            concat_result = safe_command.run(subprocess.run, concat_cmd, capture_output=True, text=True)
            
            # 一時ファイルを削除
            if os.path.exists(temp_list_path):
                os.remove(temp_list_path)
            
            if concat_result.returncode != 0:
                print(f"動画連結エラー: {concat_result.stderr}")
                raise Exception("動画の連結に失敗しました")
            
            print(f"動画を連結しました: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"動画連結エラー: {e}")
            return None

    def process_mp4_file(self, mp4_path: str, theme: str) -> Optional[str]:
        """MP4ファイルを処理: 最後のフレームを抽出→動画生成→連結"""
        try:
            # MP4の最後のフレームを抽出
            print(f"MP4の最後のフレームを抽出しています: {mp4_path}")
            last_frame_path = save_last_frame(mp4_path)
            
            # 指定されたテーマでプロンプトを準備
            prompt = self.prepare_prompt(last_frame_path, theme)
            
            # ComfyUIクライアントを作成
            client = ComfyUIClient(self.config["server_address"])
            
            # 新しい動画を生成
            print("動画生成を開始します...")
            history = client.get_images(prompt)
            
            # 生成された動画を保存
            generated_mp4 = self.save_output_image(history)
            if not generated_mp4:
                print("動画生成に失敗しました")
                return None
            
            # 元の動画と生成された動画を連結
            result_mp4 = self.concatenate_videos(mp4_path, generated_mp4)
            return result_mp4
            
        except Exception as e:
            print(f"MP4処理エラー: {e}")
            return None


def main():
    """メイン処理"""
    # シード初期化
    random.seed()
    
    # 使用するテーマを設定（ユーザーが選択可能）
    current_theme = "フェラチオ"
    
    # インスタンス作成
    processor = ImageProcessor(CONFIG, THEMES)
    
    # 指定されたMP4を処理
    input_mp4 = CONFIG["input_mp4"]
    while True:
            print(f"指定されたMP4ファイルを処理します: {input_mp4}")
            result_path = processor.process_mp4_file(input_mp4, current_theme)
            print(f"処理完了: {result_path}")
            input_mp4 = result_path

if __name__ == "__main__":
    main()
