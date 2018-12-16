import prediction
import bba
import bba_imp
import importance

def loadVideo(videoPath, replayCount):
    videoFile = open(videoPath, 'r', encoding='utf-8')
    lines = videoFile.readlines()

    output = ""

    for i in range(replayCount):
        for line in lines:
            split = line.split('\n')
            output += split[0]

    videoFile.close()
    return output

def main():
    samplePath = "samples/report.2010-09-13_1003CEST.log"
    videoInput = "samples/video_sample_01.txt"

    videoInput = loadVideo(videoInput, 3)

    prediction.simulate(videoInput, samplePath)
    importance.simulate(videoInput, samplePath)
    bba.simulate(videoInput, samplePath)
    bba_imp.simulate(videoInput, samplePath)

main()