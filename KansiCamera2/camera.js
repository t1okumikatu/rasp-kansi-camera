//#####################################################################
/*
    +-------------+
    |             |
    +-------------+
    (C) 2022 Rcat999

    >Twitter @Rcat999 (連絡はTwitterのDMをご利用ください)
    >YouTube Rcat999
    
    ・概要

    ・注意点
    内容は保証しません

    ・利用規約
    下記グローバルルールに則ります
    https://sites.google.com/view/rcatglobalrule

    ・履歴
    2022// 1.0.0 初版

    ===ヘッダーここまで===
*/
//#####################################################################
window.addEventListener("DOMContentLoaded",Init); //必須

//便利テンプレート用変数----------------------------------
let ViewPortWidth;let ViewPortHeight;
let Font = "arial black"; //Canvas用フォント

//便利関数=====================================================================
//divブロックごとの表示非表示制御
function ShowHide(ObjID){
    let obj = document.querySelector("#" + ObjID);
    obj.style.display = obj.style.display == "block" ? "none" : "block";
}
//Canvas関係-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
/*
Canvas メゾット
let Canv = document.querySelector("#area1");
let Context = Canv.getContext("2d");
Context.fillStyle = "#FEF0F0";
Context.strokeStyle = "000000";
Context.fillRect(0,0,w,h);
Context.lineWidth = 2;
Context.strokeRect(0,0,w,h);
Context.textAlign = "center";
Context.textBaseline = "middle";
Context.font = "14px arial black";
Context.fillText("CANVAS領域",w/2,h/2);
Context.beginPath();
Context.arc(c[0],c[1],w*0.4,ToRad(0),ToRad(360));
Context.moveTo(w*0.4,c[1]);
Context.lineTo(w*0.1,c[1]);
Context.fill();
Context.stroke();
Context.save();
Context.translate(c[0],c[1]);
Context.rotate(-VolumeNowAng * Math.PI/180);
Context.restore();
*/
function CanvasInit(CanvasID){
    let Canv = document.querySelector("#" + CanvasID);
    let cont = Canv.getContext("2d");
    let w = Canv.width; let h = Canv.height;
    cont.clearRect(0,0,w,h);
    cont.fillStyle = "#CCC";
    cont.strokeStyle = "#000";
    cont.fillRect(0,0,w,h);
}
//Canvasの座標取得関数----------------------------------------
//addEventListenerの即時関数にて、e=>{GetXY(e,"Canvas",0)}で呼び出し
function GetXY_Mouse(e,CanvasID,Mode=0){
    let Canv = document.querySelector("#" + CanvasID);
    let X;let Y;
    //モード別座標計算 0:普通 1:Y軸逆転(上が+) 2:中心が0,0でYが上
    if (Mode == 0){
        X = e.offsetX;
        Y = e.offsetY;
    } else if (Mode == 1){
        X = e.offsetX;
        Y = -1 * e.offsetY;
    } else if(Mode == 2){
        X = e.offsetX - (Canv.width / 2);
        Y = -1 * (e.offsetY - Canv.height / 2);
    }
    return [X,Y];
}
//タッチ用
function GetXY_Touch(e,CanvasID,Mode=0){
    let Canv = document.querySelector("#" + CanvasID);
    let CanvX = Canv.getBoundingClientRect().left + window.pageXOffset;
    let CanvY = Canv.getBoundingClientRect().top + window.pageYOffset;
    let touche;
    for(let i=0;i<e.touches.length;i++){
        if(CanvX <= e.touches[i].clientX && e.touches[i].pageX <= CanvX + Canv.width && CanvY <= e.touches[i].pageY && e.touches[i].pageY<= CanvY + Canv.height){
            touche = e.touches[i];
            break;
        }
    }
    if(!touche) return false;
    let X;let Y;
    //モード別座標計算 0:普通 1:Y軸逆転(上が+) 2:中心が0,0でYが上
    if (Mode == 0){
        X = touche.pageX - CanvX;
        Y = touche.pageY - CanvY;
    } else if (Mode == 1){
        X = touche.pageX - CanvX;
        Y = -1 * (touche.pageY - CanvY);
    } else if(Mode == 2){
        X = touche.pageX - CanvX - (Canv.width / 2);
        Y = -1 * (touche.pageY - CanvY - Canv.height / 2);
    }
    return [X,Y];
}

