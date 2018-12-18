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
    samplePath = "samples/report.2011-02-11_1618CET.log"
    videoInputPath = "samples/video_sample_01.txt"

    videoInput = loadVideo(videoInputPath, 10)

    prediction.simulate(videoInput, samplePath)
    importance.simulate(videoInput, samplePath)
    bba.simulate(videoInput, samplePath, \
        'result/bba.chunk.' + videoInputPath.split('/')[1].split('.')[0] + '.' + samplePath.split('/')[1].split('.')[1] + '.tsv', \
        'result/bba.time.' + videoInputPath.split('/')[1].split('.')[0] + '.' + samplePath.split('/')[1].split('.')[1] + '.tsv')
    bba_imp.simulate(videoInput, samplePath, \
        'result/bba_imp.chunk.' + videoInputPath.split('/')[1].split('.')[0] + '.' + samplePath.split('/')[1].split('.')[1] + '.tsv', \
        'result/bba_imp.time.' + videoInputPath.split('/')[1].split('.')[0] + '.' + samplePath.split('/')[1].split('.')[1] + '.tsv')

main()