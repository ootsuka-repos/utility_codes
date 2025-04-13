import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
import time

def main():
    # 入出力ファイルの設定
    input_file = r"F:\all_dialogues.csv"
    output_dir = os.path.dirname(input_file)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"galgame_dataset_classified_{timestamp}.csv")
    
    # CSVファイルの読み込み
    print(f"CSVファイルを読み込んでいます: {input_file}")
    df = pd.read_csv(input_file)
    
    # テキストカラムの確認
    text_column = 'Text'  # CSVのテキスト列名に合わせて変更
    if text_column not in df.columns:
        print(f"警告: '{text_column}'列が見つかりません。列名: {df.columns.tolist()}")
        text_column = input("テキストが含まれる列名を入力してください: ")
    
    # BERTモデルを1回だけロード
    print(f"BERTモデルをロードしています... (デバイス: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')})")
    model_path = "swdq/modernbert-ja-310m-nsfw"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    # ラベル辞書
    label_dict = {"usual": 0, "aegi": 1, "chupa": 2}
    reverse_label_dict = {v: k for k, v in label_dict.items()}
    
    # 結果列の初期化
    df['bert_label'] = ''
    
    # バッチサイズの設定
    batch_size = 2000
    total_rows = len(df)
    
    print("テキスト分類を実行しています...")
    for i in range(0, total_rows, batch_size):
        batch_end = min(i + batch_size, total_rows)
        if i % 1 == 0:
            print(f"処理中: {i}/{total_rows} ({i/total_rows*100:.1f}%)")
        
        # バッチのテキストを取得
        batch_texts = df.iloc[i:batch_end][text_column].tolist()
        # 空のテキストを処理からスキップ
        valid_indices = [j for j, text in enumerate(batch_texts) if isinstance(text, str) and text.strip()]
        valid_texts = [batch_texts[j] for j in valid_indices]
        
        if not valid_texts:
            continue
        
        # バッチでテキスト分類
        inputs = tokenizer(valid_texts, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # 推論
        with torch.no_grad():
            outputs = model(**inputs)
        
        # 確率の計算
        probs = outputs.logits.softmax(dim=-1)
        
        # 結果をデータフレームに追加
        for idx_in_batch, prob in zip(valid_indices, probs):
            actual_idx = i + idx_in_batch
            predicted_class = torch.argmax(prob).item()
            predicted_label = reverse_label_dict[predicted_class]
            df.at[actual_idx, 'bert_label'] = predicted_label
    
    # 結果をCSVに保存
    print(f"結果をCSVに保存しています: {output_file}")
    df.to_csv(output_file, index=False)
    print("処理が完了しました")

if __name__ == "__main__":
    main()