//=====================================================================
function Init(){
    //情報をHTMLに記述する場合
    let VERSION = "1.0.0";
    let LASTDATE = "2022//";
    //document.querySelector('#VERSION').innerHTML = "(C) 2021 Rcat999  Ver" + VERSION;
    
    //便利テンプレート----------------------------------------
    //画面サイズの取得
    ViewPortWidth = document.body.clientWidth;
    ViewPortHeight = document.documentElement.clientHeight;

    MenuInit();
    Controlinit();
    //ストリームイベント
    let STREAMIMG = document.querySelector("#stream_img");
    STREAMIMG.width = ViewPortWidth;
    STREAMIMG.addEventListener("load",e=>{
        //console.log(e.target.src);
        if (NowStream) window.setTimeout(ImageReload,1);
    });
    //録画イベント
    GetNowStatus();
}


//#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=
//グローバル変数
let NowStream = false;
let NowTimeLapse = false;
let LastPOS = [-1,-1];
let LastTouchTime = 0;
let flip = [0,0];
function Controlinit(){
    let STREAMIMG = document.querySelector("#stream_img");
    
    STREAMIMG.addEventListener("touchstart",function(e){
        e.preventDefault();
        if(!NowStream) return;
        let POS = GetXY_Touch(e,"stream_img");
        LastPOS[0] = POS[0];
        LastPOS[1] = POS[1];
    });
    STREAMIMG.addEventListener("touchend",function(e){
        if(!NowStream) return;
        fetch("/CameraCont?X=0");
    });
    STREAMIMG.addEventListener("touchmove",function(e){
        e.preventDefault();
        if(!NowStream) return;
        let Nt = Date.now();
        if(Nt - LastTouchTime < 50) return; //50ミリ秒以上間隔をあける(デバイスによってイベントの呼出し間隔が異なるため)
        LastTouchTime = Nt;
        let POS = GetXY_Touch(e,"stream_img");
        X = POS[0] - LastPOS[0];
        Y = POS[1] - LastPOS[1];
        if(Math.abs(X) > 3 || Math.abs(Y) > 3){
            LastPOS[0] = POS[0];
            LastPOS[1] = POS[1];
            X /= 4; //感度調整
            Y /= 4;   
            if(Math.abs(X) > 5) X = 5 * Math.sign(X); //上限設定
            if(Math.abs(Y) > 5) Y = 5 * Math.sign(Y);
            //console.log(POS[0] + ":" + POS[1]);
            //console.log(X + ":" + Y);
            let URL = "/CameraCont?X=" + parseInt(X * (flip[0] ? 1 : -1)) + "&Y=" + parseInt(Y * (flip[1] ? 1 : -1));
            fetch(URL);
        }
    });
    //PCからの操作用
    document.addEventListener("keydown",e=>{
        KeyordControl(e.keyCode,"down");
    });
    document.addEventListener("keyup",e=>{
        KeyordControl(e.keyCode,"up");
    });

}
let KeyBordMoveData = [0,0];
let KeyBordMoveDataFlag = false;
function KeyordControl(code,ivent){
    if (ivent == "up"){
        KeyBordMoveData = [0,0];
        KeyBordMoveDataFlag = false;
        return;
    }
    switch(code){
        //左----------------
        case 37:
        case 65:
            KeyBordMoveData[0] = 1;
            break;
        //上----------------
        case 38:
        case 87:
            KeyBordMoveData[1] = 1;
            break;
        //右----------------
        case 39:
        case 68:
            KeyBordMoveData[0] = -1;
            break;
        //下----------------
        case 40:
        case 83:
            KeyBordMoveData[1] = -1;
            break;
        default:
            return;
    }
    if(KeyBordMoveDataFlag == false){
        KeyBordMoveDataFlag = true;
        SendKeyBordMove();
    }
}
function SendKeyBordMove(){
    if(KeyBordMoveDataFlag == false) return;
    let Base = -1;
    let URL = "/CameraCont?X=" + parseInt((flip[0] ? 1 : -1) * Base*KeyBordMoveData[0]) + "&Y=" + parseInt((flip[1] ? 1 : -1) * Base*KeyBordMoveData[1]);
    fetch(URL).then(responce=>{
        window.setTimeout(SendKeyBordMove,50);
    });
}
function Shoot(){
    let STREAMIMG = document.querySelector("#stream_img");
    let Canv = document.querySelector("#streamcamv");
    Canv.width = STREAMIMG.width;
    Canv.height = STREAMIMG.height;
    let Context = Canv.getContext("2d");
    Context.fillStyle = "#333";
    Context.fillRect(0,0,Canv.width,Canv.height);
    window.setTimeout(function(){
        Context.clearRect(0,0,Canv.width,Canv.height);
        Canv.width = 0; Canv.height = 0; //0にしないと画像に重なっているので操作できなくなる
    },100);

    fetch("/streamShoot");
    if(document.querySelector("#AutoDLCapture").checked){
        window.setTimeout(function(){
            let link = document.createElement('a');
            link.download = 'capture.jpg';
            link.href = "/GetShoot";
            link.click();
        },1000);
    }
}

