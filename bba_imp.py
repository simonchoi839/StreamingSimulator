import const

RESERVOIR = 4
RESERVOIR_UPPER = 4
ALPHA = 2
CONST_SAFE = 3
WINDOW_SIZE = 10

def getNextBitrate(buffer, bufferBitrate, currentRate, chunkIndex, videoInput, gain):
    if chunkIndex >= len(videoInput):
        return const.BITRATES[0]

    totalCount = min(WINDOW_SIZE, len(videoInput) - chunkIndex)     # 예측할 윈도우 안의 청크 개수
    impCount = videoInput[chunkIndex:(chunkIndex + totalCount)].count('I')  # 윈도우 안의 중요 청크 개수

    # 현재 버퍼 사이즈
    bufferSize = 0
    for i in range(len(buffer)):
        bufferSize += buffer[i] / (bufferBitrate[i] * const.BYTE_PER_KBIT)

    # 최초 계산 값
    slope = (const.BITRATES[-1] - const.BITRATES[0]) / (const.BUFFER_MAX - RESERVOIR - RESERVOIR_UPPER)
    safe = RESERVOIR + (currentRate - const.BITRATES[0]) / (slope * CONST_SAFE)
    if bufferSize < RESERVOIR:
        origin = const.BITRATES[0]
    elif bufferSize > const.BUFFER_MAX - RESERVOIR_UPPER:
        origin = const.BITRATES[-1]
    else:
        origin = const.BITRATES[0] + slope * (bufferSize - RESERVOIR)

    # 최초 계산값 기준 discrete bitrate
    origin_res = const.BITRATES[0]
    for i in range(len(const.BITRATES) - 1):
        if origin < const.BITRATES[i+1]:
            break
        origin_res = const.BITRATES[i+1]

    if bufferSize >= safe and currentRate > origin_res:
        origin_res = currentRate

    # 보정값
    delta = 0
    if videoInput[chunkIndex] == 'N':
        delta = ALPHA * (impCount / totalCount)
#    else:
#        delta = - (gain / impCount) / slope

    if bufferSize < RESERVOIR + delta:
        modified = const.BITRATES[0]
    elif bufferSize > const.BUFFER_MAX - (RESERVOIR_UPPER - delta):
        modified = const.BITRATES[-1]
    else:
        modified = const.BITRATES[0] + slope * (bufferSize - (RESERVOIR + delta))

    if videoInput[chunkIndex] == 'I':
        modified += (gain / impCount)

    # 보정값 기준 discrete bitrate
    modified_res = const.BITRATES[0]
    for i in range(len(const.BITRATES) - 1):
        if modified < const.BITRATES[i + 1]:
            break
        modified_res = const.BITRATES[i + 1]

    if bufferSize >= safe + delta and currentRate > origin_res:
        modified_res = currentRate

    gain += (modified_res - origin_res)
    return modified_res

def simulate(videoInput, samplePath):
    sampleFile = open(samplePath, 'r', encoding='utf-8')
    lines = sampleFile.readlines()
    totalChunkCount = len(videoInput)

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

    impChunkCount = 0
    impChunkBytes = 0

    nextBitrate = const.BITRATES[0]
    bitrate = nextBitrate

    gain = 0

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
                    totalBytes += buffer[0]
                    if videoInput[chunkCount] == 'I':
                        impChunkBytes += buffer[0]
                    buffer[0] = 0
                else:
                    buffer[0] -= willConsume
                    totalBytes += willConsume
                    if videoInput[chunkCount] == 'I':
                        impChunkBytes += willConsume
                    timeToPlay = 0

                # 앞버퍼를 모두 소진한 경우 버퍼를 당김
                if buffer[0] == 0:
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
        nextBitrate = getNextBitrate(buffer, bufferBitrate, nextBitrate, chunkCount + len(buffer), videoInput, gain)

    print('')
    print('============== SUMMARY (Buffer-Based Algorithm + IMP) ==============')
    print('Total Play Time: ', timestamp / 1000, 'seconds')
    print('Average Bitrate: ', (totalBytes / const.BYTE_PER_KBIT) / (totalChunkCount * const.CHUNK_SIZE), 'kbps')
    print('Average Bitrate (Important Range): ', (impChunkBytes / const.BYTE_PER_KBIT) / (impChunkCount * const.CHUNK_SIZE), 'kbps')
    print('Rebuffering Count: ', rebufferCount)
    print('Buffering Time: ', bufferingTime / 1000, 'seconds')
    sampleFile.close()