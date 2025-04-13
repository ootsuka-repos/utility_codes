import pandas as pd
import shutil
import os
from pathlib import Path
from pydub import AudioSegment
import concurrent.futures
from tqdm import tqdm  # 進捗バーの表示用
import multiprocessing

class DatasetProcessor:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.output_dir = self.base_dir / "Data"
        self.raw_dir = self.output_dir / "raw"
        self.labels = ['usual', 'aegi', 'chupa']
        self.samples_per_label = 10000  # 各ラベルごとに抽出するサンプル数
        self.max_workers = 28
        print(f"使用するワーカー数: {self.max_workers}")

    def setup_directories(self):
        """必要なディレクトリを作成"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for label in self.labels:
            (self.raw_dir / label).mkdir(parents=True, exist_ok=True)

    def filter_and_classify_data(self, input_csv_path: str):
        """各ラベルごとに最大サンプル数をサンプリング（並列処理）"""
        print("処理開始: 各ラベルごとに最大3万件をランダムサンプリングします")
        
        # CSVファイルを読み込む
        df = pd.read_csv(input_csv_path)
        
        # ラベルごとの処理を並列実行
        filtered_data_all = pd.DataFrame()
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(len(self.labels), self.max_workers)) as executor:
            # 各ラベルの処理を並列実行
            future_to_label = {
                executor.submit(self._process_label_parallel, df, label): label 
                for label in self.labels
            }
            
            # 結果を収集
            for future in concurrent.futures.as_completed(future_to_label):
                label = future_to_label[future]
                try:
                    filtered_df = future.result()
                    filtered_data_all = pd.concat([filtered_data_all, filtered_df])
                    print(f"{label}の処理が完了しました。データ数: {len(filtered_df)}行")
                except Exception as e:
                    print(f"{label}の処理中にエラーが発生しました: {str(e)}")
        
        # フィルタリング済みデータのESDリストを作成
        self.create_esd_list(filtered_data_all)

    def _process_label_parallel(self, full_df: pd.DataFrame, label: str):
        """並列処理用の各ラベルのデータ処理関数"""
        print(f"{label}の処理開始:")
        
        # ラベルでフィルタリング
        label_df = full_df[full_df["bert_label"] == label].copy()
        print(f"{label}カテゴリのデータ数: {len(label_df)}行")
        
        # 最大サンプル数をランダムサンプリング
        if len(label_df) > self.samples_per_label:
            sampled_df = label_df.sample(n=self.samples_per_label)
            print(f"{label}: {self.samples_per_label}件をランダムサンプリングしました")
        else:
            sampled_df = label_df
            print(f"{label}: データ数が{self.samples_per_label}件未満のため、全件使用します")
        
        # 3秒以上の音声ファイルのみを抽出
        filtered_data = self._copy_audio_files(sampled_df, label)
        
        # フィルタリング済みデータをCSVに保存
        output_file = self.output_dir / f"{label}_filtered.csv"
        filtered_data.to_csv(output_file, index=False, encoding='utf-8')
        print(f"{label}: CSVデータを保存: {output_file}")
        
        return filtered_data

    def _get_audio_duration(self, file_path):
        """音声ファイルの長さ（秒）を取得"""
        try:
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000.0  # ミリ秒から秒に変換
        except Exception:
            return 0  # エラーの場合は0を返す

    def _process_single_file(self, args):
        """単一ファイルの処理（並列処理用）"""
        idx, row, audio_output_dir, label = args
        src_path = Path(row['FilePath'])
        dst_path = audio_output_dir / src_path.name
        
        try:
            # 音声ファイルの長さを確認
            duration = self._get_audio_duration(src_path)
            if duration < 3.0:  # 3秒未満の場合はスキップ
                return None, "short"
            
            # 3秒以上の場合はコピー
            shutil.copy2(src_path, dst_path)
            return idx, "success"
        except Exception:
            return None, "error"

    def _copy_audio_files(self, df: pd.DataFrame, label: str):
        """音声ファイルのコピー処理（3秒以上のファイルのみ）を並列実行"""
        audio_output_dir = self.raw_dir / label
        
        # 処理対象のファイルパラメータを準備
        file_params = [
            (idx, row, audio_output_dir, label) 
            for idx, row in df.iterrows()
        ]
        
        # カウンタの初期化
        success_count = error_count = skipped_count = 0
        valid_indices = []
        
        # 進捗バー付きで並列処理
        print(f"{label}のファイルを処理中...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(tqdm(
                executor.map(self._process_single_file, file_params),
                total=len(file_params),
                desc=f"{label}処理"
            ))
        
        # 結果を集計
        for idx, status in results:
            if status == "success":
                success_count += 1
                valid_indices.append(idx)
            elif status == "short":
                skipped_count += 1
            elif status == "error":
                error_count += 1
        
        print(f"{label}の音声ファイルコピー結果:")
        print(f"成功: {success_count}件, スキップ(3秒未満): {skipped_count}件, エラー: {error_count}件")
        
        # 3秒以上の音声ファイルのみのデータフレームを返す
        return df.loc[valid_indices].copy() if valid_indices else pd.DataFrame()

    def create_esd_list(self, data: pd.DataFrame):
        """ESDリストファイルの作成（ラベルごとに分割）"""
        # 並列処理でESDリストを作成
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.labels)) as executor:
            futures = []
            for label in self.labels:
                futures.append(
                    executor.submit(self._create_single_esd_list, data, label)
                )
            
            # 全てのタスク完了を待機
            for future in concurrent.futures.as_completed(futures):
                try:
                    label, count = future.result()
                    print(f"\nESDリスト({label})を作成しました")
                    print(f"エントリー数: {count}件")
                except Exception as e:
                    print(f"ESDリスト作成中にエラーが発生しました: {str(e)}")

    def _create_single_esd_list(self, data: pd.DataFrame, label: str):
        """単一ラベルのESDリスト作成（並列処理用）"""
        # ラベルごとにデータをフィルタリング
        label_data = data[data['bert_label'] == label]
        esd_list_path = self.output_dir / f"esd_{label}.list"
        
        with open(esd_list_path, "w", encoding="utf-8") as f:
            for _, row in label_data.iterrows():
                base_name = f"{label}\{Path(row['FilePath']).stem}.wav"
                speaker = row.get('Speaker', 'Unknown')
                text = row.get('Text', '')
                f.write(f"{base_name}|{speaker}|JP|{text}\n")
        
        return label, len(label_data)

def main():
    # 設定
    BASE_DIR = r"F:"
    INPUT_CSV = r"F:\Galgame_Dataset\data_.csv"
    
    try:
        # メモリキャッシュを最大化するための環境変数設定
        os.environ['MALLOC_TRIM_THRESHOLD_'] = '65536'
        
        processor = DatasetProcessor(BASE_DIR)
        processor.setup_directories()
        processor.filter_and_classify_data(INPUT_CSV)
        print("\n全ての処理が完了しました！")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    # プロセス起動時の最適化
    multiprocessing.set_start_method('spawn', force=True)
    main()