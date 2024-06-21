# coding: UTF-8
HELP = '''
#==============================================================================#
ラズパイ監視カメラ v2
#==============================================================================#
(C) 2022 Rcat999
Twtter : @Rcat999
YouTube: Rcat999

+--------------概要--------------+
ラズパイを使った監視カメラのVer2
WEBサーバーを使うため、スマホでもPCでも操作可能。


+--------------利用規約--------------+
下記グローバルルールに則ります
 https://sites.google.com/view/rcatglobalrule


+--------------使い方--------------+
OpenCV以外のライブラリをインストール後、同梱のRun.shをルート権限で実行する
OpenCVモード及び、タイムラプスでのMP4変換機能を使いたい場合はOpenCVもインストールする
※ライブラリのインストールについて質問は受けられません


+--------------自動起動の方法--------------+
1.起動用スクリプトのRun.shを適宜書き換える
2.下記セットアップ動画のおまけ(6分以降)を参考に自動起動を設定する
https://youtu.be/PKUM_s1R8rs
3.上記動画の配布データ(スクリプト集)同梱のServiceAdd.shを使用してサービス登録する
登録に使うサービス定義は"KansiCamera.service"。こちらも適宜書き換える


+--------------リンク--------------+
https://drive.google.com/uc?id=1-KciF4zlTl_ShOGJt70cqRCfzqNPNDJC


+--------------必要ライブラリ--------------+
>flask
 WEBサーバーを建てるのに必要
>cryptography
 クッキーを暗号化するのに必要
>psutil
 SDカード残量を照会するのに必要
>picamera
 カメラを扱うのに必要
>ipget
 IPアドレスを取得し、ネットワークが確立したことを確認するのに必要
>cv2
 OpenCV。タイムラプスを動画化するのに必要。
>GPIO_Arduino2
 Rcat999自作モジュール。サーボとGPIOの制御に使われる
>wiringpi
 GPIO_Arduinoで使っているGPIOライブラリ


+--------------履歴--------------+
Ver 1.0.0 2022/05/01 初版
'''
from enum import Flag
import sys,os,re,glob,time,threading,datetime,json,subprocess,psutil,requests
import base64,shutil
#import urllib.parse
from flask import *
from cryptography.fernet import Fernet
import picamera,io
import ipget
from GPIO_Arduino2 import *
OPENCV = True
try:
	import cv2
	#import numpy as np
except:
	print("OpenCVをImportできませんでした")
	OPENCV = False
VERSION = "1.0.0"
LASTDATE = "2022/05/01"
#######################################################################################
# Flaskオブジェクトの生成
app = Flask(__name__)
#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#WEB定型部品#=#=#=#=#=#=#=##=#=#=#=#=#=#=#
#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#よく使う定数
HEADER = {
"chr":'<meta http-equiv="Content-Type" content="text/html;charset=UTF-8">',
"viewport":'<meta name="viewport" content="width=device-width,initial-scale=1.0">'
}
#HTMLフレーム
#title,head,body
HTMLFlame = '<!DOCTYPE html><HTML><HEAD><TITLE>{title}</TITLE>{head}' + HEADER["chr"] + HEADER["viewport"] + '</HEAD><BODY><CENTER>{body}</CENTER></BODY></HTML>'
#title,script,head,body
HTMLFlame2 = '<!DOCTYPE html><HTML><HEAD><TITLE>{title}</TITLE><script>{script}</script>{head}' + HEADER["chr"] + HEADER["viewport"] + '</HEAD><BODY><CENTER>{body}</CENTER></BODY></HTML>'
#url
HTMLFlame_GoURL = HTMLFlame.format(title="move",head='<script>window.location.href = "{0}"</script>',body="")

#ログインページへ飛ばす
ToLoginHTML = HTMLFlame.format(title="ログイン",head='<script>window.location.href = "/login"</script>',body="")

#グローバル変数
Cryptographykey = Fernet.generate_key()
USERS = {"root":"Nekokawaii"} #キーがユーザー名 値がパスワード
SERVERNAME = "RcatCamServer_v2"
CONFIG = {}
CONFIG_FILE = "config.ini"
NOWUPLOADING = False
LIGHTBRIGHT = False
TMPFLAG = False

#カメラ設定
CAM = None
CAMMODE = "picam" #picam , opencv #初回起動時のデフォルト
NowResolution = "800x600"
#Resolutions = ['320x240','640x480','800x600','1024x768','1600x1200','2592x1944','1024x576','1280x720','1920x1080','2560x1440']

#カメラの状態
ANNOTATEUpdateing = False
ANNOTATESIZE = 24
STREAMOUTPUT = None
SHOOTFlag = False
LASHSHOOT = ""
CAMUSEDIMG = None
CAMCHANGEFLAG = False
NOWRECORDINGFILE = "" #録画中のファイル名(終了時に変換に渡せるように)
NOWTIMELAPSEFOLDER = "" #タイムラプスの最新フォルダ
TIMELAPSETIME = 0

#GPIO系
ServoX_Center = 90
ServoY_Center = 90
ServoX_Pin = 12
ServoY_Pin = 13
ServoX_NowAngle = 90
ServoY_NowAngle = 90
ServoX = None
ServoY = None
LIGHTPIN = 17
ShutdownButton = 4

#その他
CONVERTTASK = [] #動画の変換タスク
MAKEFILE = "" #ZIPやMP4の一時データ
#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#ページ宣言域#=#=#=#=#=#=#=##=#=#=#=#=#=#=#
#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#トップ関係
@app.route("/")
def Index():
	return Gethtml("index.html")
#-------------------------------------------------------------------
@app.route("/favicon.ico")
def favicon():
	with open("favicon.ico","rb") as f:
		response = make_response(f.read())
	response.headers["Content-type"] = "Image"
	return response
#-------------------------------------------------------------------
#ログイン関係
@app.route("/login")
def LoginPage():
	if ChkLogin():
		return HTMLFlame.format(title="Login",head='<META http-equiv="Refresh" content="2;URL=/">',body="すでにログイン済みです")
	return Gethtml("Login.html")
@app.route("/DoLogin",methods=["POST"])
def LoginCGI():
	inputuser = request.form["user"]
	if inputuser in USERS:
		if request.form["pass"] == USERS[inputuser]:
			resp = make_response("OK")
			resp.set_cookie(SERVERNAME,Cryptograph(inputuser),max_age=3600*24*30)
			return resp
	return "Fail"
