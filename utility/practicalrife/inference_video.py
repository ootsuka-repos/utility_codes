import os
import cv2
import torch
import argparse
import numpy as np
from tqdm import tqdm
from torch.nn import functional as F
import warnings
import _thread
import skvideo.io
from queue import Queue
from model.pytorch_msssim import ssim_matlab
import shutil
import gradio as gr

warnings.filterwarnings("ignore")

def transferAudio(sourceVideo, targetVideo):
    tempAudioFileName = "./temp/audio.mkv"

    # clear old "temp" directory if it exits
    if os.path.isdir("temp"):
        shutil.rmtree("temp")
    os.makedirs("temp")

    # extract audio from video
    os.system(f'ffmpeg -y -i "{sourceVideo}" -c:a copy -vn {tempAudioFileName}')

    targetNoAudio = os.path.splitext(targetVideo)[0] + "_noaudio" + os.path.splitext(targetVideo)[1]
    os.rename(targetVideo, targetNoAudio)

    # combine audio file and new video file
    os.system(f'ffmpeg -y -i "{targetNoAudio}" -i {tempAudioFileName} -c copy "{targetVideo}"')

    if os.path.getsize(targetVideo) == 0:
        tempAudioFileName = "./temp/audio.m4a"
        os.system(f'ffmpeg -y -i "{sourceVideo}" -c:a aac -b:a 160k -vn {tempAudioFileName}')
        os.system(f'ffmpeg -y -i "{targetNoAudio}" -i {tempAudioFileName} -c copy "{targetVideo}"')
        if os.path.getsize(targetVideo) == 0:
            os.rename(targetNoAudio, targetVideo)
            print("Audio transfer failed. Interpolated video will have no audio")
        else:
            print("Lossless audio transfer failed. Audio was transcoded to AAC (M4A) instead.")
            os.remove(targetNoAudio)
    else:
        os.remove(targetNoAudio)

    shutil.rmtree("temp")

