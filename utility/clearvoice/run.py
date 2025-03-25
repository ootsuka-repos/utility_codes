import os
import sys
import subprocess

input_file_path = "/home/user/デスクトップ/ClearerVoice-Studio/test.wav"
output_path = '/home/user/デスクトップ/ClearerVoice-Studio/MossFormer2_SE_48K_kekka.wav'

# 現在のディレクトリのパスを取得
current_dir = os.path.dirname(os.path.abspath(__file__))

def main():
    
    # 環境変数にPYTHONPATHを設定して、モジュールを正しく見つけられるようにする
    my_env = os.environ.copy()
    if 'PYTHONPATH' in my_env:
        my_env['PYTHONPATH'] = f"{current_dir}:{my_env['PYTHONPATH']}"
    else:
        my_env['PYTHONPATH'] = current_dir
    
    # exec.pyのパスとclearvoiceディレクトリのパス
    clearvoice_dir = os.path.join(current_dir, 'clearvoice')
    exec_path = os.path.join(clearvoice_dir, 'exec.py')
    
    # サブプロセスとしてexec.pyを実行（clearvoiceディレクトリで実行）
    print(f"exec.pyを実行します: {exec_path}")
    print(f"入力ファイル: {input_file_path}")
    print(f"出力ファイル: {output_path}")
    
    result = subprocess.run([sys.executable, exec_path, input_file_path, output_path], 
                          cwd=clearvoice_dir,  # clearvoiceディレクトリで実行
                          env=my_env,
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE,
                          text=True)
    
    # 結果を表示
    if result.returncode == 0:
        print("処理が完了しました。")
        print(result.stdout)
    else:
        print("エラーが発生しました：")
        print(result.stderr)

if __name__ == "__main__":
    main()