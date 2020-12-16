import glob
import random

def choice_picture():
    filePath = "./pictures/*.*"
    reportfiles = [r.split('/')[-1] for r in glob.glob(filePath)]
    print(reportfiles)
    posttext = ""
    if(len(reportfiles) > 0):
        posttext = random.choice(reportfiles)
    return posttext

a = choice_picture()
print(a)