@app.route("/logout")
def LogoutPage():
	if ChkLogin():
		resp = make_response(HTMLFlame.format(title="Logout",head='<META http-equiv="Refresh" content="1;URL=/">',body="ログアウトしました"))
		resp.set_cookie(SERVERNAME,expires=0)
		return resp
	return HTMLFlame.format(title="Logout",head='<META http-equiv="Refresh" content="2;URL=/">',body="ログインしていません")
#-------------------------------------------------------------------
#ファイルアップロード関係
'''
@app.route("/Doupload",methods=['POST'])
def Uploadcgi():
	#if not ChkLogin(): return "Error",511
	if not os.path.isdir("uploadDatas"): os.mkdir("uploadDatas")
	if 'Upload' not in request.files:
		return "Error"
	upload_files = request.files.getlist('Upload')
	for file in upload_files:
		fileName = file.filename
		if fileName == "": continue
		file.save(os.path.join("uploadDatas", fileName))
	return "OK"
'''
#-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+任意ページ記述域+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@app.route("/GetStatus")
def CameraStatusURL():
	if not ChkLogin(): return ToLoginHTML
	NowStatus = {}
	NowStatus["recording"] = CAM.recording
	NowStatus["streaming"] = True if STREAMOUTPUT else False
	NowStatus["resolution"] = NowResolution
	NowStatus["framerate"] = CAM.framerate[0]
	NowStatus["iso"] = CAM.iso
	NowStatus["light"] = LIGHTBRIGHT
	NowStatus["timelapse"] = True if NOWTIMELAPSEFOLDER != "" else False
	NowStatus["timelapsetime"] = TIMELAPSETIME
	NowStatus["hflip"] = CAM.hflip
	NowStatus["vflip"] = CAM.vflip
	NowStatus["cammode"] = CAMMODE
	
	NowStatus["MotionEnable"] = CAM.MotionEnable if CAMMODE == "opencv" else "無効"
	NowStatus["MotionTrigger"] = CAM.MotionTrigger if CAMMODE == "opencv" else "無効"
	NowStatus["MotionRectime"] = CAM.MotionRectime if CAMMODE == "opencv" else "0"
	NowStatus["Motion_Threshold"] = CAM.Motion_Threshold if CAMMODE == "opencv" else "0"
	NowStatus["Motion_Preview"] = CAM.Motion_Preview if CAMMODE == "opencv" else "無効"

	resp = make_response(json.dumps(NowStatus))
	resp.mimetype = "text/json"
	return resp
#-------------------------------------------------------------------
@app.route("/stream")
def StreamURL2():
	if not ChkLogin(): return ToLoginHTML
	global STREAMOUTPUT,LASHSHOOT
	resp = make_response()
	while CAMCHANGEFLAG:
		time.sleep(0.5)
	if not STREAMOUTPUT: #ストリームされていない状態
		if CAM.recording: #--------------------
			time.sleep(0.5)
			return CAMUSEDIMG #録画中画像
		#--------------------------------------
		STREAMOUTPUT = StreamingOutput()
		CAM.start_recording(STREAMOUTPUT, format='mjpeg')
		time.sleep(1)
	#CAM.annotate_text = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
	with STREAMOUTPUT.condition:
		STREAMOUTPUT.condition.wait()
		frame = STREAMOUTPUT.frame
		if SHOOTFlag: StreamShoot(frame)#ストリーム中に撮影ができる

	resp.data = frame
	resp.mimetype = "image/jpeg"
	return resp
#-------------------------------------------------------------------
#ストリーム撮影用フラグを立てるURL
@app.route("/streamShoot")
def StreamShootURL():
	if not ChkLogin(): return ToLoginHTML
	global SHOOTFlag
	SHOOTFlag = True
	return "OK"
#-------------------------------------------------------------------
def StreamShoot(buf):
	global SHOOTFlag,LASHSHOOT
	SHOOTFlag = False
	CaptF = os.path.join(os.getcwd(),"captures")
	if not os.path.isdir(CaptF): os.mkdir(CaptF)
	LASHSHOOT = os.path.join(CaptF,datetime.datetime.now().strftime("%Y%m%d%H%M%S")+".jpg")
	with open(LASHSHOOT,"wb") as f:
		f.write(buf)
#-------------------------------------------------------------------
@app.route("/streamStop")
def StreamStopURL():
	if not ChkLogin(): return ToLoginHTML
	global STREAMOUTPUT
	if STREAMOUTPUT:
		if CAM.recording: 
			if NOWTIMELAPSEFOLDER != "": return "NowTimelapse"
			CAM.stop_recording()
			STREAMOUTPUT = None
	return "StopStream"
#-------------------------------------------------------------------
@app.route("/GetShoot")
def StreamShootGetURL():
	if not ChkLogin(): return ToLoginHTML
	if LASHSHOOT:
		return send_file(LASHSHOOT)
	else:
		return "File Not Found"
#-------------------------------------------------------------------
#カメラの設定を変更するURL(GET)
@app.route("/Camerasetting")
def CameraSetURL():
	if not ChkLogin(): return ToLoginHTML
	global NowResolution,ANNOTATESIZE,CAM,CAMMODE
	for k in request.args.keys():
		v = request.args.get(k,"")
		if k == "Resolution":
			NowResolution = v
			if not CAM.recording: CAM.resolution = GetResolution()
		elif k == "FlameRate":
			if not CAM.recording: CAM.framerate = int(v)
		elif k == "hflip":
			CAM.hflip = True if v == "true" else False
		elif k == "vflip":
			CAM.vflip = True if v == "true" else False
		elif k == "brightness": #0-100 50
			CAM.brightness = int(v)
		elif k == "contrast": #-100-100 0
			CAM.contrast = int(v)
		elif k == "iso": #[0,100,200,320,400,500,640,800,1600] 0
			CAM.iso = int(v)
		elif k == "sharpness":#-100-100 0
			pass
		elif k == "fontsize":#6-160 24
			siz = int(v)
			if siz < 6:
				ANNOTATESIZE = 0
				CAM.annotate_text = ""
			else:
				ANNOTATESIZE = siz
				CAM.annotate_text_size = siz
		elif k == "cammode":
			if v == "picam":
				CAM.close()
				CAMMODE = "picam"
				CAM = None
				CAM = picamera.PiCamera()
			elif v == "opencv":
				if not OPENCV:return "Err"
				CAM.close()
				CAMMODE = "opencv"
				CAM = None
				CAM = OpenCVCamera(0)
		#OpenCV================================================
		if CAMMODE == "opencv":
			if k == "MotionEnable":
				CAM.MotionEnable = True if v == "true" else False
			elif k == "MotionTrigger":
				CAM.MotionTrigger = True if v == "true" else False
			elif k == "MotionRectime":
				CAM.MotionRectime = int(v)
			elif k == "Motion_Threshold":
				CAM.Motion_Threshold = int(v)
			elif k == "Motion_Preview":
				CAM.Motion_Preview = True if v == "true" else False
	return "OK"
