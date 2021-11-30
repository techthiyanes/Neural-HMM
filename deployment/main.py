import streamlit as st

import torch
import sys
import numpy as np
import torch
import matplotlib.pyplot as plt
from nltk import word_tokenize
import warnings

import os
if os.getcwd().split('/')[-1] == 'deployment':
    os.chdir('../')

import nltk
nltk.download('punkt')

sys.path.append('src/model')
sys.path.append('waveglow/')

from src.hparams import create_hparams
from src.training_module import TrainingModule
from src.utilities.text import text_to_sequence, phonetise_text
from waveglow.denoiser import Denoiser
import pydub
import soundfile
from scipy.io.wavfile import write
from PIL import Image

#===========================================#
#                Configs                    #
#===========================================#

title = 'Neural HMM'
image = Image.open('deployment/NeuralHMMTTS.png')
desc = "Generate audio with the Neural HMM, more information available at https://shivammehta007.github.io/Neural-HMM/"


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
checkpoint_path = "neur-hmm.ckpt"
waveglow_path = "waveglow_256channels_universal_v5.pt"


#===========================================#
#        Loads Model and Pipeline           #
#===========================================#


### Load Waveglow Vocoder

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    waveglow = torch.load(waveglow_path)['model']
    waveglow.to(device).eval()
    for k in waveglow.convinv:
        k.float()
    denoiser = Denoiser(waveglow)


hparams = create_hparams()

### Load Neural-HMM
def load_model(checkpoint_path):
    model = TrainingModule.load_from_checkpoint(checkpoint_path)
    _ = model.to(device).eval()
    return model

model = load_model(checkpoint_path)

### Phonetising
def prepare_text(text):
    text = phonetise_text(hparams.cmu_phonetiser, text, word_tokenize)
    sequence = np.array(text_to_sequence(text, ['english_cleaners']))[None, :]
    sequence = torch.from_numpy(sequence).to(device).long()
    return sequence


### Plotting mel
def plot_spectrogram_to_numpy(spectrogram):

    fig.canvas.draw()
    plt.close()
    return fig

#===========================================#
#              Streamlit Code               #
#===========================================#


st.title(title)
st.write(desc)
st.image(image, caption='Neural HMM Architecture')

user_input = st.text_input('Text to generate')
if st.button('Generate Audio'):
    with torch.no_grad():
        # model.model.hmm.hparams.duration_quantile_threshold= 1 - speaking_rate
        text = prepare_text(user_input)
        mel_output, _ = model.inference(text)
        mel_output = torch.tensor(mel_output).T.unsqueeze(0).cuda()
        audio = waveglow.infer(mel_output, sigma=0.666)
        audio_denoised = denoiser(audio, strength=0.01)[:, 0].cpu().numpy()

    # import pdb; pdb.set_trace()

    sample_rate = 22050
    print(audio_denoised.shape)
    print(mel_output.shape)
    # audio_segment = pydub.AudioSegment(
    #     audio_denoised.tobytes(), 
    #     sample_width=audio_denoised.dtype.itemsize, 
    #     frame_ratsample_e=rate,
    #     channels=1
    # )_


    spectrogram = mel_output.cpu().numpy()[0]
    fig, ax = plt.subplots(figsize=(12, 3))
    im = ax.imshow(spectrogram, aspect="auto", origin="lower",
                   interpolation='none')
    plt.colorbar(im, ax=ax)
    plt.xlabel("Frames")
    plt.ylabel("Channels")
    plt.title("Synthesised Mel-Spectrogram")
    st.pyplot(fig)

    soundfile.write('temp.wav', audio_denoised.T, sample_rate)
    st.audio('temp.wav', format='audio/wav')

    # write('temp.wav', sample_rate, audio_denoised)
    # with open('temp.wav', 'rb') as f:
    #     st.aud:_io(f.read(), format='audio/wav')

    # st.audio('temp.wav', format='audio/wav')
