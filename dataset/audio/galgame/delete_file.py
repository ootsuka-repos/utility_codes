import pandas as pd
import os
import shutil

def remove_files_not_in_csv(csv_path, base_directory):
    """
    CSVファイルに記載されていないファイルをベースディレクトリから削除します
    
    Args:
        csv_path (str): CSVファイルのパス
        base_directory (str): 削除対象のベースディレクトリ
    """
    # CSVファイルを読み込む
    print(f"{csv_path} を読み込んでいます...")
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    # FilePath列からファイルパスのリストを作成
    if 'FilePath' not in df.columns:
        print("エラー: CSVファイルにFilePathカラムが存在しません")
        return
        
    csv_files = set(df['FilePath'].tolist())
    print(f"CSVに含まれるファイル数: {len(csv_files)}")
    
    # 削除されたファイル数をカウント
    removed_count = 0
    skipped_count = 0
    removed_dir_count = 0
    
    # ベースディレクトリ内のすべてのファイルを走査
    for root, dirs, files in os.walk(base_directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            # CSVにないファイルを削除
            if file_path not in csv_files:
                try:
                    os.remove(file_path)
                    removed_count += 1
                    if removed_count % 100 == 0:
                        print(f"{removed_count} ファイルを削除しました...")
                except Exception as e:
                    print(f"エラー: {file_path} を削除できませんでした - {e}")
                    skipped_count += 1
    
    # index.jsonのみのディレクトリと空のディレクトリを削除
    for root, dirs, files in os.walk(base_directory, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            dir_contents = os.listdir(dir_path)
            
            # index.jsonのみのディレクトリの場合
            if len(dir_contents) == 1 and dir_contents[0] == "index.json":
                try:
                    json_path = os.path.join(dir_path, "index.json")
                    os.remove(json_path)
                    os.rmdir(dir_path)
                    removed_dir_count += 1
                    print(f"index.jsonのみのディレクトリを削除: {dir_path}")
                except Exception as e:
                    print(f"エラー: index.jsonのみのディレクトリ {dir_path} を削除できませんでした - {e}")
            
            # 空のディレクトリの場合
            elif not dir_contents:
                try:
                    os.rmdir(dir_path)
                    removed_dir_count += 1
                    print(f"空のディレクトリを削除: {dir_path}")
                except Exception as e:
                    print(f"エラー: 空のディレクトリ {dir_path} を削除できませんでした - {e}")
    
    print(f"合計 {removed_count} ファイルを削除しました")
    print(f"合計 {removed_dir_count} ディレクトリを削除しました")
    print(f"削除できなかったファイル: {skipped_count}")

def main():
    csv_path = r"F:\data.csv"
    base_directory = r"F:\Galgame_Dataset"
    remove_files_not_in_csv(csv_path, base_directory)

if __name__ == "__main__":
    main()