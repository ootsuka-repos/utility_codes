import sys
from clearvoice import ClearVoice

# コマンドライン引数から入力ファイルパスと出力パスを取得
if len(sys.argv) >= 3:
    input_file_path = sys.argv[1]
    output_path = sys.argv[2]
else:
    # デフォルト値（元のハードコードされた値）
    input_file_path = "/home/user/デスクトップ/ClearerVoice-Studio/10大特典付きえっちなバニーがお出迎え癒し処ゆるりらっくす 清純巨乳処女JK 愛園小夜は頑張るあなたに全てを捧げたい_250311081244.wav"
    output_path = '/home/user/デスクトップ/ClearerVoice-Studio/MossFormer2_SE_48K_kekka.wav'

myClearVoice = ClearVoice(task='speech_enhancement', model_names=['MossFormer2_SE_48K'])
output_wav = myClearVoice(input_path=input_file_path, online_write=False)
myClearVoice.write(output_wav, output_path=output_path)