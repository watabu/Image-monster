import sys, os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import random
import cv2
import numpy as np
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

    #画像を切り抜く
    def crop(self, image):
        #TODO 切り抜き方法を工夫する
        height, width, dim = image.shape
        return image[height//4 :height*3//4, width//4 :width*3//4,:]

    #ステータスを生成して返す
    def generateStatus(self, image):
        #TODO 画像によってステータスを生成する
        return Status()

    def generateMonster(self, image):
        monster = Monster(self.crop(image))
        monster.status = self.generateStatus(image)
        return monster



class Status:
    def __init__(self, hp=0, attack=0, defence=0):
        self.hp = 0
        self.attack = 0
        self.defence = 0
    
class Battle:
    #プレイヤーとエネミーを初期化でもらってくる
    def __init__(self, player=None, enemy=None):
        #プレイヤーは初期化時に渡される？
        #self.player = player
        self.player = Monster(None)
        #ステータスを決め打ちで決める
        self.player.status = Status(0,0,0)

        #敵は固定
        self.enemy = Monster(None)
        #1ターン行動するボタン
        self.button_act = 0

    def act_one_turn(self):
        #プレイヤーが敵に攻撃する

        #敵がプレイヤーに攻撃する
        pass

    
    

class Monster:
    def __init__(self, image):
        self.status = Status()
        self.image = image

    def take_damage(self, attack):
        self.status.hp = self.status.hp
        



class MyWindow(QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self.generator = MonsterGenerator(self)
    
        self.initUI()

    def initUI(self):
        self.resize(800, 600) 
        self.setWindowTitle('Game')
        #ボタン生成・クリック時の挙動、座標設定
        captureButton = QPushButton('モンスター生成', self)
        captureButton.clicked.connect(self.generator.capture)
        captureButton.move(80,20)

        #文字生成？
        label = QLabel("test", self)
        label.move(200, 20)

        #画像生成　self.show()の前に作っておかないと表示されない＜ーなんで？
        self.imageViewer = ImageViewer(self, x=50, y=100)
        #画像が表示される大きさを指定
        self.imageViewer.resize(300, 300)

        self.iconViewer = ImageViewer(self, x=450, y=100)
        #画像が表示される大きさを指定
        self.iconViewer.resize(200, 200)

        self.show()

    def setImage(self, image):
        #画像を選択後に呼び出される
        #元画像と切り抜き後の画像をセットする
        self.image = image
        self.player = self.generator.generateMonster(self.image)

        self.imageViewer.setImage(image)
        self.iconViewer.setImage(self.player.image)
        
        
        

def main():
    app = QApplication(sys.argv)
    w = MyWindow()
    app.exec_()
            
if __name__ == '__main__':
    main()