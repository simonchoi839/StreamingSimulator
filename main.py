import prediction
import bba
import importance

def loadVideo(videoPath):
    videoFile = open(videoPath, 'r', encoding='utf-8')
    lines = videoFile.readlines()

    output = ""
    for line in lines:
        split = line.split('\n')
        output += split[0]

    videoFile.close()
    return output

def main():
    samplePath = "samples/report.2010-09-13_1003CEST.log"
    videoInput = "samples/video_sample_03.txt"

    videoInput = loadVideo(videoInput)

    prediction.simulate(videoInput, samplePath)
    bba.simulate(videoInput, samplePath)
    importance.simulate(videoInput, samplePath)

main()