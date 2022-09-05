from email import message
import websocket
import wave
import serial
import numpy as np
import datetime
import hashlib
import base64
import hmac
import json
import speech_recognition as sr
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread

STATUS_FIRST_FRAME = 0  # first frame
STATUS_CONTINUE_FRAME = 1  # mid frame
STATUS_LAST_FRAME = 2  # last frame

command = ""
serialName = "COM3"
baudRate=9600


class Ws_Param(object):
    # Initialization
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        # common parameter
        self.CommonArgs = {"app_id": self.APPID}
        # business parameter
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo":1,"vad_eos":10000}

    # forming url
    def create_url(self):
        url = 'wss://ws-api.xfyun.cn/v2/iat'
        # forming timestamp, format: RFC1123
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        # hmac-sha256 encryption
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # Combine the authentication parameters of the request into a dictionary
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # Concatenate authentication parameters to generate urls
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # print('websocket url :', url)
        return url


# Process the message received from websocket
def on_message(ws, message):
    global command
    try:
        code = json.loads(message)["code"]
        sid = json.loads(message)["sid"]
        if code != 0:
            errMsg = json.loads(message)["message"]
            print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))

        else:
            data = json.loads(message)["data"]["result"]["ws"]
            # print(json.loads(message))
            result = ""
            for i in data:
                for w in i["cw"]:
                    result += w["w"]
            print("Parsing success! Your said:%s" %result)
            if result != "." and result != "。":
                command = result.strip()
    except Exception as e:
        print("receive msg,but parse exception:", e)



# websocket error
def on_error(ws, error):
    print("### error:", error)


# websocket normal close
def on_close(ws):
    print("### closed ###")


# websocket connection building
def on_open(ws):
    def run(*args):
        frameSize = 8000  # audio size of each frame
        intervel = 0.04  # audio transmission interval(unit:second)
        status = STATUS_FIRST_FRAME  # The state of the audio, identifying whether the audio is the first frame, the middle frame, or the last frame

        with open(wsParam.AudioFile, "rb") as fp:
            while True:
                buf = fp.read(frameSize)
                if not buf:
                    status = STATUS_LAST_FRAME
                # Deal with first frame
                # send the audio of first frame with business parameter
                # appid must be attached
                if status == STATUS_FIRST_FRAME:

                    d = {"common": wsParam.CommonArgs,
                         "business": wsParam.BusinessArgs,
                         "data": {"status": 0, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    d = json.dumps(d)
                    ws.send(d)
                    status = STATUS_CONTINUE_FRAME
                # Deal with mid frame
                elif status == STATUS_CONTINUE_FRAME:
                    d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                # Deal with last frame
                elif status == STATUS_LAST_FRAME:
                    d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                    time.sleep(1)
                    break
                # imitate audio sampling interval
                time.sleep(intervel)
        ws.close()

    thread.start_new_thread(run, ())

def wav2pcm(wavfile, pcmfile, data_type=np.int16):
    f = open(wavfile, "rb")
    f.seek(0)
    f.read(44)
    data = np.fromfile(f, dtype= data_type)
    data.tofile(pcmfile)

def pcm2wav(pcm_file, wav_file, channels=1, bits=16, sample_rate=16000):
    pcmf = open(pcm_file, 'rb')
    pcmdata = pcmf.read()
    pcmf.close()

    if bits % 8 != 0:
        raise ValueError("bits % 8 must == 0. now bits:" + str(bits))

    wavfile = wave.open(wav_file, 'wb')
    wavfile.setnchannels(channels)
    wavfile.setsampwidth(bits // 8)
    wavfile.setframerate(sample_rate)
    wavfile.writeframes(pcmdata)
    wavfile.close()

# Use SpeechRecognition to record voice command
def my_record(rate=16000):
    r = sr.Recognizer()
    with sr.Microphone(sample_rate=rate) as source:
        print("************\nplease say something:")
        audio = r.listen(source)
 
    with open("./code/voice/test.wav", "wb") as f:
        f.write(audio.get_wav_data())
    print("Successfully recorded!\n************")
 
if __name__ == "__main__":
    # pcm2wav("./code/iat_pcm_16k.pcm", "./code/iat_pcm_16k.wav")
    print("Start connecting bluetooth module...")
    port="COM5" #This will be different for various devices
    bluetooth=serial.Serial(port, 9600)#Start communications with the bluetooth unit
    print("Bluetooth module connected!")
    bluetooth.flushInput() #This gives the bluetooth a little kick

    # test_count = 0
    # while(test_count<10):
    #     test_count += 1
    while(1):
        my_record()
        wav2pcm("./code/voice/test.wav","./code/voice/test.pcm")
        # time1 = datetime.now()
        wsParam = Ws_Param(APPID='25a33629', APISecret='ZjVmZGJhMTBlZGVmNWM4ZDFkZDRjZDEz',
                        APIKey='5d6e295d396b59727bf45035c4e05cbc',
                        AudioFile=r'./code/voice/test.pcm')
        websocket.enableTrace(False)
        wsUrl = wsParam.create_url()
        ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
        ws.on_open = on_open
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        # time2 = datetime.now()

        # open & “开” 
        if command == "Open" or command == "开":
            print("************\nCommand: open\nFan action:")
            bluetooth.write(str.encode("on"))
            time.sleep(1)
            input_data=bluetooth.readline() #This reads the incoming data.
            time.sleep(0.5)
            print(input_data.decode())      #These are bytes coming in so a decode is needed
            time.sleep(0.5)                 #A pause between bursts

        # close & "关” 
        if command == "Close" or command == "关":
            print("************\nCommand: close\nFan action:")
            bluetooth.write(str.encode("off"))
            time.sleep(1)
            input_data=bluetooth.readline() #This reads the incoming data.
            time.sleep(0.5)
            print(input_data.decode())      #These are bytes coming in so a decode is needed
            time.sleep(0.5)                 #A pause between bursts

        # up & "加速” 
        if command == "Up" or command == "加速" or command == "Speed up":
            print("************\nCommand: speed up\nFan action:")
            bluetooth.write(str.encode("up"))
            time.sleep(1)
            input_data=bluetooth.readline() #This reads the incoming data.
            time.sleep(0.5)
            print(input_data.decode())      #These are bytes coming in so a decode is needed
            time.sleep(0.5)                 #A pause between bursts

        # down & "减速”
        if command == "Down" or command == "减速" or command == "Slow down":
            print("************\nCommand: slow down\nFan action:")
            bluetooth.write(str.encode("down"))
            time.sleep(1)
            input_data=bluetooth.readline() #This reads the incoming data.
            time.sleep(0.5)
            print(input_data.decode())      #These are bytes coming in so a decode is needed
            time.sleep(0.5)                 #A pause between bursts

    time.sleep(0.5)
    bluetooth.close()
    print("Done")


