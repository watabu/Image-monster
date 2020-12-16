import sys, os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import random
import cv2
import numpy as np
import math
import asyncio
import time
import tkinter
from PIL import Image, ImageTk
from math import log
from View import ImageViewer

#画像取り込み、切り抜き、ステータス生成をする
class MonsterGenerator:
    def __init__(self, parent):
        self.parent = parent
        
    #画像を取得し親に渡す
    def capture(self):
        # ファイル選択ダイアログの表示
        file_name = QFileDialog.getOpenFileName(self.parent, 'Open file', './')     # 画像を選択してファイル名を取得
        if file_name[0] == '':
            return    
       
        n = np.fromfile(file_name[0], dtype=np.uint8)# imreadだと日本語のファイル名に対応できないため，np.fromfileとcv2.imdecodeを使う
        image = cv2.imdecode(n, cv2.IMREAD_COLOR) 
        self.image = image
        #画像をセットする
        self.parent.setImage(image)

    def eventStart(self, event):
        self.canvas.delete("rect")
        self.canvas.create_rectangle(event.x, event.y, event.x + 1, event.y + 1, outline="red", tag="rect")
        self.sx, self.sy = event.x, event.y
    
    def eventDraw(self, event):
        self.canvas.coords("rect", self.sx, self.sy, max(0, min(self.i_w, event.x)), max(0, min(self.i_h, event.y)))
    
    def eventRelease(self, event):
        sx, sy, ex, ey = [ round(n) for n in self.canvas.coords("rect") ]
        self.rect_d = (sx, sy, ex, ey)
        self.root.destroy()

    def getRect(self, img):

        self.root = tkinter.Tk()
        self.root.attributes("-topmost", True)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_tk = ImageTk.PhotoImage(image = Image.fromarray(img_rgb))

        self.canvas = tkinter.Canvas(self.root, bg="black", width=self.i_w, height=self.i_h)
        self.canvas.create_image(0, 0, image=img_tk, anchor=tkinter.NW)

        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.eventStart)
        self.canvas.bind("<Button1-Motion>", self.eventDraw)
        self.canvas.bind("<ButtonRelease-1>", self.eventRelease)
        self.root.mainloop()

    #画像を切り抜く
    def crop(self, image):
        #TODO 切り抜き方法を工夫する
        height, width, dim = image.shape
        self.i_h = height
        self.i_w = width
        # 0: Background (cv2.GC_BGD)
        # 1: Foreground (cv2.GC_FGD)
        # 2: Probably Background (cv2.GC_PR_BGD)
        # 3: Probably Foreground (cv2.GC_PR_FGD)
        maskGC = np.zeros(image.shape[:2], np.uint8)

        modelShape = (1, 65) # this value should not be changed

        bgdModel = np.zeros(modelShape, np.float64)
        fgdModel = np.zeros(modelShape, np.float64)

        self.getRect(image)
        # paddingAbove = 60
        # paddingBelow = 70
        # paddingLeft = 30
        # paddingRight = 50

        # paddingAbove = int(height * 0.1)
        # paddingBelow = int(height * 0.1)
        # paddingLeft = int(width * 0.1)
        # paddingRight = int(width * 0.1)

        # rect = (paddingLeft, paddingAbove, width - paddingRight, height - paddingBelow)
        rect_d = self.rect_d
        rect = (rect_d[0], rect_d[1], rect_d[2]-rect_d[0], rect_d[3]-rect_d[1])

        itrCnt = 15
        #itrCnt = 3

        print('crop: grabCut started')
        cv2.grabCut(image, maskGC, rect, bgdModel, fgdModel, itrCnt, cv2.GC_INIT_WITH_RECT)
        # cv2.grabCut(img, mask, rect, bgdModel, fgdModel, itrCnt, cv2.GC_INIT_WITH_MASK)
        print('crop: grabCut finished')

        mask = np.where((maskGC==0)|(maskGC==2), 0, 1).astype('uint8')

        return image * mask[:,:,np.newaxis]

        # return image[height//4 :height*3//4, width//4 :width*3//4,:]

    def grabcut(self, image):
        pass

    def convertImage(self, image, mask=None):
        if mask is None:
            return image

        bgrAverage = image[mask == 1].T

        colorAverage = np.average(image[mask], axis=0)
        image[mask == 0] = colorAverage
        
        return image

    #ステータスを生成して返す
    def generateStatus(self, image, debug=False):
        #rgb成分の割合の算出
        bgr_hist = image.T.sum(axis=1).sum(axis=1) 
        bgr_hist = bgr_hist / max(sum(bgr_hist), 1)
        
        #グレースケール画像
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) / 256
        
        #フーリエ変換・パワースペクトル画像の算出
        f = np.fft.fft2(image_gray, axes=(0,1))
        fshift = np.fft.fftshift(f)
        foo = np.abs(fshift)
        foo = np.where(foo < 1, 1, foo)
        magnitude_spectrum = 20 * np.log(foo) 

        h, w = magnitude_spectrum.shape
        
        #振幅の和
        sum_spec = np.sum(magnitude_spectrum) / w / h
        sum_spec = sum_spec if sum_spec > 0 else 1
        
        #中心の1/4部分
        low = np.sum(magnitude_spectrum[h//4:h*3//4, w//4:w*3//4]) / w / h
        #それ以外　外周の部分
        high = sum_spec - low
        
        #それぞれの面積を考慮した値
        high_std = high * 4 / 3 / sum_spec # 面積の3/4を占めるので 4/3倍
        low_std = low * 4 / sum_spec # 面積の1/4を占めるので 4倍
        
        #単純な全体に占める割合
        high_ratio = high / sum_spec
        low_ratio = low / sum_spec
        
        #体力に関する定数値
        hp_base1 = 100
        hp_base2 = 1
        hp_freq = (log(sum_spec) -hp_base2)
        hp_color = (bgr_hist[1]/0.33)**2
        
        #攻撃力に関する定数値
        attack_base = 100
        attack_freq = high_ratio/0.5
        attack_color = (bgr_hist[2]/0.33)**2
        
        #防御力に関する定数値
        defence_base = 100
        defence_freq = low_ratio/0.5
        defence_color = (bgr_hist[0]/0.33)**2
            
        status = Status()
        status.hp = max(1, round(hp_base1 * hp_freq * hp_color))
        status.attack = max(1, round(attack_base * attack_freq * attack_color))
        status.defence = max(1, round(defence_base * defence_freq * defence_color))
        status.command=((status.attack+status.defence)%5)+1
        
        if debug:
            #テスト用の出力
            print("bgr: " , bgr_hist)
            # print("sum:", sum_spec, log(sum_spec))
            # print("high:", high, high_ratio, high_std)
            # print("low:", low, low_ratio, low_std)
            
            print("base * freq * color = value")
            print("hp(green) info : %f * %f * %f = %d" % (hp_base1, hp_freq, hp_color, status.hp))
            print("atk(red) info: %f * %f * %f = %d" % (attack_base, attack_freq, attack_color, status.attack))
            print("def(blue) info: %f * %f * %f = %d" % (defence_base, defence_freq, defence_color, status.defence))

            print("status:", status.hp, status.attack, status.defence,status.command)
            print("")
            
        return status
        

    def generateMonster(self, image):
        monster = Monster(image)
        #monster.status = self.generateStatus(image)
        monster.status = self.generateStatus(image, True)
        return monster



class Status:
    def __init__(self, hp=0, attack=0, defence=0,command=1):
        self.hp = hp
        self.attack = attack
        self.defence = defence
        self.command=((attack+defence)%5)+1
    
    def print(self):
        print("status:", self.hp, self.attack, self.defence)

class Battle:
    #プレイヤーとエネミーを初期化でもらってくる
    def __init__(self, player=None, enemy=None):
        #プレイヤーは初期化時に渡される
        self.player = player
        
        #ステータスを決め打ちで決める
        #self.player = Monster(None)
        #self.player.status = Status(20,5,25)

        self.enemy = enemy
        #敵も決め打ち
        #self.enemy = Monster(None)
        #self.enemy.status=Status(20,5,0)
        
        #1ターン行動するボタン
        self.button_act = None

    def act_one_turn(self,command=0):
        if self.player.isDead() or self.enemy.isDead():
            return -1
        self.player.attackResult = ""
        self.enemy.attackResult = ""

        #プレイヤーが敵に攻撃する
        if command==0:
            self.enemy.take_damage(self.damage_calculator(self.player,self.enemy))
            print("tekinohp",max(self.enemy.status.hp,0))
        if command==1:
            self.player.status.attack=math.ceil(self.player.status.attack*1.5)
        if command==2:
            self.player.status.defence=math.ceil(self.player.status.defence*1.5)
        if command==3:
            self.enemy.status.defence=math.ceil(self.player.status.defence*0.8)
        if command==4:
            self.enemy.status.attack=math.ceil(self.enemy.status.attack*0.8)
        if command==5:
            self.enemy.take_damage(self.damage_calculator(self.player, self.enemy,1.5))
        if(self.enemy.isDead()):
            return 1

        #敵がプレイヤーに攻撃する
        if random.randrange(2)==1:
            self.player.take_damage(self.damage_calculator(self.enemy, self.player))
        else:
            if self.enemy.status.command==1:
                self.enemy.status.attack=math.ceil(self.enemy.status.attack*1.5)
            if self.enemy.status.command==2:
                self.enemy.status.defence=math.ceil(self.enemy.status.defence*1.5)
            if self.enemy.status.command==3:
                self.player.status.defence=math.ceil(self.player.status.defence*0.8)
            if self.enemy.status.command==4:
                self.player.status.attack=math.ceil(self.player.status.attack*0.8)
            if self.enemy.status.command==5:
                self.player.take_damage(self.damage_calculator(self.enemy,self.player,1.5))

        print("mikatanohp",max(self.player.status.hp,0))
        #self.end_check(self.player.status.hp,1)
        if(self.player.isDead()):
            return 2
        
        #print("player: ", self.player.attackResult)
        #print("enemy: ", self.enemy.attackResult)

        return 0
            
    def damage_calculator(self,attacker, defencer, power=1):
        attack = attacker.status.attack
        defence = defencer.status.defence

        rando=random.uniform(0.5,1.5)
        base=max(attack-defence,0)
        cri=random.randrange(200)
        ddg=random.randrange(100)
        geta=random.randrange(-30,30,1)
        
        if cri>=attack+50:
            crit=1.5
            print("critical!")
            attacker.attackResult ="critical!" 
        else:
            crit=1
        if ddg<=min(defence/2,50):
            dodge=0
            print("dodge!")
            defencer.attackResult ="dodge!"
        else:
            dodge=1
        
        damagebase=max(math.ceil((base*rando+geta)*power),1)
        damage=math.ceil(damagebase*crit)*dodge
        return damage
    
    

class Monster:
    def __init__(self, image, status=Status()):
        self.status = status
        self.image = image
        self.attackResult = ""

    def take_damage(self, attack):
        self.status.hp = max(0,self.status.hp-attack)

    def isDead(self):
        return self.status.hp <= 0



class MyWindow(QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self.generator = MonsterGenerator(self)

        self.width = 800
        self.height = 600

        self.initUI()
        self.show()

    def initUI(self):
        self.resize(self.width, self.height)
        self.setFixedSize(self.size())
        self.setWindowTitle('Game')
        #ボタン生成・クリック時の挙動、座標設定
        captureButton = QPushButton('モンスター生成', self)
        captureButton.clicked.connect(self.generator.capture)
        captureButton.move(80,20)

        self.actButton = QPushButton('たたかう', self)
        self.actButton.clicked.connect(self.testAct)
        self.actButton.move(450, 440)
        self.actButton.setEnabled(False)
        self.actButton2 = QPushButton('たたかう2', self)
        self.actButton2.clicked.connect(self.testAct2)
        self.actButton2.move(600, 440)
        self.actButton2.setEnabled(False)

        #結果
        self.resultLabel = QLabel("", self)
        self.resultLabel.move(450, 500)
        self.resultLabel.resize(300, 30)

        #ステータス表示
        QLabel("player", self).move(450, 320)
        self.statusLabels = []
        self.statusLabels.append(QLabel("<font color=#090> hp: undefined</font>", self))
        self.statusLabels.append(QLabel("<font color=#900> attack: undefined</font>", self))
        self.statusLabels.append(QLabel("<font color=#009> defense: undefined</font>", self))
        self.statusLabels.append(QLabel("", self))
        for i in range(0, 4):
            self.statusLabels[i].move(450 , 340 + i*20)
        

        #テスト用の敵表示
        QLabel("enemy", self).move(600, 320)
        self.enemyStatusLabels = []
        self.enemyStatusLabels.append(QLabel("<font color=#090> hp: undefined</font>", self))
        self.enemyStatusLabels.append(QLabel("<font color=#900> attack: undefined</font>", self))
        self.enemyStatusLabels.append(QLabel("<font color=#009> defense: undefined</font>", self))
        self.enemyStatusLabels.append(QLabel("", self))
        for i in range(0, 4):
            self.enemyStatusLabels[i].move(600 , 340 + i*20)
        QLabel("", self).move(450, 410)

        #画像生成　self.show()の前に作っておかないと表示されない＜ーなんで？
        self.imageViewer = ImageViewer(self, x=50, y=100)
        #画像が表示される大きさを指定
        self.imageViewer.resize(300, 300)

        self.iconViewer = ImageViewer(self, x=450, y=100)
        #画像が表示される大きさを指定
        self.iconViewer.resize(200, 200)

    def setImage(self, image):
        #画像を選択後に呼び出される
        #元画像と切り抜き後の画像をセットする
        #self.image = image
        self.imageViewer.setImage(image)
        QCoreApplication.processEvents()
        
        self.image = self.generator.crop(image)
        self.player = self.generator.generateMonster(self.image)

        self.iconViewer.setImage(self.player.image)

        self.statusLabels[0].setText(colorize("hp: %d" %(self.player.status.hp), "090"))
        self.statusLabels[1].setText(colorize("attack: %d" %(self.player.status.attack), "900"))
        self.statusLabels[2].setText(colorize("defense: %d" %(self.player.status.defence), "009"))

        self.initBattle()

    def initBattle(self):
        player = self.player

        enemyImage = cv2.imread("./sources/test.png")
        enemyStatus = self.generator.generateStatus(enemyImage)
        enemy = Monster(enemyImage, enemyStatus)

        self.battle = Battle(player, enemy)
        self.actButton.setEnabled(True)
        self.actButton2.setEnabled(True)
        self.resultLabel.setText("")
        self.updateLabels(self.battle.player, self.battle.enemy)
        
    def testAct(self):
        if (self.battle is None):
            return
        res = self.battle.act_one_turn()
        
        self.updateLabels(self.battle.player, self.battle.enemy, res, 0.5)
        #asyncio.ensure_future(self.updateLabelsDelay(self.battle.player, self.battle.enemy, 1))
        #loop = asyncio.get_event_loop()
        #loop.run_until_complete(self.updateLabelsDelay(self.battle.player, self.battle.enemy,res, 1))
        
    def testAct2(self):
        if(self.battle is None):
            return
        res = self.battle.act_one_turn(self.battle.player.status.command)
        self.updateLabels(self.battle.player,self.battle.enemy,res,0.5)

    def updateLabels(self, player, enemy, res=0, delay=1):
        self.statusLabels[3].setText("waiting..")
        self.actButton.setEnabled(False)
        self.actButton2.setEnabled(False)

        self.enemyStatusLabels[0].setText(colorize("hp: %d" %(enemy.status.hp), "090"))
        self.enemyStatusLabels[1].setText(colorize("attack: %d" %(enemy.status.attack), "900"))
        self.enemyStatusLabels[2].setText(colorize("defense: %d" %(enemy.status.defence), "009"))
        self.enemyStatusLabels[3].setText(enemy.attackResult)
        if (res == 1):
            print("味方のかち")
            self.resultLabel.setText('<font color="RED"><h1>YOU WIN!<h1></font>')
            self.resultLabel.setEnabled(True)
        QCoreApplication.processEvents()
        time.sleep(delay)
        
        self.statusLabels[0].setText(colorize("hp: %d" %(player.status.hp), "090"))
        self.statusLabels[1].setText(colorize("attack: %d" %(player.status.attack), "900"))
        self.statusLabels[2].setText(colorize("defense: %d" %(player.status.defence), "009"))
        self.statusLabels[3].setText(player.attackResult)
        if (res == 2):
            print("敵のかち")
            self.resultLabel.setText('<font color="BLUE"><h1>YOU LOSE...<h1></font>')
            self.resultLabel.setEnabled(True)

        if(res == 0):
            self.actButton.setEnabled(True)
            self.actButton2.setEnabled(True)
    
    #非同期的に処理をして、敵のHP減少ー＞味方のHP減少　にしたかった。
    # async def updateLabelsDelay(self, player, enemy, res= 0, delay=0.25):
    #     self.enemyStatusLabels[0].setText(colorize("hp: %d" %(enemy.status.hp), "090"))
    #     self.enemyStatusLabels[1].setText(colorize("attack: %d" %(enemy.status.attack), "900"))
    #     self.enemyStatusLabels[2].setText(colorize("defense: %d" %(enemy.status.defence), "009"))
    #     self.enemyStatusLabels[3].setText(enemy.attackResult)
    #     if (res == 1):
    #         print("味方のかち")
    #         self.resultLabel.setText('<font color="RED"><h1>YOU WIN!<h1></font>')
    #     QCoreApplication.processEvents()
    #     await asyncio.sleep(delay)
    #     #task = asyncio.create_task(asyncio.sleep(delay))
    #     #await task

    #     self.statusLabels[0].setText(colorize("hp: %d" %(player.status.hp), "090"))
    #     self.statusLabels[1].setText(colorize("attack: %d" %(player.status.attack), "900"))
    #     self.statusLabels[2].setText(colorize("defense: %d" %(player.status.defence), "009"))
    #     self.statusLabels[3].setText(player.attackResult)
    #     if (res == 2):
    #         print("敵のかち")
    #         self.resultLabel.setText('<font color="BLUE"><h1>YOU LOSE...<h1></font>')
    
def colorize(str, color):
    return "<font color=#" + color + ">"+str+"</font>"


def main():
    app = QApplication(sys.argv)
    w = MyWindow()
    
    app.exec_()
            
if __name__ == '__main__':
    main()
