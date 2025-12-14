import os
import threading
import tkinter as tk
import queue
from datetime import timedelta, datetime

import torch.cuda
from pydub import AudioSegment
import ffmpeg
from tkinter import filedialog, messagebox
from funasr import AutoModel
import psutil

spk_txt_queue = queue.Queue()

# 创建窗口
root = tk.Tk()
root.title("说话人分离 https://blog.lukeewin.top")

# 获取屏幕宽度和高度
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# 设置窗口大小
window_width = 400
window_height = 200

# 计算居中位置
x_coordinate = (screen_width // 2) - (window_width // 2)
y_coordinate = (screen_height // 2) - (window_height // 2)

# 设置窗口大小和位置
root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

home_directory = os.path.expanduser("~")
asr_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "models", "iic", "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
asr_model_revision = "v2.0.4"
vad_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "models", "iic", "speech_fsmn_vad_zh-cn-16k-common-pytorch")
vad_model_revision = "v2.0.4"
punc_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "models", "iic", "punc_ct-transformer_zh-cn-common-vocab272727-pytorch")
punc_model_revision = "v2.0.4"
spk_model_path = os.path.join(home_directory, ".cache", "modelscope", "hub", "models", "iic", "speech_campplus_sv_zh-cn_16k-common")
spk_model_revision = "v2.0.4"
hotword_file = "./hotwords.txt"
ngpu = 1 if torch.cuda.is_available() else 0
ncpu = psutil.cpu_count()

# ASR 模型
model = AutoModel(model=asr_model_path,
                  model_revision=asr_model_revision,
                  vad_model=vad_model_path,
                  vad_model_revision=vad_model_revision,
                  punc_model=punc_model_path,
                  punc_model_revision=punc_model_revision,
                  spk_model=spk_model_path,
                  spk_model_revision = spk_model_revision,
                  ngpu=ngpu,
                  ncpu=ncpu,
                  disable_pbar=True,
                  disable_log=True,
                  disable_update=True
                  )

# 创建一个队列，用于线程间通信
result_queue = queue.Queue()
# 音频合并队列
audio_concat_queue = queue.Queue()

# 支持的音视频格式
support_audio_format = ['.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.aif']
support_video_format = ['.mp4', '.avi', '.mov', '.mkv']

