# coding: UTF-8
HELP = '''
#==============================================================================#
 Arduino風関数でラズパイを使うためのモジュール
#==============================================================================#
(C) 2022 Rcat999
Twtter : @Rcat999
YouTube: Rcat999

+--------------概要--------------+
Arduinoからラズパイに手を出した人向けのモジュール。
慣れ親しんだdigitalWriteやanalogWrite関数を使いましょう!!


+--------------利用規約--------------+
下記グローバルルールに則ります
 https://sites.google.com/view/rcatglobalrule


+--------------使い方--------------+
・使用例
from GPIO_Arduino import *
PinMode(18,OUTPUT)
digitalWrite(18,HIGH)
CleanUP()

from GPIO_Arduino import *
analogWrite(18,50) #PWM値は0-100
CleanUP()

・サーボの使い方
from GPIO_Arduino import *
Sv = Servo(18)
Sv.Angle(90)
CleanUP()

+--------------リンク--------------+
https://drive.google.com/uc?id=


+--------------必要ライブラリ--------------+
>wiringpi


+--------------履歴--------------+
Ver 1.0.0 2022/04/04 初版
'''
import sys,os,time
import wiringpi
VERSION = "1.0.0"
LASTDATE = "2022/04/04"
##################################################################################
#グローバル変数
INPUT = wiringpi.GPIO.INPUT
OUTPUT = wiringpi.GPIO.OUTPUT
INPUT_PULLUP = wiringpi.GPIO.PUD_UP
INPUT_PULLDOWN = wiringpi.GPIO.PUD_DOWN
PinModes1 = {
	'INPUT':INPUT,
	0:INPUT,
	INPUT:INPUT,
	INPUT_PULLUP:INPUT,
	INPUT_PULLDOWN:INPUT,
	'OUTPUT':OUTPUT,
	1:OUTPUT,
	OUTPUT:OUTPUT,
}
PinModes2 = [
	INPUT_PULLUP,
	INPUT_PULLDOWN
]
LOW = wiringpi.GPIO.LOW
HIGH = wiringpi.GPIO.HIGH
PinStat = {
	'LOW':wiringpi.GPIO.LOW,
	'HIGH':wiringpi.GPIO.HIGH,
	LOW:LOW,
	HIGH:HIGH,
	0:wiringpi.GPIO.LOW,
	1:wiringpi.GPIO.HIGH
}
PWMs = []
#######################################################################################
def SetUP():
	wiringpi.wiringPiSetupGpio()

#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
#Arduino風関数
def PinMode(Pin,Mode):
	if Mode in PinModes1:
		wiringpi.pinMode(Pin,PinModes1[Mode])
	if Mode in PinModes2:
		wiringpi.pinMode(Pin,PinModes1[Mode])
		wiringpi.pullUpDnControl(Pin,Mode)

#====================================================================================
def digitalWrite(Pin,Mode):
	if Mode in PinStat:
		wiringpi.digitalWrite(Pin,PinStat[Mode])

#====================================================================================
#0-1024
def analogWrite(Pin,Value,Freq=1000): #Freqは最初のピンのみ有効。以降は変更できない。
	global PWMs
	if len(PWMs) == 0:
		wiringpi.pinMode(12, wiringpi.GPIO.PWM_OUTPUT) #最初にPWM系のピンをまとめて初期化。そうじゃないと2個目が反応しない
		wiringpi.pinMode(13, wiringpi.GPIO.PWM_OUTPUT)
		wiringpi.pwmSetMode(wiringpi.GPIO.PWM_MODE_MS)
		wiringpi.pwmSetRange(1024) #0-1024
		wiringpi.pwmSetClock(int(19200000 / (Freq * 1024))) #19200000はラズパイのハードウェアクロックらしい
		PWMs.append(Pin)

	#他のピンは初期化しなくてもいいみたい。
	wiringpi.pwmWrite(Pin, Value)

#====================================================================================
def digitalRead(pin):
	return wiringpi.digitalRead(pin)
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
#サーボ制御クラス
class Servo():
	def __init__(self,pinNum,min=26,max=123,freq=50):
		#min,maxはデューティ比の最大最小。使うサーボに合わせて最適な値を入力する
		self.min = min
		self.max = max
		self.SvPin = pinNum
		analogWrite(self.SvPin,0,freq)
		self.nowduty = 0

	def Angle(self,ang):
		self.nowduty = int(self.map(ang,0,180,self.min,self.max))
		analogWrite(self.SvPin,self.nowduty)

	def Enable(self):
		analogWrite(self.SvPin,self.nowduty)

	def Disable(self):
		analogWrite(self.SvPin,0)

	def map(self,x,imin,imax,omin,omax):
		buf = (x - imin) * (omax - omin) / (imax - imin) + omin
		if buf < omin:
			buf = omin
		if buf > omax:
			buf = omax
		return buf
#====================================================================================
SetUP()
if __name__ == '__main__':
	pass
