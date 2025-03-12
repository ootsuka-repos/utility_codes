from huggingface_hub import login, upload_file, create_repo
import os
import glob
import argparse
from tqdm import tqdm

def parse_arguments():
    """コマンドライン引数をパースする"""
    parser = argparse.ArgumentParser(description='ファイルをHugging Face Hubにアップロードします')
    parser.add_argument('--dir', type=str, default="/home/user/ドキュメント/nsfw_anime",
                        help='アップロードするファイルのディレクトリパス')
    parser.add_argument('--repo', type=str, default="swdq/videos",
                        help='アップロード先のHugging Face Hubリポジトリ名')
    parser.add_argument('--repo-type', type=str, default="dataset", choices=['model', 'dataset'],
                        help='リポジトリのタイプ（model または dataset）')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Hugging Face Hubにログイン
    login()
    
    # リポジトリが存在しない場合は作成
    try:
        create_repo(args.repo, repo_type=args.repo_type, exist_ok=True)
        print(f"リポジトリ {args.repo} (タイプ: {args.repo_type}) を使用します")
    except Exception as e:
        print(f"リポジトリの作成中にエラーが発生しました: {str(e)}")
        return
    
    # ファイル一覧を再帰的に取得
    all_files = []
    base_dir = os.path.abspath(args.dir)
    print(f"ディレクトリ '{base_dir}' からファイルを再帰的に検索中...")
    
    for root, _, filenames in os.walk(base_dir):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            all_files.append(file_path)
    
    print(f"アップロード対象のファイル数: {len(all_files)}")
    
    # 各ファイルをアップロード
    uploaded_count = 0
    failed_count = 0
    
    for file_path in tqdm(all_files, desc="アップロード中"):
        try:
            # リポジトリ内のパスを元のディレクトリ構造を維持するように設定
            relative_path = os.path.relpath(file_path, base_dir)
            # ファイルをHugging Faceにアップロード（repo_typeパラメータを追加）
            upload_file(
                path_or_fileobj=file_path,
                path_in_repo=relative_path,
                repo_id=args.repo,
                repo_type=args.repo_type  # repo_typeパラメータを追加
            )
            uploaded_count += 1
            if uploaded_count % 10 == 0:  # 10ファイルごとに進捗を表示
                print(f"進捗: {uploaded_count}/{len(all_files)} ファイルをアップロード済み")
        except Exception as e:
            failed_count += 1
            print(f"エラー: {os.path.basename(file_path)} のアップロードに失敗: {str(e)}")
    
    print(f"\n完了: {uploaded_count}個のファイルが {args.repo} に正常にアップロードされました")
    if failed_count > 0:
        print(f"警告: {failed_count}個のファイルのアップロードに失敗しました")

if __name__ == "__main__":
    main()