import const
import csv

RESERVOIR = 4 #sec
RESERVOIR_UPPER = 4 #sec
CONST_SAFE = 3

def getNextBitrate(buffer, bufferBitrate, currentRate):
    bufferSize = 0
    for i in range(len(buffer)):
        bufferSize += buffer[i] / (bufferBitrate[i] * const.BYTE_PER_KBIT)
    if bufferSize < RESERVOIR:
        return const.BITRATES[0]
    if bufferSize > const.BUFFER_MAX - RESERVOIR_UPPER:
        return const.BITRATES[-1]

    slope = (const.BITRATES[-1] - const.BITRATES[0]) / (const.BUFFER_MAX - RESERVOIR - RESERVOIR_UPPER)
    if currentRate == const.BITRATES[0]:
        safe = 0
    else:
        safe = RESERVOIR + (currentRate - const.BITRATES[0]) / (slope * CONST_SAFE)
    conRate = const.BITRATES[0] + slope * (bufferSize - RESERVOIR)

    res = const.BITRATES[0]
    for i in range(len(const.BITRATES) - 1):
        if conRate < const.BITRATES[i+1]:
            break
        res = const.BITRATES[i+1]

    if bufferSize >= safe and currentRate > res:
        return currentRate
    else:
        return res

def simulate(videoInput, samplePath, resultPath_chunk, resultPath_time):
    sampleFile = open(samplePath, 'r', encoding='utf-8')
    lines = sampleFile.readlines()
    totalChunkCount = len(videoInput)

    resultFile_chunk = open(resultPath_chunk, 'w', encoding='utf-8')
    resultFile_time = open(resultPath_time, 'w', encoding='utf-8')

    timestamp = 0       # 흐른 시간(ms)
    totalBytes = 0      # 처음부터 재생된 바이트 수(byte)
    buffer = []         # 버퍼 (bytes): 각 chunk의 바이트 수를 저장 [bytes_of_chunk_0, bytes_of_chunk_1, ...]
    bufferBitrate = []  # 버퍼의 각 chunk들의 bitrate (kbps)
    chunkCount = 0      # 재생 완료한 chunk 개수
    nextBitrate = 0     # 다운로드 요청 중인 chunk의 bitrate (kbps)
    rebufferCount = 0   # 총 리버퍼링 횟수
    bufferingTime = 0   # 총 버퍼링 시간 (ms)
    playing = False     # 버퍼의 첫번째 chunk가 플레이중인지
    buffering = True
    playingTime = 0
    impPlayingTime = 0

    impChunkCount = 0
    impChunkBytes = 0

    nextBitrate = const.BITRATES[0]
    bitrate = nextBitrate

    for i in range(len(lines)):

        if chunkCount == totalChunkCount:
            break
        line = lines[i]
        split = line.split(' ')
        timeToPlay = int(split[5])
        downloadBytes = int(split[4])

        # 다운로드 먼저
        timestamp += timeToPlay

        # nextbitrate 만큼의 chunk가 전송되었으면 buffer에 넣음
        notMoved = downloadBytes
        while notMoved > 0:
            bytesInBuffer = 0
            if len(buffer) > 0:
                bytesInBuffer = bufferBitrate[len(buffer) - 1] * const.CHUNK_SIZE * const.BYTE_PER_KBIT
                willMoved = min(bytesInBuffer - buffer[len(buffer) - 1], notMoved)
                buffer[len(buffer) - 1] += willMoved
                notMoved -= willMoved

            if len(buffer) >= const.BUFFER_MAX / const.CHUNK_SIZE:
                break
            elif len(buffer) == 0 or buffer[len(buffer) - 1] == bytesInBuffer:
                buffer.append(0)
                bufferBitrate.append(nextBitrate)

        # 맨 앞의 chunk가 완성된 chunk일 경우 재생
        while timeToPlay > 0:
            if playing == True or \
                    (playing == False and len(buffer) > 0 and buffer[0] > 0 and buffer[0] == bufferBitrate[0] * const.CHUNK_SIZE * const.BYTE_PER_KBIT):
                playing = True
                buffering = False
                willConsume = int(bufferBitrate[0] * (timeToPlay / 1000) * const.BYTE_PER_KBIT)

                if willConsume >= buffer[0]:
                    timeToPlay -= (buffer[0] * 1000 / (bufferBitrate[0] * const.BYTE_PER_KBIT))
                    playingTime += (buffer[0] * 1000 / (bufferBitrate[0] * const.BYTE_PER_KBIT))
                    totalBytes += buffer[0]
                    if videoInput[chunkCount] == 'I':
                        impChunkBytes += buffer[0]
                        impPlayingTime += (buffer[0] * 1000 / (bufferBitrate[0] * const.BYTE_PER_KBIT))
                    buffer[0] = 0
                else:
                    buffer[0] -= willConsume
                    totalBytes += willConsume
                    if videoInput[chunkCount] == 'I':
                        impChunkBytes += willConsume
                        impPlayingTime += timeToPlay
                    playingTime += timeToPlay
                    timeToPlay = 0

                # 앞버퍼를 모두 소진한 경우 버퍼를 당김
                if buffer[0] == 0:
                    resultFile_chunk.write(str(chunkCount) + '\t' + videoInput[chunkCount] + '\t' + str(bufferBitrate[0]) + '\n')
                    if videoInput[chunkCount] == 'I':
                        impChunkCount += 1

                    chunkCount += 1     # 재생 완료
                    if chunkCount == totalChunkCount:
                        break
                    buffer = buffer[1:]
                    bufferBitrate = bufferBitrate[1:]
                    playing = False

            else:       # 재생해야할 시간이 남았지만 첫번째 chunk가 완료되지 않았을 경우
                if buffering == False:
                    rebufferCount += 1
                    buffering = True
                bufferingTime += timeToPlay
                break

        # 다음에 요청할 bitrate 결정
        nextBitrate = getNextBitrate(buffer, bufferBitrate, nextBitrate)
        bufferLength = 0
        if len(bufferBitrate) > 0:
            bitrate = bufferBitrate[0]
        else:
            bitrate = 0
        for i in range(len(buffer)):
            bufferLength += (buffer[i] / const.BYTE_PER_KBIT) / bufferBitrate[i]
        resultFile_time.write(str(timestamp / 1000) + '\t' + videoInput[chunkCount - 1] + '\t' + str(bufferLength) + '\t' + str(bitrate) + '\n')

    print('')
    print('============== SUMMARY (Buffer-Based Algorithm) ==============')
    print('Total Play Time: ', timestamp / 1000, 'seconds')
    print('Average Bitrate: ', (totalBytes / const.BYTE_PER_KBIT) / (playingTime / 1000), 'kbps')
    print('Average Bitrate (Important Range): ', (impChunkBytes / const.BYTE_PER_KBIT) / (impChunkCount * const.CHUNK_SIZE), 'kbps')
    print('Rebuffering Count: ', rebufferCount)
    print('Buffering Time: ', bufferingTime / 1000, 'seconds')
    sampleFile.close()
    resultFile_chunk.close()
    resultFile_time.close()