hotwords = ''
if hotword_file is not None and os.path.exists(hotword_file):
    with open(hotword_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        lines = [line.strip() for line in lines]
    hotwords = " ".join(lines)
    print(f"热词：{hotwords}")

input_frame = tk.Frame(root)
input_frame.pack(side=tk.TOP, padx=10, pady=2)
output_frame = tk.Frame(root)
output_frame.pack(side=tk.TOP, padx=10, pady=2)
start_trans_frame = tk.Frame(root)
start_trans_frame.pack(side=tk.TOP, padx=10, pady=2)
show_frame = tk.Frame(root)
show_frame.pack(side=tk.TOP,padx=10, pady=2)

selected_file_list = []
# 选择需要分离的音频
def select_multi_file():
    selected_file_list.clear()
    selected_files = filedialog.askopenfilenames(title='选择多个文件', filetypes=[('音频文件', '*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.aif *.wma'), ('视频文件', '*.mp4 *.avi *.mov *.mkv')])
    selected_file_count = len(selected_files)
    for tmp_file in selected_files:
        selected_file_list.append(tmp_file)
        print(f"选择的音频或视频：{tmp_file}")
    show_input_info.config(text=f"已选择 {selected_file_count} 个文件")
select_input_file_button = tk.Button(input_frame, text='选择音视频', command=select_multi_file)
select_input_file_button.pack(side=tk.LEFT, padx=10, pady=2)
show_input_info = tk.Label(input_frame, text='')
show_input_info.pack(side=tk.LEFT, padx=10, pady=2)

# 指定转写后的保存路径
output_label = tk.Label(output_frame, text="保存路径")
output_label.pack(side=tk.LEFT, padx=10, pady=2)

save_path = tk.StringVar(None)
# 指定保存路径
def save_dir():
    save_directory = filedialog.askdirectory(title='选择保存路径')
    if save_directory:
        save_path.set(save_directory)
        output_label.config(text=save_directory)
tk.Button(output_frame, text='选择保存目录', command=save_dir).pack(side=tk.LEFT, padx=10, pady=2)

def copy_output_path():
    # 获取label中的文本内容
    text_to_copy = output_label.cget("text")
    # 清空剪贴板
    root.clipboard_clear()
    # 将文本内容添加到剪贴板
    root.clipboard_append(text_to_copy)

# 复制
copy_button = tk.Button(output_frame, text="复制路径", command=copy_output_path)
copy_button.pack(side=tk.RIGHT, padx=10, pady=2)

# 分离字数
label_split = tk.Label(start_trans_frame, text="合并相邻相同讲话人阈值")
label_split.pack(side=tk.LEFT, padx=5, pady=2)
split_number = tk.Entry(start_trans_frame, width=2)
split_number.insert(0, str(10))
split_number.pack(side=tk.LEFT, padx=5, pady=2)

def to_date(milliseconds):
    """将时间戳转换为SRT格式的时间"""
    time_obj = timedelta(milliseconds=milliseconds)
    return f"{time_obj.seconds // 3600:02d}:{(time_obj.seconds // 60) % 60:02d}:{time_obj.seconds % 60:02d}.{time_obj.microseconds // 1000:03d}"


def to_milliseconds(time_str):
    time_obj = datetime.strptime(time_str, "%H:%M:%S.%f")
    time_delta = time_obj - datetime(1900, 1, 1)
    milliseconds = int(time_delta.total_seconds() * 1000)
    return milliseconds

# 转写获取时间戳，根据时间戳进行切分，然后根据 spk id 进行分类
# audio: 音频
# return 切分后按照 spk id 的地址
def trans():
    if len(selected_file_list) != 0 and save_path.get() != '' and save_path.get() is not None:
        for audio in selected_file_list:
            if os.path.exists(audio):
                audio_name = os.path.splitext(os.path.basename(audio))[0]
                _, audio_extension = os.path.splitext(audio)
                show_info_label.config(text=f'正在执行中，请勿关闭程序。{audio}')
                speaker_audios = {}  # 每个说话人作为 key，value 为列表，列表中为当前说话人对应的每个音频片段
                # 音频预处理
                try:
                    audio_bytes, _ = (
                        ffmpeg.input(audio, threads=0, hwaccel='cuda')
                        .output("-", format="wav", acodec="pcm_s16le", ac=1, ar=16000)
                        .run(cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
                    )
                    res = model.generate(input=audio_bytes, batch_size_s=300, is_final=True, sentence_timestamp=True, hotword=hotwords)
                    rec_result = res[0]
                    asr_result_text = rec_result['text']
                    if asr_result_text != '':
                        sentences = []
                        for sentence in rec_result["sentence_info"]:
                            start = to_date(sentence["start"])
                            end = to_date(sentence["end"])
                            if sentences and sentence["spk"] == sentences[-1]["spk"] and len(sentences[-1]["text"]) < int(split_number.get()):
                                sentences[-1]["text"] += "" + sentence["text"]
                                sentences[-1]["end"] = end
                            else:
                                sentences.append(
                                    {"text": sentence["text"], "start": start, "end": end, "spk": sentence["spk"]}
                                )

                        # 剪切音频或视频片段
                        i = 0
                        for stn in sentences:
                            stn_txt = stn['text']
                            start = stn['start']
                            end = stn['end']
                            # tmp_start = to_milliseconds(start)
                            # tmp_end = to_milliseconds(end)
                            # duration = round((tmp_end - tmp_start) / 1000, 3)
                            spk = stn['spk']

                            # 根据文件名和 spk 创建目录
                            date = datetime.now().strftime("%Y-%m-%d")
                            final_save_path = os.path.join(save_path.get(), date, audio_name, str(spk))
                            os.makedirs(final_save_path, exist_ok=True)
                            # 获取音视频后缀
                            file_ext = os.path.splitext(audio)[-1]
                            final_save_file = os.path.join(final_save_path, str(i)+file_ext)
                            spk_txt_path = os.path.join(save_path.get(), date, audio_name)
                            spk_txt_file = os.path.join(spk_txt_path, f'spk{spk}.txt')
                            spk_txt_queue.put({'spk_txt_file': spk_txt_file, 'spk_txt': stn_txt, 'start': start, 'end': end})
                            i += 1
                            try:
                                if file_ext in support_audio_format:
                                    (
                                        ffmpeg.input(audio, threads=0, ss=start, to=end, hwaccel='cuda')
                                        .output(final_save_file)
                                        .run(cmd=["ffmpeg", "-nostdin"], overwrite_output=True, capture_stdout=True,
                                             capture_stderr=True)
                                    )
                                elif file_ext in support_video_format:
                                    final_save_file = os.path.join(final_save_path, str(i)+'.mp4')
                                    (
                                        ffmpeg.input(audio, threads=0, ss=start, to=end, hwaccel='cuda')
                                        .output(final_save_file, vcodec='libx264', crf=23, acodec='aac', ab='128k')
                                        .run(cmd=["ffmpeg", "-nostdin"], overwrite_output=True, capture_stdout=True,
                                             capture_stderr=True)
                                    )
                                else:
                                    print(f'{audio}不支持')
                            except ffmpeg.Error as e:
                                print(f"剪切音频发生错误，错误信息：{e}")
                            # 记录说话人和对应的音频片段，用于合并音频片段
                            if spk not in speaker_audios:
                                speaker_audios[spk] = []  # 列表中存储音频片段
                            speaker_audios[spk].append({'file': final_save_file, 'audio_name': audio_name})
                        ret = {"text": asr_result_text, "sentences": sentences}
                        print(f'{audio} 切分完成')
                        result_queue.put(f'{audio} 切分完成')
                        show_info_label.config(text=f'{audio} 切分完成')
                        print(f'转写结果：{ret}')
                        # 存入合并队列
                        audio_concat_queue.put(speaker_audios)
                    else:
                        print("没有转写结果")
                except Exception as e:
                    print(f"转写异常：{e}")
            else:
                print("输入的文件不存在")
                messagebox.showinfo("提醒", "输入的文件不存在")
    else:
        print("没有填写输入输出")
        messagebox.showinfo("提醒", "没有填写选择文件或保存路径")


def start_transcription_thread():
    # 创建并启动转写线程
    thread = threading.Thread(target=trans)
    thread.start()


btn_start = tk.Button(start_trans_frame, text="分离", command=start_transcription_thread)
btn_start.pack(side=tk.LEFT, padx=10, pady=2)

# 显示分离情况
show_info_label = tk.Label(show_frame, text="")
show_info_label.pack(side=tk.LEFT, padx=10, pady=2)


def show_info():
    res = result_queue.get()
    show_info_label.config(text=res)


threading.Thread(target=show_info).start()


def write_txt():
    while True:
        item = spk_txt_queue.get()
        spk_txt_file = item['spk_txt_file']
        spk_txt = item['spk_txt']
        spk_start = item['start']
        spk_end = item['end']
        dir_path = os.path.dirname(spk_txt_file)
        os.makedirs(dir_path, exist_ok=True)
        with open(spk_txt_file, 'a', encoding='utf-8') as f:
            f.write(f"{spk_start} --> {spk_end}\n{spk_txt}\n\n")


threading.Thread(target=write_txt).start()


def audio_concat_worker():
    while True:
        speaker_audios_tmp = audio_concat_queue.get()
        for spk, audio_segments in speaker_audios_tmp.items():
            # 合并每个说话人的音频片段
            audio_name = audio_segments[0]['audio_name']
            output_file = os.path.join(save_path.get(), datetime.now().strftime("%Y-%m-%d"), audio_name, f"{spk}.mp3")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            inputs = [seg['file'] for seg in audio_segments]
            concat_audio = AudioSegment.from_file(inputs[0])
            for i in range(1, len(inputs)):
                concat_audio = concat_audio + AudioSegment.from_file(inputs[i])
            concat_audio.export(output_file, format="mp3")
            print(f"已将 {spk} 的音频合并到 {output_file}")
        audio_concat_queue.task_done()


# 创建一个线程用于消费音频合并队列中的内容
audio_concat_thread = threading.Thread(target=audio_concat_worker)
audio_concat_thread.daemon = True
audio_concat_thread.start()


if __name__ in '__main__':
    print("项目源码：https://github.com/lukeewin/AudioSeparationGUI")
    root.mainloop()