def interpolate_video(video_path, multi):
    args = argparse.Namespace(
        video=video_path,
        output=None,
        modelDir='train_log',
        fp16=False,
        UHD=False,
        scale=1.0,
        fps=None,
        png=False,
        ext='mp4',
        exp=1,
        multi=multi
    )

    if args.exp != 1:
        args.multi = (2 ** args.exp)
    assert (not args.video is None)
    if args.UHD and args.scale == 1.0:
        args.scale = 0.5
    assert args.scale in [0.25, 0.5, 1.0, 2.0, 4.0]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_grad_enabled(False)
    if torch.cuda.is_available():
        torch.backends.cudnn.enabled = True
        torch.backends.cudnn.benchmark = True
        if(args.fp16):
            torch.set_default_tensor_type(torch.cuda.HalfTensor)

    from train_log.RIFE_HDv3 import Model
    model = Model()
    if not hasattr(model, 'version'):
        model.version = 0
    model.load_model(args.modelDir, -1)
    print("Loaded 3.x/4.x HD model.")
    model.eval()
    model.device()

    videoCapture = cv2.VideoCapture(args.video)
    fps = videoCapture.get(cv2.CAP_PROP_FPS)
    tot_frame = videoCapture.get(cv2.CAP_PROP_FRAME_COUNT)
    videoCapture.release()
    if args.fps is None:
        fpsNotAssigned = True
        args.fps = fps * args.multi
    else:
        fpsNotAssigned = False
    videogen = skvideo.io.vreader(args.video)
    lastframe = next(videogen)
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    video_path_wo_ext, ext = os.path.splitext(args.video)
    print(f'{video_path_wo_ext}.{args.ext}, {tot_frame} frames in total, {fps}FPS to {args.fps}FPS')
    if args.png == False and fpsNotAssigned == True:
        print("The audio will be merged after interpolation process")
    else:
        print("Will not merge audio because using png or fps flag!")

    h, w, _ = lastframe.shape
    vid_out_name = f'{video_path_wo_ext}_{args.multi}X_{int(np.round(args.fps))}fps.{args.ext}'
    vid_out = cv2.VideoWriter(vid_out_name, fourcc, args.fps, (w, h))

    def clear_write_buffer(user_args, write_buffer):
        cnt = 0
        while True:
            item = write_buffer.get()
            if item is None:
                break
            vid_out.write(item[:, :, ::-1])

    def build_read_buffer(user_args, read_buffer, videogen):
        try:
            for frame in videogen:
                read_buffer.put(frame)
        except:
            pass
        read_buffer.put(None)

    def make_inference(I0, I1, n, model):    
        if model.version >= 3.9:
            res = []
            for i in range(n):
                res.append(model.inference(I0, I1, (i+1) * 1. / (n+1), args.scale))
            return res
        else:
            middle = model.inference(I0, I1, args.scale)
            if n == 1:
                return [middle]
            first_half = make_inference(I0, middle, n=n//2, model=model)
            second_half = make_inference(middle, I1, n=n//2, model=model)
            if n%2:
                return [*first_half, middle, *second_half]
            else:
                return [*first_half, *second_half]

    def pad_image(img):
        if(args.fp16):
            return F.pad(img, padding).half()
        else:
            return F.pad(img, padding)

    tmp = max(128, int(128 / args.scale))
    ph = ((h - 1) // tmp + 1) * tmp
    pw = ((w - 1) // tmp + 1) * tmp
    padding = (0, pw - w, 0, ph - h)
    pbar = tqdm(total=tot_frame)
    write_buffer = Queue(maxsize=500)
    read_buffer = Queue(maxsize=500)
    _thread.start_new_thread(build_read_buffer, (args, read_buffer, videogen))
    _thread.start_new_thread(clear_write_buffer, (args, write_buffer))

    I1 = torch.from_numpy(np.transpose(lastframe, (2,0,1))).to(device, non_blocking=True).unsqueeze(0).float() / 255.
    I1 = pad_image(I1)
    temp = None

    while True:
        if temp is not None:
            frame = temp
            temp = None
        else:
            frame = read_buffer.get()
        if frame is None:
            break
        I0 = I1
        I1 = torch.from_numpy(np.transpose(frame, (2,0,1))).to(device, non_blocking=True).unsqueeze(0).float() / 255.
        I1 = pad_image(I1)
        I0_small = F.interpolate(I0, (32, 32), mode='bilinear', align_corners=False)
        I1_small = F.interpolate(I1, (32, 32), mode='bilinear', align_corners=False)
        ssim = ssim_matlab(I0_small[:, :3], I1_small[:, :3])

        break_flag = False
        if ssim > 0.996:
            frame = read_buffer.get()
            if frame is None:
                break_flag = True
                frame = lastframe
            else:
                temp = frame
            I1 = torch.from_numpy(np.transpose(frame, (2,0,1))).to(device, non_blocking=True).unsqueeze(0).float() / 255.
            I1 = pad_image(I1)
            I1 = model.inference(I0, I1, scale=args.scale)
            I1_small = F.interpolate(I1, (32, 32), mode='bilinear', align_corners=False)
            ssim = ssim_matlab(I0_small[:, :3], I1_small[:, :3])
            frame = (I1[0] * 255).byte().cpu().numpy().transpose(1, 2, 0)[:h, :w]
            
        if ssim < 0.2:
            output = []
            for i in range(args.multi - 1):
                output.append(I0)
        else:
            output = make_inference(I0, I1, args.multi - 1, model)

        write_buffer.put(lastframe)
        for mid in output:
            mid = (((mid[0] * 255.).byte().cpu().numpy().transpose(1, 2, 0)))
            write_buffer.put(mid[:h, :w])
        pbar.update(1)
        lastframe = frame
        if break_flag:
            break

    write_buffer.put(lastframe)
    write_buffer.put(None)

    import time
    while(not write_buffer.empty()):
        time.sleep(0.1)
    pbar.close()
    vid_out.release()

    if args.png == False and fpsNotAssigned == True and not args.video is None:
        try:
            transferAudio(args.video, vid_out_name)
        except:
            print("Audio transfer failed. Interpolated video will have no audio")
            targetNoAudio = os.path.splitext(vid_out_name)[0] + "_noaudio" + os.path.splitext(vid_out_name)[1]
            os.rename(targetNoAudio, vid_out_name)

    return vid_out_name

# Gradio UI
inputs = [
    gr.components.Video(label="元動画"),
    gr.components.Number(label="FPSを何倍にするか", value=8)
]

output = gr.components.Video(label="Output Video")

gr.Interface(fn=interpolate_video, inputs=inputs, outputs=output, title="Video Interpolation").launch()