#-------------------------------------------------------------------
#録画開始URL
@app.route("/RecodingStart")
def RecodingStartURL():
	if not ChkLogin(): return ToLoginHTML
	global STREAMOUTPUT,CAMCHANGEFLAG,NOWRECORDINGFILE
	if psutil.disk_usage('/').percent > 90:
		return "No space left on device",503
	CAMCHANGEFLAG = True
	if CAM.recording: CAM.stop_recording()
	STREAMOUTPUT = None #ストリーム中に割り込んだ場合の為
	Fname = os.path.join(os.getcwd(),"Recs")
	if not os.path.isdir(Fname): os.mkdir(Fname)
	NOWRECORDINGFILE = os.path.join(Fname,datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_" + str(CAM.framerate[0]) + ".h264")
	if CAMMODE == "opencv":NOWRECORDINGFILE = os.path.splitext(NOWRECORDINGFILE)[0] + ".mp4"
	CAM.capture(os.path.splitext(NOWRECORDINGFILE)[0] + ".jpg",format="jpeg") #サムネイル
	CAM.start_recording(NOWRECORDINGFILE, format='h264')
	CAMCHANGEFLAG = False
	return "StartRecording"
#-------------------------------------------------------------------
#録画終了URL
@app.route("/RecodingStop")
def RecodingStopURL():
	if not ChkLogin(): return ToLoginHTML
	global NOWRECORDINGFILE
	if CAM.recording: CAM.stop_recording()
	if CONFIG["AutoRecConvert"] == "True" and CAMMODE == "picam": AddConvertSchedule(NOWRECORDINGFILE)
	NOWRECORDINGFILE = ""
	return "StopRecording"
#-------------------------------------------------------------------
#タイムラプスURL
@app.route("/Timelapse")
def TimelapseURL():
	if not ChkLogin(): return ToLoginHTML
	global NOWTIMELAPSEFOLDER,STREAMOUTPUT,TIMELAPSETIME
	mode = request.args.get("mode","stop")
	TIMELAPSETIME = int(request.args.get("time","0"))
	BaseFolder = os.path.join(os.getcwd(),"Timelapses")
	if mode == "start":
		if TIMELAPSETIME <= 0: return "ERR"
		if not os.path.isdir(BaseFolder): os.mkdir(BaseFolder)
		while CAMCHANGEFLAG:
			time.sleep(0.5)
		if not STREAMOUTPUT: #ストリームされていない状態
			if CAM.recording:
				time.sleep(0.5)
				return "CAMUSEING"
			STREAMOUTPUT = StreamingOutput()
			CAM.start_recording(STREAMOUTPUT, format='mjpeg')
			time.sleep(1)
		NOWTIMELAPSEFOLDER = os.path.join(BaseFolder,datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
		os.mkdir(NOWTIMELAPSEFOLDER)
		with open(os.path.join(NOWTIMELAPSEFOLDER,"data.txt"),"w",encoding="UTF-8") as f:
			tfps = 1 / TIMELAPSETIME
			f.write(f"FPS={tfps:.3f}")
		th = threading.Thread(target=TimelapseThread,daemon=True)
		th.start()
	else:
		NOWTIMELAPSEFOLDER = "" #フォルダ名が変わると時間で終わる
	return "OK"
#-------------------------------------------------------------------
def TimelapseThread():
	Folder = NOWTIMELAPSEFOLDER
	st = TIMELAPSETIME
	print(f"タイムラプスが開始されました。{st}s")
	while Folder == NOWTIMELAPSEFOLDER:
		if STREAMOUTPUT:
			with STREAMOUTPUT.condition:
				STREAMOUTPUT.condition.wait()
				frame = STREAMOUTPUT.frame
				with open(os.path.join(NOWTIMELAPSEFOLDER,datetime.datetime.now().strftime("%Y%m%d%H%M%S")+".jpg"),"wb") as f:
					f.write(frame)
			time.sleep(st)
		else:
			print("タイムラプス中に別の割り込み発生")
			break
	print("タイムラプスが終了しました")
#-------------------------------------------------------------------
@app.route("/CameraCont")
def ServoMoveURL():
	if not ChkLogin(): return ToLoginHTML
	#return "OK"
	global ServoY_NowAngle,ServoX_NowAngle,LIGHTBRIGHT
	#Getで+-どのくらい動かすのか指示する
	x = int(request.args.get("X","0"))
	y = int(request.args.get("Y","0"))
	Light = request.args.get("Light","") #ライト
	if x != 0:
		ServoX_NowAngle += x
		if ServoX_NowAngle < 0: ServoX_NowAngle = 0
		if ServoX_NowAngle > 180: ServoX_NowAngle = 180
		ServoX.Angle(ServoX_NowAngle)
	if y != 0:
		ServoY_NowAngle += y
		if ServoY_NowAngle < 0: ServoY_NowAngle = 0
		if ServoY_NowAngle > 180: ServoY_NowAngle = 180
		ServoY.Angle(ServoY_NowAngle)
		
	if Light:
		LIGHTBRIGHT = True if Light == "ON" else False #状態を記録
		digitalWrite(LIGHTPIN,(HIGH if LIGHTBRIGHT else LOW))
	return "OK"

#-------------------------------------------------------------------
#-------------------------------------------------------------------
#画像参照用URL
@app.route("/captures")
def capturesURL():
	if not ChkLogin(): return ToLoginHTML
	IMAGECOUNT = 10
	ImageEnd = False
	html = ""
	PAGE = int(request.args.get("page","0"))
	IMAGES = glob.glob(os.path.join(os.getcwd(),"captures/*"))
	IMAGES.sort(reverse=True)
	for i in range(IMAGECOUNT):#1ページ当たりの画像数
		index = PAGE * IMAGECOUNT + i
		if index >= len(IMAGES):
			ImageEnd = True
			break
		html += '<img src="' + os.path.relpath(IMAGES[index]) + '"width=320 onclick="Showmsg(this);">'
		if i % 2 == 1: html += "<br>"
	BackDisabled = "true" if PAGE == 0 else "false"
	NextDisabled = "true" if ImageEnd else "false"
	NextPage = PAGE + 1
	BackPage = PAGE - 1
	return render_template('capturepage.html', TITLE="キャプチャ一覧",Inserthtml=html,BackDisabled=BackDisabled,NextDisabled=NextDisabled,NextPage=NextPage,BackPage=BackPage,MODE="capt")
#-------------------------------------------------------------------
#動画参照用URL
@app.route("/records")
def RecordsURL():
	if not ChkLogin(): return ToLoginHTML
	IMAGECOUNT = 10
	ImageEnd = False
	html = ""
	PAGE = int(request.args.get("page","0"))
	IMAGES = glob.glob(os.path.join(os.getcwd(),"Recs/*.jpg")) #ポスター画像を検索
	#H264s = [os.path.splitext(i)[0] for i in glob.glob(os.path.join(os.getcwd(),"Recs/*.h264"))]
	MP4s = [os.path.splitext(i)[0] for i in glob.glob(os.path.join(os.getcwd(),"Recs/*.mp4"))]
	IMAGES.sort(reverse=True)
	for i in range(IMAGECOUNT):#1ページ当たりの動画数
		index = PAGE * IMAGECOUNT + i
		if index >= len(IMAGES):
			ImageEnd = True
			break
		bn = os.path.splitext(IMAGES[index])[0] #拡張子を取る
		if bn in MP4s:
			html += '<div>{0}<br><video src="{1}" width=320 controls preload="none" poster="{2}" onclick="Showmsg(this);"></video></div>'.format(os.path.basename(IMAGES[index]).replace(".jpg",".mp4"),os.path.relpath(IMAGES[index]).replace(".jpg",".mp4"),os.path.relpath(IMAGES[index]))
		else:
			html += '<div>{0}<br><img src="{1}" width=320 onclick="Showmsg(this);"></div>'.format(os.path.basename(IMAGES[index]),os.path.relpath(IMAGES[index]))
		if i % 2 == 1: html += "<br>"
	BackDisabled = "true" if PAGE == 0 else "false"
	NextDisabled = "true" if ImageEnd else "false"
	NextPage = PAGE + 1
	BackPage = PAGE - 1
	return render_template('capturepage.html', TITLE="録画一覧",Inserthtml=html,BackDisabled=BackDisabled,NextDisabled=NextDisabled,NextPage=NextPage,BackPage=BackPage,MODE="rec")
#-------------------------------------------------------------------
@app.route("/recordsConv")
def RecordsConvURL():
	if not ChkLogin(): return ToLoginHTML
	global TMPFLAG
	fname = request.args.get("name","")
	FPS = int(request.args.get("fps","0"))
	fpath = os.path.splitext(os.path.join(os.getcwd(),fname[1:]))[0] + ".h264"
	if FPS <= 1: return "ERR"
	if os.path.isfile(fpath):
		th = threading.Thread(target=ConvMP4Now,daemon=True,args=(fpath,FPS))
		th.start()
		return "OK"
	else:
		return "ERR"
#-------------------------------------------------------------------
def ConvMP4Now(fpath,FPS):
	global TMPFLAG
	TMPFLAG = True
	Conv_h264ToMP4(fpath,"",FPS,False)
	TMPFLAG = False

#-------------------------------------------------------------------
@app.route("/recordsConvStatus")
def RecordsConvStatusURL():
	if not ChkLogin(): return ToLoginHTML
	return "" if TMPFLAG else "OK"
#-------------------------------------------------------------------
#タイムラプス参照URL
@app.route("/timelapses")
def TimelapsesURL():
	if not ChkLogin(): return ToLoginHTML
	IMAGECOUNT = 10
	ImageEnd = False
	html = ""
	PAGE = int(request.args.get("page","0"))
	IMAGES = [i for i in glob.glob(os.path.join(os.getcwd(),"Timelapses/*")) if os.path.isdir(i)]
	IMAGES.sort(reverse=True)
	for i in range(IMAGECOUNT):#1ページ当たりの動画数
		index = PAGE * IMAGECOUNT + i
		if index >= len(IMAGES):
			ImageEnd = True
			break
		poster = glob.glob(IMAGES[i] + "/*.jpg")
		if len(poster) == 0: continue
		if i % 2 == 0: html += '<div id="Group">\n' #divでグループにすることで文字の下に画像を置いても横並びできるようにする。別途CSS定義
		#タイムラプスの情報を載せる
		with open(os.path.join(IMAGES[i],"data.txt"),"r",encoding="UTF-8") as f:
			l = [j.strip().split("=") for j in f.readlines()]
		dic = {}
		for j in range(len(l)):
			dic[l[j][0]] = l[j][1]
		html += f"<div>{os.path.basename(poster[0])}({len(poster)}枚/{dic['FPS']}FPS)<br>"
		html += '<img src="' + os.path.relpath(poster[0]) + '"width=320 onclick="Showmsg(this);"></div>'
		#html += '<img src="' + os.path.relpath(poster[0]) + '"width=320 onclick="Showmsg(this);">'
		if i % 2 == 1: html += "\n</div>\n"
	if len(IMAGES) % 2 == 1: html += "</div>\n"
	BackDisabled = "true" if PAGE == 0 else "false"
	NextDisabled = "true" if ImageEnd else "false"
	NextPage = PAGE + 1
	BackPage = PAGE - 1
	return render_template('EditTimelapse.html', TITLE="タイムラプス一覧",Inserthtml=html,BackDisabled=BackDisabled,NextDisabled=NextDisabled,NextPage=NextPage,BackPage=BackPage)
#-------------------------------------------------------------------
@app.route("/timelapsescgi")
def TimelapsesCGI():
	if not ChkLogin(): return ToLoginHTML
	global MAKEFILE
	MAKEFILE = ""
	mode = request.args.get("mode","")
	file = request.args.get("file","")
	FPS = int(request.args.get("fps","1"))
	file = os.path.abspath(file[1:])
	export = os.path.join(os.getcwd(),"tmp")
	URL = ""
	if mode == "zip":
		URL = "/" + os.path.basename(MakeZIP(file,export))
	elif mode == "mp4":
		URL = "/" + os.path.basename(MakeMove(file,export,FPS))
	else:
		return "ERR"
	MAKEFILE = URL
	return URL
#-------------------------------------------------------------------
@app.route("/timelapsescgistatus")
def TimelapsesCGIStatus():
	if not ChkLogin(): return ToLoginHTML
	return MAKEFILE
#-------------------------------------------------------------------
@app.route("/rmfiles")
def FileRemoveURL():
	if not ChkLogin(): return ToLoginHTML
	fname = request.args.get("name","")
	fpath = os.path.join(os.getcwd(),fname[1:])
	if os.path.isfile(fpath):
		if os.path.splitext(fpath)[1] in [".jpg",".mp4",".h264"]:
			os.remove(fpath)
			print(fpath + "を削除しました")
			RemoveThumbnail()
			return "OK",200
	else:
		if "Timelapses" in fpath:
			shutil.rmtree(fpath)
			print(fpath + "を削除しました")
			return "OK",200

	return "Error",503
#-------------------------------------------------------------------
#ステータス表示
@app.route("/status")
def StatusURL():
	if not ChkLogin(): return ToLoginHTML
	return render_template('status.html', SDPercent=str(psutil.disk_usage('/').percent))
#-------------------------------------------------------------------
@app.route("/getconfig")
def GetConfigURL():
	if not ChkLogin(): return ToLoginHTML
	resp = make_response(json.dumps(CONFIG))
	resp.mimetype = "text/json"
	return resp
#-------------------------------------------------------------------
@app.route("/setconfig")
def SetConfigURL():
	if not ChkLogin(): return ToLoginHTML
	global CONFIG
	CONFIG["RecSplit"] = request.args.get("RecSplit","False")
	CONFIG["RecSplitSize"] = request.args.get("RecSplitSize","1024")
	CONFIG["NoSpaceDo"] = request.args.get("NoSpaceDo","1")
	#アップロード設定
	CONFIG["AutoUpload"] = request.args.get("AutoUpload","False")
	CONFIG["AutoUploadTiming"] = request.args.get("AutoUploadTiming","1")
	CONFIG["AutoUploadSpace"] = request.args.get("AutoUploadSpace","50")
	CONFIG["AutoUploadURL"] = request.args.get("AutoUploadURL","")
	#変換設定
	CONFIG["AutoRecConvert"] = request.args.get("AutoRecConvert","True")
	CONFIG["AutoRemoveh264"] = request.args.get("AutoRemoveh264","True")
	CONFIG["ConvxN"] = request.args.get("ConvxN","1")

	Conf_Save()
	return "OK"
#-------------------------------------------------------------------
@app.route("/System")
def SystemURL():
	if not ChkLogin(): return ToLoginHTML
	CMD = request.args.get("cmd","")
	if CMD == "shutdown": SystemShutdown()
	if CMD == "reboot": Systemreboot()

#-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+自動検出用+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@app.route("/<path:path>")
def AnyPage(path):
	BList = [".py",".ini"] #ブラックリスト
	TEXTList = [".html","htm","txt","json","log"] #テキストとして返すもの
	LOGINList = ["camera\.html","camera\.js","Config\.html",".+\.mp4",".+\.h264",".+\.jpg"] #ログインしないと返さないもの 正規表現
	file = os.path.join(os.getcwd(),path)
	ex = os.path.splitext(path)[1]
	if ex in BList:
		return NotFound()
	elif ex == "":
		file += ".html" #拡張子無しはHTMLとする
		ex = ".html"
	
	if os.path.isfile(file):
		for r in LOGINList:
			if re.search(r,file): 
				if not ChkLogin(): return ToLoginHTML
		if ex in TEXTList:
			return Gethtml(file)
		else:
			return send_file(file)
			#return send_from_directory(directory=os.path.abspath(os.path.join(os.path.dirname(__file__),file)),filename=fname)
	else:
		return NotFound()
#-------------------------------------------------------------------
#エラーを返す
@app.errorhandler(404)
def NotFound2(err):
	return NotFound()
def NotFound():
	return HTMLFlame.format(title="ページが見つかりません",head="",body="<H1>404 Not Found</H1><hr>ページは見つかりませんでした")

#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#機能宣言域#=#=#=#=#=#=#=##=#=#=#=#=#=#=#
#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#WEB系機能
def ChkLogin():
	id = Cryptograph(request.cookies.get(SERVERNAME),"decode")
	return id if id in USERS else False
#====================================================================================
#その他機能
def Gethtml(Path):
	try:
		with open(Path,"r",encoding="UTF-8") as f:
			l = f.read()
	except:
		return ""
	else:
		return l
#ログイン許可ユーザーを読み込む関数
def ReadUSERS():
	global USERS
	try:
		with open("users","r",encoding="UTF-8") as f:
			l = [i.strip() for i in f.readlines()]
	except:
		pass
	else:
		for i in l:
			buf = i.split(",")
			USERS[buf[0]] = buf[1]
#====================================================================================
def LoadImage():
	global CAMUSEDIMG
	with open("Recording.png","rb") as f:
		CAMUSEDIMG = f.read()
#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#WEB以外の処理#=#=#=#=#=#=#=##=#=#=#=#=#=#=#
#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=#=#=##=#=#=#=#=#=#=#=#=#=#=#=
#暗号化
def Cryptograph(Str,Mode='encode'):
	if not Str: return ""
	f = Fernet(Cryptographykey)
	if Mode == "encode":
		return f.encrypt(Str.encode("UTF-8")).decode("UTF-8")
	else:
		try:
			return f.decrypt(Str.encode("UTF-8")).decode("UTF-8")
		except:
			return ''

#====================================================================================
def GetResolution():
	buf = NowResolution.split("x")
	return int(buf[0]),int(buf[1])
#====================================================================================
#MP4BOXを使って変換する関数(変換するファイルの倍以上のストレージ容量が必要)
def Conv_h264ToMP4(File,MP4Name="",FPS=0,Remove=True):
	if psutil.disk_usage('/').free <= os.path.getsize(File):
		print("変換に必要な空き容量がありません")
		return 1
	if FPS == 0: 
		FPSRe = re.compile('_\d+\.')
		if FPSRe.search(File):
			FPS = int(FPSRe.findall(File)[-1][1:-1]) #ファイル名末尾に"_10.h264"のようにFPSを書いておけばそれを参照する
		else:
			FPS = CAM.framerate[0] #無ければ現在のカメラのレートを参照
	if MP4Name == "": MP4Name=os.path.splitext(File)[0] + ".mp4"
	CMD = 'MP4Box -new -fps %FPS -add %H264NANE %MP4NAME'
	FPS_ = FPS
	xN = int(CONFIG["ConvxN"])
	if xN != 1: FPS_ = FPS * xN
	CMD = CMD.replace('%FPS',str(FPS_))
	CMD = CMD.replace('%H264NANE',File)
	CMD = CMD.replace('%MP4NAME',MP4Name)
	print(CMD)
	subprocess.run(CMD,shell=True)
	#ConvMP4(File)
	#ConvAVI(File)
	if Remove: os.remove(File)
	return 0
#====================================================================================
#HTTPを使って別のデバイスにデータをアップロードする
def UploadFile(Path="",ElemName="Upload"):
	global NOWUPLOADING
	if Path == "" or os.path.isfile(Path) == False:
		files = [i for i in glob.glob("Recs/*") if re.match("(.+\.mp4$|.+\.h264$)",i)] #動画データをリスト化
		if len(files) == 0: return
		files.sort(key=os.path.getmtime, reverse=False)
	Path = files[0]
	data = open(Path,"rb")
	Files = {ElemName: (os.path.basename(Path),data)}
	if NOWUPLOADING:return
	NOWUPLOADING = True
	try:
		resp = requests.post(CONFIG["AutoUploadURL"],files=Files,timeout=(10.0, 30.0))
	except:
		NOWUPLOADING = False
		print("エラー:アップロードに失敗しました")
		return
	NOWUPLOADING = False
	if resp.status_code == 200:
		os.remove(Path)
		RemoveThumbnail()
		print(f"情報:{os.path.basename(Path)}をアップロードしました")
	else:
		print("エラー:アップロードに失敗しました")
#====================================================================================
#もっとも古い録画データを削除する
def RMLastRec():
	files = [i for i in glob.glob("Recs/*") if re.match("(.+\.mp4$|.+\.h264$)",i)]
	if len(files) == 0: return
	files.sort(key=os.path.getmtime, reverse=False)
	os.remove(files[0])
	RemoveThumbnail()
	print(files[0] + "を削除しました")
#====================================================================================
def RemoveThumbnail(): #動画のサムネイルを整理する
	mp4ORh264 = [os.path.splitext(os.path.basename(i))[0] for i in [j for j in glob.glob("Recs/*") if re.match("(.+\.mp4$|.+\.h264$)",j)]]
	jpg = [os.path.splitext(os.path.basename(i))[0] for i in glob.glob("Recs/*.jpg")]
	for i in jpg:
		if not i in mp4ORh264: os.remove(os.path.join("Recs",i + ".jpg"))
#====================================================================================
#動画にする
def MakeMove(images:str,fname:str,FPS:int=1)->str:
	if not isinstance(images,list):
		if os.path.isdir(images):
			images = glob.glob(os.path.join(images,"*.jpg"))
			if len(images) == 0: return ""
			images.sort(key=os.path.getmtime, reverse=False)
	fourcc = cv2.VideoWriter_fourcc('m','p','4','v')
	tmpim = cv2.imread(images[0])#縦横取得用
	Fname = os.path.splitext(fname)[0] #fnameに拡張子は要らない
	Fname = f'{Fname}.mp4'
	video = cv2.VideoWriter(Fname, fourcc, FPS, (tmpim.shape[1], tmpim.shape[0]))
	for i in range(len(images)):
		video.write(cv2.imread(images[i]))
	video.release()
	return Fname
#====================================================================================
#フォルダをzipに圧縮する
def MakeZIP(Path:str,fname:str="") -> str:
	if not os.path.isdir(Path): return ""
	fname = os.path.splitext(fname)[0] #fnameに拡張子は要らない
	return shutil.make_archive(fname, format='zip', root_dir=Path)
#====================================================================================
#動画をMP4に変換する
def ConvMP4(File:str,FPS:int=0)->str:
	video = cv2.VideoCapture(File)
	if not video.isOpened():
		print("動画ファイルを開けませんでした")
		return ""
	OFile = os.path.splitext(File)[0] + ".mp4"
	if FPS == 0: FPS = video.get(cv2.CAP_PROP_FPS)
	W = int(video.get(cv2.CAP_PROP_FRAME_WIDTH)) #なぜかFloatで返ってくる
	H = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
	fourcc = cv2.VideoWriter_fourcc(*"mp4v") #*"mp4v"は'm','p','4','v'と同じ
	writer = cv2.VideoWriter(OFile,fourcc,FPS,(W,H))
	while True:
		ret, frame = video.read()
		if ret:
			writer.write(frame)
		else:
			break
	video.release()
	writer.release()
	return OFile
#====================================================================================
#動画をMP4に変換する
def ConvAVI(File:str,FPS:int=0)->str:
	video = cv2.VideoCapture(File)
	if not video.isOpened():
		print("動画ファイルを開けませんでした")
		return ""
	OFile = os.path.splitext(File)[0] + ".avi"
	if FPS == 0: FPS = video.get(cv2.CAP_PROP_FPS)
	W = int(video.get(cv2.CAP_PROP_FRAME_WIDTH)) #なぜかFloatで返ってくる
	H = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
	fourcc = cv2.VideoWriter_fourcc(*"MJPG") #*"mp4v"は'm','p','4','v'と同じ
	writer = cv2.VideoWriter(OFile,fourcc,FPS,(W,H))
	while True:
		ret, frame = video.read()
		if ret:
			writer.write(frame)
		else:
			break
	video.release()
	writer.release()
	return OFile
#====================================================================================
#====================================================================================
#インターバルタイマー関数
#====================================================================================
#一定間隔で変数を監視して行うイベント系関数
def IntervalScheduleRun():
	th = threading.Thread(target=IntervalSchedule,daemon=True)
	th.start()
#----------------------------
def IntervalSchedule():
	global NOWRECORDINGFILE
	while True:
		#ストレージ容量を監視して録画を止めたり削除したりする
		StorageP = psutil.disk_usage('/').percent
		if StorageP > 90:
			if CONFIG["NoSpaceDo"] == "1":
				RecodingStopURL()
				print("ストレージ容量が90%を超えたため録画を停止しました")
			elif CONFIG["NoSpaceDo"] == "2":
				RMLastRec()
		
		#特定の容量で分割する場合
		if CONFIG["RecSplit"] == "True":
			if NOWRECORDINGFILE != "" and os.path.getsize(NOWRECORDINGFILE) > int(CONFIG["RecSplitSize"]) * (1024**2):
				print("録画サイズが規定値を超えたため分割します")
				CAM.stop_recording()
				if CONFIG["AutoRecConvert"] == "True" and CAMMODE == "picam": AddConvertSchedule(NOWRECORDINGFILE)
				NOWRECORDINGFILE = os.path.join(os.path.join(os.getcwd(),"Recs"),datetime.datetime.now().strftime("%Y%m%d%H%M%S")+".h264")
				if CAMMODE == "opencv":NOWRECORDINGFILE = os.path.splitext(NOWRECORDINGFILE)[0] + ".mp4"
				CAM.capture(os.path.splitext(NOWRECORDINGFILE)[0] + ".jpg",format="jpeg") #サムネイル
				CAM.start_recording(NOWRECORDINGFILE, format='h264')
				#CAM.split_recording() #サムネイル撮影があるので使わない
		if CONFIG["AutoUpload"] == "True":
			if CONFIG["AutoUploadTiming"] == "1" or StorageP > int(CONFIG["AutoUploadSpace"]):
				th = threading.Thread(target=UploadFile,daemon=True)
				th.start()

		#動画を変換する
		if len(CONVERTTASK) > 0: Conv_h264ToMP4(CONVERTTASK.pop(),Remove=(True if CONFIG["AutoRemoveh264"] == "True" else False))
		
		time.sleep(30)
#====================================================================================
#====================================================================================
#====================================================================================
#====================================================================================
#====================================================================================
def AddConvertSchedule(Path):
	global CONVERTTASK
	CONVERTTASK.append(Path)
#====================================================================================
def AnnotateUpdate():
	global ANNOTATEUpdateing
	if ANNOTATEUpdateing: return
	ANNOTATEUpdateing = True
	th = threading.Thread(target=annotateUpdate_,daemon=True)
	th.start()
def annotateUpdate_():
	while ANNOTATEUpdateing:
		if ANNOTATESIZE >= 6 and CAM: CAM.annotate_text = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		time.sleep(1)
#====================================================================================
def GetStorageUsed():#メインストレージ使用率を返す
	return psutil.disk_usage('/').percent
#====================================================================================
def SystemShutdown():
	subprocess.run(('/sbin/shutdown','-h','now'))
#====================================================================================
def Systemreboot():
	subprocess.run(('/sbin/shutdown','-r','now'))
#====================================================================================
def GPIOSetUP():
	global ServoX,ServoY
	PinMode(LIGHTPIN,OUTPUT)
	ServoY = Servo(ServoY_Pin)
	ServoY.Angle(ServoY_Center)
	ServoX = Servo(ServoX_Pin)
	ServoX.Angle(ServoX_Center)
	#PinMode(ShutdownButton,INPUT_PULLUP)

#====================================================================================
#設定管理系
def Conf_Default():
	global CONFIG
	CONFIG = {}
	#録画設定
	CONFIG["RecSplit"] = "False"
	CONFIG["RecSplitSize"] = "1024" #MB
	CONFIG["NoSpaceDo"] = "1" #ストレージ残量90%の時どうするか 1:停止 2:古いの削除
	#アップロード設定
	CONFIG["AutoUpload"] = "False"
	CONFIG["AutoUploadTiming"] = "1" #1:常に 2:残量低下時(%)
	CONFIG["AutoUploadSpace"] = "50" #残量低下の閾値(%)
	CONFIG["AutoUploadURL"] = "http://192.168.0.199/uploadapp" #アップロード先のURL
	#変換設定
	CONFIG["AutoRecConvert"] = "True"
	CONFIG["AutoRemoveh264"] = "True"
	CONFIG["ConvxN"] = "1"
	Conf_Save()
def Conf_Read():
	global CONFIG
	CONFIG = {}
	if not os.path.isfile(CONFIG_FILE):
		Conf_Default()
		return
	with open(CONFIG_FILE,"r",encoding="UTF-8") as f:
		l = [i.strip() for i in f.readlines() if i != ""]
	for i in l:
		buf = i.split("|")
		CONFIG[buf[0]] = buf[1]
def Conf_Save():
	with open(CONFIG_FILE,"w",encoding="UTF-8") as f:
		for k in CONFIG.keys():
			f.write(f"{k}|{CONFIG[k]}\n")
#====================================================================================
def Main():
	ReadUSERS()
	IntervalScheduleRun() #10秒おきに自動スケジュール作動
	try:
		app.run(host="0.0.0.0", port=25570)#debug=True)
	except KeyboardInterrupt:
		CAM.close()
#====================================================================================
class StreamingOutput(object):
	def __init__(self):
		self.frame = None
		self.buffer = io.BytesIO()
		self.condition = threading.Condition()
	def write(self, buf):
		#if buf.startswith(b'\xff\xd8'):
		self.buffer.truncate()
		with self.condition:
			self.frame = self.buffer.getvalue()
			self.condition.notify_all()
			self.buffer.seek(0)
		return self.buffer.write(buf)

#====================================================================================
class OpenCVCamera():
	def __init__(self,id) -> None:
		self.Cam = cv2.VideoCapture(id) #カメラを接続
		#インスタンス変数
		self.recording = False
		self._framerate = 30
		self.hflip = False
		self.vflip = False
		self.iso = 0
		self.annotate_text = ""
		self.contrast = 0
		self.brightness = 0
		self.annotate_text_size = 24
		self.resolution = [800,600]
		#動体検知系
		self.MotionEnable = True #動体検知を有効にするか
		self.MotionTrigger = True #動体検知トリガで録画を制御するか
		self.MotionRectime = 30 #動体検知があってから録画する長さ
		self._MotionRecStarttime = 0 #動体検知があってから録画する時間
		self.Motion_Threshold = 1000 #動体検知閾値(長方形の面積)
		self.Motion_Preview = True #画面に枠を描写するか
		self._LastFrameGlay = None
	#-------------------------------------------------------------
	def __del__(self):
		pass
		#self.Cam.release()
	#-------------------------------------------------------------
	def capture(self,Path:str,format="jpg"):
		self._StartUP()
		ret, frame = self.Cam.read()
		img = self._ImageEdit(frame)	
		cv2.imwrite(os.path.splitext(Path)[0] + ".jpg",img)
	#-------------------------------------------------------------
	def Read(self):
		return ""
	#-------------------------------------------------------------
	def start_recording(self,Path,format="jpg"):
		self._StartUP()
		th = threading.Thread(target=self._DoRecordind,daemon=True,args=(Path,format))
		th.start()
		self.recording = True
	#-------------------------------------------------------------
	def _DoRecordind(self,Path,format):
		if format in ["jpg","jpeg","mjpg"]:
			fourcc = cv2.VideoWriter_fourcc(*"jpeg")
			if isinstance(Path,str): Path = os.path.splitext(Path)[0] + ".avi"
		else:
			fourcc = cv2.VideoWriter_fourcc(*"mp4v")
			if isinstance(Path,str): Path = os.path.splitext(Path)[0] + ".mp4"
		writer = None
		if isinstance(Path,str): writer = cv2.VideoWriter(Path, fourcc, self._framerate, (self.resolution[0],self.resolution[1]))
		while self.recording:
			MotionFlag = False
			ret, frame = self.Cam.read()
			if self.MotionEnable:
				MotionFlag = self._Motion(frame)
				if self.MotionTrigger and MotionFlag:
					self._MotionRecStarttime = time.time() #録画開始時間を更新

			frame = self._ImageEdit(frame)

			if writer:
				if self.MotionTrigger:
					if time.time() - self._MotionRecStarttime < self.MotionRectime: writer.write(frame)
				else:
					writer.write(frame)
			else:
				success, buffer = cv2.imencode(".jpg", frame)
				Path.write(buffer)
				#self.io_buf = io.BytesIO(buffer)
	#-------------------------------------------------------------
	def stop_recording(self):
		self.recording = False
	#-------------------------------------------------------------
	def _StartUP(self):
		self._LastFrameGlay = None
		self.Cam.set(cv2.CAP_PROP_FRAME_WIDTH,self.resolution[0])
		self.Cam.set(cv2.CAP_PROP_FRAME_HEIGHT,self.resolution[1])
		self.Cam.set(cv2.CAP_PROP_FPS,self._framerate)
		#if self.Cam.get(cv2.CAP_PROP_FRAME_WIDTH) != self.resolution[0]: print(f"失敗:{self.resolution[0]}")
		#if self.Cam.get(cv2.CAP_PROP_FRAME_HEIGHT) !=self.resolution[1]: print(f"失敗:{self.resolution[1]}")
		#if self.Cam.get(cv2.CAP_PROP_FPS) != self._framerate: print(f"失敗:{self._framerate}")
	#-------------------------------------------------------------
	def _ImageEdit(self,img):
		img_ = img
		#上下左右反転処理
		if self.hflip and self.vflip:
			img_ = cv2.flip(img_, -1)
			#img_ = np.flip(img_)
		elif self.hflip:
			img_ = cv2.flip(img_, 1)
			#img_ = np.flip(img_,1)
		elif self.vflip:
			img_ = cv2.flip(img_, 0)
			#img_ = np.flip(img_,0)
		#印字処理
		if self.annotate_text_size > 6:
			img_ = cv2.putText(img_,text=self.annotate_text,org=(0, self.resolution[1]),fontFace=cv2.FONT_HERSHEY_SIMPLEX,fontScale=self.annotate_text_size/24,color=(255, 255, 255),thickness=2,lineType=cv2.LINE_4)
		return img_
	#-------------------------------------------------------------
	def _Motion(self,frame_New):
		gray = cv2.cvtColor(frame_New, cv2.COLOR_BGR2GRAY) #グレースケールに変換
		
		if self._LastFrameGlay is None: #比較用のフレームを取得する
			self._LastFrameGlay = gray.copy().astype("float")
			return False

		# 現在のフレームと移動平均との差を計算
		cv2.accumulateWeighted(gray, self._LastFrameGlay, 0.6) #移動平均
		frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(self._LastFrameGlay))

		# デルタ画像を閾値処理を行う
		thresh = cv2.threshold(frameDelta, 3, 255, cv2.THRESH_BINARY)[1]

		# 輪郭のデータを取得
		contours = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]

		# 差分があった点を画面に描画
		Flag = False
		for target in contours:
			x, y, w, h = cv2.boundingRect(target)
			
			# 小さい変更点は無視
			if w*h < self.Motion_Threshold: continue 
			Flag = True
			if self.Motion_Preview: cv2.rectangle(frame_New, (x, y), (x+w, y+h), (0,0,255), 1) #渡したイメージに上書き
		return Flag
	#-------------------------------------------------------------
	def close(self):
		self.Cam.release()
	#-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-
	@property
	def framerate(self):
		return (self._framerate,1)
	@framerate.setter
	def framerate(self,framerate):
		self._framerate = framerate
	#-------------------------------------------------------------

#====================================================================================

if __name__ == '__main__':
	if CAMMODE == "picam":
		CAM = picamera.PiCamera()
	else:
		CAM = OpenCVCamera(0)
	LoadImage()
	CAM.resolution = GetResolution()
	CAM.annotate_text_size = 24
	Conf_Read()
	AnnotateUpdate()
	GPIOSetUP()
	Main()
#末尾資料
'''
クッキーをセットする
resp = make_response(HTML)
resp.set_cookie(クッキー名,値,max_age=有効期間)

クッキーを取得
request.cookies.get('クッキー名')

Get送信データ取得
value = request.args.get("Name","") #第二引数は、値が無い時に返される値を指定できる

ファイル(POST)
if '名前' not in request.files: #POSTにデータがあるか確認
for file in request.files.getlist('名前'):
	fileName = file.filename
	file.save(fileName)
'''