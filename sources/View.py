import sys, os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import random
import cv2
import numpy as np

class ImageViewer:
    def __init__(self, parent, image=None, x=0, y=0):
        #super(ImageViewer, self).__init__(parent)
        self.parent = parent
        self.imageLabel = QLabel(parent=self.parent)
        self.imageLabel.move(x, y)
        self.w = 0
        self.h = 0
        self.fixSize = False
        if(image is None):
            self.image = None
            return 
        self.setImage(image)
        self.image = image
    
    def setImage(self, image):
        if self.fixSize:
            image = cv2.resize(image , dsize=(self.w , self.h))
        
        height, width, dim = image.shape
        bytesPerLine = dim * width
        self.imageLabel.resize(width, height)

        self.imageLabel.resize(width, height)
        image = QImage(image, width, height, bytesPerLine, QImage.Format_RGB888)
        self.imageLabel.setPixmap(QPixmap.fromImage(image))
        self.image = image

    #画像の表示位置を設定する
    def move(self, x, y):
        self.imageLabel.move(x,y)

    #あらかじめ画像が表示される大きさを設定する
    def resize(self, w, h):
        self.fixSize = True
        self.w , self.h = w, h
        if  not(self.image is None): 
            self.setImage(self.image)