//初期化系
function MenuInit(){
    let MENU = document.querySelector("#Menu");
    MENU.style.display = "none";
    let MENUButton = document.querySelector("#Button_Menu");
    MENUButton.addEventListener("click",function(){
        MENU.style.display = MENU.style.display == "block" ? "none" : "block";
    });
    let STREAMButton = document.querySelector("#Button_Stream");
    let STREAMShootButton = document.querySelector("#Button_StreamShoot");
    let RECButton = document.querySelector("#Button_Rec");
    let LightButton = document.querySelector("#Button_Light");
    let TimelapseButton = document.querySelector("#Button_TimelapseShoot");
    STREAMButton.addEventListener("click",PUSHStream);
    RECButton.addEventListener("click",PUSHRec);
    STREAMShootButton.addEventListener("click",Shoot);
    STREAMShootButton.disabled = true;
    LightButton.addEventListener("click",PUSHLight);

    let CONF_MENU = document.querySelector("#Menu_CameraSetting");
    CONF_MENU.style.display = "none";
    let CONF_MENUButton = document.querySelector("#Button_CameraSetting");
    CONF_MENUButton.addEventListener("click",function(){
        CONF_MENU.style.display = CONF_MENU.style.display == "block" ? "none" : "block";
    });

    let Menu_Timelapse = document.querySelector("#Menu_Timelapse");
    Menu_Timelapse.style.display = "none";
    TimelapseButton.addEventListener("click",function(){
        Menu_Timelapse.style.display = Menu_Timelapse.style.display == "block" ? "none" : "block";
    });
    let TimelapseStartButton = document.querySelector("#Timelapse_Start");
    let TimelapseCancelButton = document.querySelector("#Timelapse_Cancel");
    TimelapseCancelButton.addEventListener("click",function(){
        Menu_Timelapse.style.display = "none";
    });
    TimelapseStartButton.addEventListener("click",function(){
        let TLtime = parseInt(document.querySelector("#Timelapse_Time").value);
        TimelapseStartButton.disabled = !false;
        let URL = "/Timelapse?mode="
        URL += NowTimeLapse ? "stop":"start";
        URL += "&time=" + String(TLtime);
        fetch(URL).then(Resp=>{
                return Resp.text();
            }).then(Result=>{
                console.log(Result);
                if(Result == "OK"){
                    TimelapseStartButton.innerHTML = NowTimeLapse ? "開始":"停止";
                    Menu_Timelapse.style.display = "none";
                    NowTimeLapse = !NowTimeLapse;
                }
                TimelapseStartButton.disabled = !true;
        });
    });


    //カメラ設定
    document.querySelector("#Setting_Resolution").addEventListener("change",function(e){
        SendSetting("Resolution",e.currentTarget.value);
    });
    document.querySelector("#Setting_FlameRate").addEventListener("change",function(e){
        SendSetting("FlameRate",e.currentTarget.value);
    });
    document.querySelector("#Setting_Mirror").addEventListener("click",function(){
        console.log(flip[0]);
        flip[0] = !flip[0];
        console.log(flip[0]);
        SendSetting("hflip",flip[0]);
    });
    document.querySelector("#Setting_MirrorUpDown").addEventListener("click",function(){
        flip[1] = !flip[1];
        SendSetting("vflip",flip[1]);
    });

    document.querySelector("#Setting_Iso").addEventListener("change",function(e){
        SendSetting("iso",e.currentTarget.value);
    });
    document.querySelector("#Setting_Brightness").addEventListener("input",function(e){
        SendSetting("brightness",e.currentTarget.value);
        document.querySelector("#Brightness_Value").innerHTML = e.currentTarget.value;
    });
    document.querySelector("#Setting_contrast").addEventListener("input",function(e){
        SendSetting("contrast",e.currentTarget.value);
        document.querySelector("#contrast_Value").innerHTML = e.currentTarget.value;
    });
    document.querySelector("#Setting_fontsize").addEventListener("input",function(e){
        SendSetting("fontsize",e.currentTarget.value);
        document.querySelector("#fontsize_Value").innerHTML = e.currentTarget.value;
    });
    //OpenCV
    document.querySelector("#Setting_Mode").addEventListener("change",function(e){
        SendSetting("cammode",e.currentTarget.value);
    });
    document.querySelector("#Setting_cv_MotionEnable").addEventListener("change",function(e){
        SendSetting("MotionEnable",(e.currentTarget.value == "有効" ? true:false));
    });
    document.querySelector("#Setting_cv_Motion_Threshold").addEventListener("input",function(e){
        SendSetting("Motion_Threshold",e.currentTarget.value);
    });
    document.querySelector("#Setting_cv_Motion_Preview").addEventListener("change",function(e){
        SendSetting("Motion_Preview",(e.currentTarget.value == "有効" ? true:false));
    });
    document.querySelector("#Setting_cv_MotionTrigger").addEventListener("change",function(e){
        SendSetting("MotionTrigger",(e.currentTarget.value == "有効" ? true:false));
    });
    document.querySelector("#Setting_cv_Recordingtime").addEventListener("input",function(e){
        SendSetting("MotionRectime",e.currentTarget.value);
    });
}
//=====================================================================
//現在の状態を取得
function GetNowStatus(){
    fetch("/GetStatus").then(Resp=>{
            return Resp.json();
        }).then(Result=>{
            console.log(Result);
            //録画ボタンの状態を変更
            document.querySelector("#Button_Rec").textContent = (Result["recording"] == true && Result["streaming"] == false) ? "録画停止":"録画開始";
            document.querySelector("#Setting_Resolution").value = Result["resolution"];
            document.querySelector("#Setting_FlameRate").value = Result["framerate"];
            document.querySelector("#Setting_Iso").value = Result["iso"];
            //タイムラプス
            NowTimeLapse = Result["timelapse"];
            document.querySelector("#Timelapse_Start").innerHTML = NowTimeLapse ? "停止":"開始";
            document.querySelector("#Timelapse_Time").value = Result["timelapsetime"];
            //ライトボタン
            document.querySelector("#Button_Light").style.backgroundColor = Result["light"] ? "#FF0" : "#CCC";
            flip[0] = Result["hflip"];
            flip[1] = Result["vflip"];
            //OpenCV系
            document.querySelector("#Setting_Mode").value = Result["cammode"];
            document.querySelector("#Setting_cv_MotionEnable").value = Result["MotionEnable"] ? "有効":"無効";
            document.querySelector("#Setting_cv_Motion_Threshold").value = Result["Motion_Threshold"];
            document.querySelector("#Setting_cv_Motion_Preview").value = Result["Motion_Preview"] ? "有効":"無効";
            document.querySelector("#Setting_cv_MotionTrigger").value = Result["MotionTrigger"] ? "有効":"無効";
            document.querySelector("#Setting_cv_Recordingtime").value = Result["MotionRectime"];
        });
}
//=====================================================================
function SendSetting(Key,Value){
    fetch("/Camerasetting?" + Key + "=" + Value)
    .then(responce=>{
        return responce.text();
    }).then(text=>{
        console.log(text);
    });
}

