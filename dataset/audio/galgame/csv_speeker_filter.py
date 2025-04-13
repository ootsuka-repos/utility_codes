import pandas as pd
import os

def filter_by_speaker_count(input_csv, output_csv, min_count=2000):
    """
    ゲームタイトルとキャラクターの組み合わせが指定した件数未満のデータを削除します
    """
    # CSVファイルを読み込む
    print(f"{input_csv} を読み込んでいます...")
    df = pd.read_csv(input_csv, encoding='utf-8')
    
    # 元のデータ行数を記録
    original_count = len(df)
    print(f"元のデータ行数: {original_count}")
    
    # 各ゲーム・キャラクターの組み合わせごとのデータ数をカウント
    combo_counts = df.groupby(['GameFolder', 'Speaker']).size().reset_index(name='count')
    print(f"ゲーム・キャラクターの組み合わせ総数: {len(combo_counts)}")
    
    # min_count件以上ある組み合わせを抽出
    valid_combos = combo_counts[combo_counts['count'] >= min_count]
    print(f"{min_count}件以上ある組み合わせ数: {len(valid_combos)}")
    
    # 有効な組み合わせをマージして一度にフィルタリング
    filtered_df = pd.merge(df, valid_combos[['GameFolder', 'Speaker']], 
                          on=['GameFolder', 'Speaker'], 
                          how='inner')
    
    # count列が含まれていれば削除
    if 'count' in filtered_df.columns:
        filtered_df = filtered_df.drop(columns=['count'])
    
    # FilePathカラムを絶対パスに変換
    if 'FilePath' in filtered_df.columns:
        print("FilePathカラムを絶対パスに変換しています...")
        base_dir = os.path.dirname(os.path.abspath(input_csv))
        
        # パスとゲームフォルダのマッピングを作成（高速化のため）
        path_to_game = dict(zip(filtered_df['FilePath'], filtered_df['GameFolder']))
        
        # 相対パスを絶対パスに変換する関数（最適化版）
        def to_absolute_path(row):
            # カウンター変数を静的変数として使用
            if not hasattr(to_absolute_path, "counter"):
                to_absolute_path.counter = 0
            if not hasattr(to_absolute_path, "total"):
                to_absolute_path.total = len(filtered_df)
            
            to_absolute_path.counter += 1
            
            # 100件ごとに進捗を表示
            if to_absolute_path.counter % 100 == 0 or to_absolute_path.counter == 1:
                progress = (to_absolute_path.counter / to_absolute_path.total) * 100
                print(f"処理中: {to_absolute_path.counter}/{to_absolute_path.total} ({progress:.1f}%)")
            
            path = row['FilePath']
            if not os.path.isabs(path):
                game_folder = row['GameFolder']
                return os.path.normpath(os.path.join(base_dir, game_folder, path))
            return path
        
        # 行ごとに適用して高速に変換
        filtered_df['FilePath'] = filtered_df.apply(to_absolute_path, axis=1)
        print("変換完了")
    
    # 結果を保存
    filtered_count = len(filtered_df)
    print(f"フィルタリング後のデータ行数: {filtered_count}")
    print(f"削除されたデータ行数: {original_count - filtered_count}")
    
    # 残ったゲーム数を表示
    remaining_games = filtered_df['GameFolder'].nunique()
    print(f"残ったゲーム数: {remaining_games}")
    
    # フィルタリングされたデータを新しいCSVファイルに保存
    filtered_df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"フィルタリングされたデータを {output_csv} に保存しました")

def main():
    # 入力CSVと出力CSVのパスを絶対パスで設定
    input_csv = r"F:\Galgame_Dataset\data.csv"
    output_csv = r"F:\Galgame_Dataset\data_.csv"
    
    # 2000件未満のデータを削除
    filter_by_speaker_count(input_csv, output_csv, min_count=2000)

if __name__ == "__main__":
    main()