from scipy.io import wavfile
import noisereduce as nr
# load data
rate, data = wavfile.read("/Users/zack/ECE5730/microcontrollers/wav-fixed/sharp-sweep_5_9_corrected.wav")
# perform noise reduction
reduced_noise = nr.reduce_noise(y=data, sr=rate)
wavfile.write("mywav_reduced_noise.wav", rate, reduced_noise)