//#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=
//イベント系
function PUSHStream(){
    document.querySelector("#stream_img").src = NowStream ? "camimage.png" : "/stream";
    let STREAMButton = document.querySelector("#Button_Stream");
    if(NowStream){
        STREAMButton.innerHTML = "ストリーム開始";
        window.setTimeout(function(){fetch("/streamStop");},500);
    } else {
        STREAMButton.innerHTML = "ストリーム終了";
    }
    document.querySelector("#Button_StreamShoot").disabled = NowStream;
    NowStream = !NowStream;
}
//=====================================================================
function PUSHRec(){
    let RECButton = document.querySelector("#Button_Rec");
    if(RECButton.textContent == "録画開始"){
        fetch("/RecodingStart");
        RECButton.textContent = "録画停止";
    } else {
        fetch("/RecodingStop");
        RECButton.textContent = "録画開始";
    }
}
//=====================================================================
function PUSHLight(){
    let LightButton = document.querySelector("#Button_Light");
    if(LightButton.style.backgroundColor == 'rgb(255, 255, 0)'){
        fetch("/CameraCont?Light=OFF");
        LightButton.style.backgroundColor = "#CCC";
    } else {
        fetch("/CameraCont?Light=ON");
        LightButton.style.backgroundColor = "#FF0";
    }
}
//=====================================================================
function ImageStream(){

}
function ImageReload(){
    document.querySelector("#stream_img").src = "/stream?id=" + Math.random();
}
//=====================================================================
//=====================================================================
//=====================================================================