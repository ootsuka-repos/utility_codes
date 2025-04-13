import os
import json
import csv
import glob
from pathlib import Path

def collect_json_data(root_folder):
    """指定されたフォルダ内のすべてのindex.jsonファイルからデータを収集します"""
    all_data = []
    
    # すべてのindex.jsonファイルを再帰的に検索
    json_files = glob.glob(os.path.join(root_folder, "**", "index.json"), recursive=True)
    
    for json_file in json_files:
        try:
            # 作品フォルダ名を取得（親ディレクトリの名前）
            game_folder = Path(json_file).parent.name
            
            # JSONファイルを読み込む
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # データがリスト形式であると仮定
            if isinstance(data, list):
                for item in data:
                    # 必要なフィールドが存在するか確認
                    if all(key in item for key in ["Speaker", "Text", "FilePath"]):
                        # ゲームフォルダ名を追加情報として含める
                        item["GameFolder"] = game_folder
                        all_data.append(item)
            else:
                print(f"警告: {json_file} はリスト形式ではありません")
                
        except Exception as e:
            print(f"エラー: {json_file} の処理中に問題が発生しました: {e}")
    
    return all_data

def save_to_csv(data, output_file):
    """データをCSVファイルに保存します"""
    if not data:
        print("保存するデータがありません")
        return
    
    # ヘッダーを設定（最初のデータ項目からキーを取得）
    fieldnames = ["GameFolder", "Speaker", "Text", "FilePath"]
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"データを {output_file} に保存しました（合計 {len(data)} 行）")

def main():
    # ルートフォルダとCSV出力パスを設定
    root_folder = r"F:\Galgame_Dataset"
    output_csv = r"F:\Galgame_Dataset\all_dialogues.csv"
    
    # データを収集してCSVに保存
    print("JSONファイルからデータを収集しています...")
    all_data = collect_json_data(root_folder)
    print(f"合計 {len(all_data)} 行のデータが見つかりました")
    
    save_to_csv(all_data, output_csv)

if __name__ == "__main__":
    main()